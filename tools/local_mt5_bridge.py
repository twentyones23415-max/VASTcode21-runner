from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd, cwd: Path, check=True):
    return subprocess.run(cmd, cwd=str(cwd), check=check, text=True, capture_output=False)


def git_exe() -> str:
    configured = os.getenv("VC21_GIT_EXE", "").strip()
    if configured and Path(configured).exists():
        return configured
    default = Path(r"C:\Program Files\Git\cmd\git.exe")
    return str(default if default.exists() else "git")


def locate_local_core(repo: Path, explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if (p / "vastcode21").exists():
            return p
        raise SystemExit(f"Local core not found: {p}")
    root = repo.parent
    candidates = sorted(root.glob("VASTcode21_local_v*"), reverse=True)
    for p in candidates:
        if (p / "vastcode21").exists() and (p / ".venv").exists():
            return p.resolve()
    raise SystemExit("Could not find VASTcode21_local_v* with .venv next to the GitHub runner")


def ensure_mt5_env():
    if not os.getenv("MT5_TERMINAL_PATH"):
        p = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
        if p.exists():
            os.environ["MT5_TERMINAL_PATH"] = str(p)
    if not os.getenv("METAEDITOR_PATH"):
        p = Path(r"C:\Program Files\MetaTrader 5\metaeditor64.exe")
        if p.exists():
            os.environ["METAEDITOR_PATH"] = str(p)


def mt5_terminal_is_running() -> bool:
    """Return True when a terminal64.exe instance already exists.

    MT5 command-line Strategy Tester configuration is unreliable when the same
    terminal installation is already open interactively.  We never kill a user
    terminal automatically; the bridge safely defers and retries later.
    """
    try:
        p = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/FO", "CSV", "/NH"],
            text=True, capture_output=True, timeout=10, check=False,
        )
        out = (p.stdout or "").strip().lower()
        return "terminal64.exe" in out
    except Exception:
        return False


def pull_repo(repo: Path):
    g = git_exe()
    run([g, "pull", "--rebase", "origin", "main"], repo)


def read_key(repo: Path) -> str:
    p = repo / "LOCAL_ONLY" / "VC21_CORE_KEY.txt"
    if not p.exists():
        raise SystemExit(f"Missing local-only key: {p}")
    key = p.read_text(encoding="utf-8").strip()
    if len(key) < 32:
        raise SystemExit("VC21_CORE_KEY looks invalid")
    return key


def load_queue(repo: Path, key: str) -> list[dict]:
    sys.path.insert(0, str(repo / "tools"))
    from crypto_utils import decrypt_file
    state = repo / "state" / "state.enc"
    if not state.exists():
        return []
    with tempfile.TemporaryDirectory(prefix="vc21_state_") as td:
        td = Path(td)
        tar_path = td / "state.tar.gz"
        out = td / "state"
        out.mkdir()
        decrypt_file(state, tar_path, key)
        with tarfile.open(tar_path, "r:gz") as tf:
            try:
                tf.extractall(out, filter="data")
            except TypeError:
                tf.extractall(out)
        q = out / "cloud_out" / "mt5_validation_queue.json"
        if not q.exists():
            return []
        return json.loads(q.read_text(encoding="utf-8"))


def resolve_symbol(asset: str, local_core: Path) -> str:
    sys.path.insert(0, str(local_core))
    import MetaTrader5 as mt5
    from vastcode21.trading.symbol_resolver import resolve_mt5
    terminal = os.getenv("MT5_TERMINAL_PATH", "").strip()
    kwargs = {"path": terminal} if terminal else {}
    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        found = resolve_mt5(mt5, assets=(asset,), min_score=60)
        if asset not in found:
            raise RuntimeError(f"Could not resolve broker symbol for {asset}")
        return found[asset].symbol
    finally:
        mt5.shutdown()


def validate_one(item: dict, repo: Path, local_core: Path) -> dict:
    sys.path.insert(0, str(local_core))
    from vastcode21.core.config import load_settings
    from vastcode21.trading.mql5_generator import write_ea
    from vastcode21.trading.mt5_tester import MT5Tester

    asset = str(item["asset"])
    timeframe = str(item["timeframe"])
    spec = dict(item["spec"])
    exp_id = int(item["id"])
    broker_symbol = resolve_symbol(asset, local_core)

    gen = repo / "LOCAL_ONLY" / "mt5_bridge" / "generated"
    gen.mkdir(parents=True, exist_ok=True)
    # Keep a deterministic local filename tied to the cloud experiment.
    spec["name"] = f"VC21_CLOUD_{asset}_{timeframe}_{exp_id:06d}"
    ea = write_ea(spec, gen)

    old_cwd = Path.cwd()
    try:
        os.chdir(local_core)
        settings = load_settings()
        cfg = dict(settings.raw.get("real_tick_validation", {}))
        result = MT5Tester().validate(ea, broker_symbol, timeframe, cfg)
    finally:
        os.chdir(old_cwd)

    metrics = dict(result.get("metrics") or {})
    metrics.pop("report_path", None)
    return {
        "schema_version": 1,
        "experiment_id": exp_id,
        "asset": asset,
        "timeframe": timeframe,
        "strategy_name": str(item.get("strategy_name") or spec["name"]),
        "broker_symbol": broker_symbol,
        "decision": str(result["decision"]),
        "reasons": list(result.get("reasons") or []),
        "metrics": metrics,
        "tested_at": utcnow(),
    }


def encrypt_result(repo: Path, key: str, payload: dict) -> Path:
    sys.path.insert(0, str(repo / "tools"))
    from crypto_utils import encrypt_file
    inbox = repo / "handoff" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    exp_id = int(payload["experiment_id"])
    plain = repo / "LOCAL_ONLY" / "mt5_bridge" / f"result_{exp_id}_{stamp}.json"
    plain.parent.mkdir(parents=True, exist_ok=True)
    plain.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    enc = inbox / f"mt5_{exp_id}_{stamp}.enc"
    encrypt_file(plain, enc, key)
    return enc


def push_results(repo: Path, files: list[Path]):
    if not files:
        return
    g = git_exe()
    rels = [str(p.relative_to(repo)).replace("\\", "/") for p in files]
    run([g, "add", *rels], repo)
    ids = ",".join(p.stem.split("_")[1] for p in files)
    c = subprocess.run([g, "commit", "-m", f"mt5: validation envelopes {ids}"], cwd=str(repo), text=True)
    if c.returncode not in (0, 1):
        raise RuntimeError("git commit failed")
    # Cloud can commit at any time. Rebase immediately before push; retry once.
    for attempt in range(2):
        run([g, "pull", "--rebase", "origin", "main"], repo)
        p = subprocess.run([g, "push"], cwd=str(repo), text=True)
        if p.returncode == 0:
            return
        if attempt == 0:
            time.sleep(3)
    raise RuntimeError("Could not push MT5 validation envelopes")


def main():
    ap = argparse.ArgumentParser(description="VASTcode21 local MT5 validation bridge")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--local-core", default=None)
    ap.add_argument("--max", type=int, default=2, help="Maximum pending candidates to validate per run")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    local_core = locate_local_core(repo, args.local_core)
    ensure_mt5_env()
    key = read_key(repo)
    pull_repo(repo)
    queue = load_queue(repo, key)
    if not queue:
        print("[VASTcode21 MT5 bridge] no pending candidates")
        return

    if mt5_terminal_is_running():
        print("[VASTcode21 MT5 bridge] MT5 terminal is already open; validation safely deferred")
        print("[VASTcode21 MT5 bridge] no terminal was closed and no candidate was consumed")
        print("[VASTcode21 MT5 bridge] daemon will retry automatically on the next cycle")
        return

    selected = queue[: max(1, int(args.max))]
    encrypted: list[Path] = []
    print(f"[VASTcode21 MT5 bridge] validating {len(selected)} candidate(s) with MT5 real ticks")
    print("[VASTcode21 MT5 bridge] live trading OFF; paid services OFF")
    for item in selected:
        exp_id = int(item["id"])
        try:
            payload = validate_one(item, repo, local_core)
            enc = encrypt_result(repo, key, payload)
            encrypted.append(enc)
            m = payload["metrics"]
            print(
                f"experiment={exp_id} asset={payload['asset']} symbol={payload['broker_symbol']} "
                f"decision={payload['decision']} PF={m.get('profit_factor')} DD={m.get('equity_drawdown_maximal_pct')} "
                f"trades={m.get('trades')}",
                flush=True,
            )
        except Exception as exc:
            print(f"experiment={exp_id} ERROR: {exc}", flush=True)
    push_results(repo, encrypted)
    print(f"[VASTcode21 MT5 bridge] uploaded {len(encrypted)} encrypted validation envelope(s)")
    print("[VASTcode21 MT5 bridge] cloud will ingest them on the next research run")


if __name__ == "__main__":
    main()
