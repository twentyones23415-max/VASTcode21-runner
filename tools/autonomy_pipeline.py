from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / "LOCAL_ONLY" / "autonomy"
STATE_FILE = LOCAL / "state.json"
LOG_FILE = LOCAL / "autonomy.log"
PUBLIC_STATUS = REPO / "status" / "autonomy.json"
VERSION = "2.0.0"

ROBUSTNESS_WINDOWS = [
    ("regime_2024", "2024.01.01", "2024.12.31"),
    ("regime_2025", "2025.01.01", "2025.12.31"),
    ("recent_2026", "2026.01.01", "2026.08.31"),
]
FORWARD_MIN_AGE_DAYS = 45
FORWARD_MIN_TRADES = 10
FORWARD_RETEST_DAYS = 1

os.environ["VC21_LIVE_TRADING"] = "0"
os.environ["VC21_PAID_SERVICES"] = "0"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    line = f"[{utcnow()}] {message}"
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(f"[VASTcode21 autonomy] {message}", flush=True)


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"schema_version": 1, "version": VERSION, "candidates": {}}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("state is not an object")
        data.setdefault("schema_version", 1)
        data["version"] = VERSION
        data.setdefault("candidates", {})
        return data
    except Exception as exc:
        backup = STATE_FILE.with_suffix(f".corrupt-{int(time.time())}.json")
        shutil.copy2(STATE_FILE, backup)
        log(f"local state unreadable; preserved as {backup.name}: {exc}")
        return {"schema_version": 1, "version": VERSION, "candidates": {}}


def save_state(state: dict[str, Any]) -> None:
    LOCAL.mkdir(parents=True, exist_ok=True)
    state["version"] = VERSION
    state["updated_at"] = utcnow()
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(STATE_FILE)


def git_exe() -> str:
    configured = os.getenv("VC21_GIT_EXE", "").strip()
    if configured and Path(configured).exists():
        return configured
    default = Path(r"C:\Program Files\Git\cmd\git.exe")
    return str(default if default.exists() else "git")


def run_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([git_exe(), *args], cwd=str(REPO), text=True, capture_output=True, check=False)


def safe_publish(paths: list[Path], message: str) -> bool:
    rels = [str(p.relative_to(REPO)).replace("\\", "/") for p in paths if p.exists()]
    if not rels:
        return True
    if run_git("add", "--", *rels).returncode != 0:
        log("public status staging failed; local state remains safe")
        return False
    if run_git("diff", "--cached", "--quiet").returncode == 0:
        return True
    if run_git("commit", "-m", message).returncode != 0:
        log("public status commit failed; local state remains safe")
        return False
    for attempt in range(3):
        if run_git("pull", "--rebase", "origin", "main").returncode != 0:
            log("public status rebase failed; no force push/reset attempted")
            return False
        if run_git("push").returncode == 0:
            return True
        if attempt < 2:
            time.sleep(3)
    log("public status push failed after safe retries; no force push attempted")
    return False


def locate_local_core(explicit: str | None = None) -> Path:
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if (p / "vastcode21").exists() and (p / ".venv").exists():
            return p
        raise RuntimeError(f"local core not found: {p}")
    for p in sorted(REPO.parent.glob("VASTcode21_local_v*"), reverse=True):
        if (p / "vastcode21").exists() and (p / ".venv").exists():
            return p.resolve()
    raise RuntimeError("could not locate VASTcode21_local_v*")


def load_mt5_pass_results() -> list[dict[str, Any]]:
    base = REPO / "LOCAL_ONLY" / "mt5_bridge"
    results: dict[int, dict[str, Any]] = {}
    for p in sorted(base.glob("result_*.json")):
        try:
            item = json.loads(p.read_text(encoding="utf-8"))
            results[int(item["experiment_id"])] = item
        except Exception:
            continue
    return [v for _, v in sorted(results.items()) if str(v.get("decision")) == "pass"]


def generated_ea_path(exp_id: int, asset: str, timeframe: str) -> Path | None:
    gen = REPO / "LOCAL_ONLY" / "mt5_bridge" / "generated"
    exact = gen / f"VC21_CLOUD_{asset}_{timeframe}_{exp_id:06d}.mq5"
    if exact.exists():
        return exact
    matches = sorted(gen.glob(f"*{exp_id:06d}*.mq5"))
    return matches[-1] if matches else None


_INPUT_RE = re.compile(
    r"^(?P<prefix>\s*input\s+(?:int|double|long|ulong|bool)\s+)"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?P<mid>\s*=\s*)"
    r"(?P<value>[-+]?\d+(?:\.\d+)?)"
    r"(?P<suffix>\s*;.*)$"
)


def parse_inputs(source: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in source.splitlines():
        m = _INPUT_RE.match(line)
        if m:
            try:
                out[m.group("name")] = float(m.group("value"))
            except ValueError:
                pass
    return out


def mutate_source(source: str, changes: dict[str, float]) -> str:
    lines: list[str] = []
    for line in source.splitlines():
        m = _INPUT_RE.match(line)
        if not m or m.group("name") not in changes:
            lines.append(line)
            continue
        new = changes[m.group("name")]
        if "." not in m.group("value") and abs(new - round(new)) < 1e-9:
            rendered = str(int(round(new)))
        else:
            rendered = f"{new:.6f}".rstrip("0").rstrip(".")
        lines.append(f"{m.group('prefix')}{m.group('name')}{m.group('mid')}{rendered}{m.group('suffix')}")
    return "\n".join(lines) + ("\n" if source.endswith("\n") else "")


def clamp_int(value: float, minimum: int = 2) -> int:
    return max(minimum, int(round(value)))


def parameter_variants(inputs: dict[str, float]) -> list[tuple[str, dict[str, float]]]:
    variants: list[tuple[str, dict[str, float]]] = []
    if "FastEMA" in inputs or "SlowEMA" in inputs:
        faster: dict[str, float] = {}
        slower: dict[str, float] = {}
        if "FastEMA" in inputs:
            faster["FastEMA"] = clamp_int(inputs["FastEMA"] * 0.90)
            slower["FastEMA"] = clamp_int(inputs["FastEMA"] * 1.10)
        if "SlowEMA" in inputs:
            faster["SlowEMA"] = clamp_int(inputs["SlowEMA"] * 0.90, 3)
            slower["SlowEMA"] = clamp_int(inputs["SlowEMA"] * 1.10, 3)
        if faster:
            variants.append(("ema_faster_10pct", faster))
        if slower:
            variants.append(("ema_slower_10pct", slower))
    if "ATRStopMult" in inputs or "RR" in inputs:
        tighter: dict[str, float] = {}
        wider: dict[str, float] = {}
        if "ATRStopMult" in inputs:
            tighter["ATRStopMult"] = max(0.1, inputs["ATRStopMult"] * 0.90)
            wider["ATRStopMult"] = inputs["ATRStopMult"] * 1.10
        if "RR" in inputs:
            tighter["RR"] = max(0.2, inputs["RR"] * 0.90)
            wider["RR"] = inputs["RR"] * 1.10
        if tighter:
            variants.append(("risk_tighter_10pct", tighter))
        if wider:
            variants.append(("risk_wider_10pct", wider))
    return variants[:4]


def get_tester_context(local_core: Path, asset: str):
    sys.path.insert(0, str(REPO / "tools"))
    sys.path.insert(0, str(local_core))
    from local_mt5_bridge import ensure_mt5_env, mt5_terminal_is_running, resolve_symbol
    from vastcode21.trading.mt5_tester import MT5Tester
    ensure_mt5_env()
    if mt5_terminal_is_running():
        raise RuntimeError("MT5 terminal is open; autonomy stage deferred safely")
    symbol = resolve_symbol(asset, local_core)
    return MT5Tester(), symbol


def run_test(tester, mq5_file: Path, symbol: str, timeframe: str, from_date: str, to_date: str,
             deposit: float = 10000.0, leverage: str = "1:100", timeout_seconds: int = 900) -> dict[str, Any]:
    ex5 = tester.compile_and_install(mq5_file)
    metrics, report = tester.run_real_tick_test(ex5, symbol, timeframe, from_date, to_date, deposit, leverage, timeout_seconds)
    metrics = dict(metrics or {})
    metrics["report_path"] = str(report)
    return metrics


def metric_num(metrics: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(metrics.get(key, default))
    except (TypeError, ValueError):
        return default


def evaluate_robustness(windows: list[dict[str, Any]], variants: list[dict[str, Any]]) -> tuple[str, list[str], dict[str, Any]]:
    reasons: list[str] = []
    wm = [x["metrics"] for x in windows if x.get("ok")]
    if len(wm) != len(ROBUSTNESS_WINDOWS):
        reasons.append("rolling_window_incomplete")
    if wm:
        positive = sum(1 for m in wm if metric_num(m, "net_profit") > 0)
        pfs = [metric_num(m, "profit_factor") for m in wm]
        dds = [metric_num(m, "equity_drawdown_maximal_pct", 999.0) for m in wm]
        trades = [metric_num(m, "trades") for m in wm]
        sharpes = [metric_num(m, "sharpe_ratio", -999.0) for m in wm]
        if positive < 2:
            reasons.append("rolling_profit_instability")
        if statistics.median(pfs) < 1.05:
            reasons.append("rolling_profit_factor_too_low")
        if max(dds) > 18.0:
            reasons.append("rolling_drawdown_too_high")
        if min(trades) < 15:
            reasons.append("rolling_too_few_trades")
        if statistics.median(sharpes) < 0.20:
            reasons.append("rolling_sharpe_too_low")
    vm = [x["metrics"] for x in variants if x.get("ok")]
    if len(vm) < 4:
        reasons.append("parameter_stress_incomplete")
    if vm:
        positive = sum(1 for m in vm if metric_num(m, "net_profit") > 0)
        pfs = [metric_num(m, "profit_factor") for m in vm]
        dds = [metric_num(m, "equity_drawdown_maximal_pct", 999.0) for m in vm]
        if positive < math.ceil(len(vm) * 0.67):
            reasons.append("parameter_profit_instability")
        if statistics.median(pfs) < 1.05:
            reasons.append("parameter_profit_factor_too_low")
        if max(dds) > 18.0:
            reasons.append("parameter_drawdown_too_high")
    summary = {
        "rolling_positive_windows": sum(1 for m in wm if metric_num(m, "net_profit") > 0),
        "rolling_windows_total": len(wm),
        "rolling_median_profit_factor": round(statistics.median([metric_num(m, "profit_factor") for m in wm]), 4) if wm else None,
        "rolling_worst_equity_dd_pct": round(max(metric_num(m, "equity_drawdown_maximal_pct", 999.0) for m in wm), 4) if wm else None,
        "parameter_positive_variants": sum(1 for m in vm if metric_num(m, "net_profit") > 0),
        "parameter_variants_total": len(vm),
        "parameter_median_profit_factor": round(statistics.median([metric_num(m, "profit_factor") for m in vm]), 4) if vm else None,
        "parameter_worst_equity_dd_pct": round(max(metric_num(m, "equity_drawdown_maximal_pct", 999.0) for m in vm), 4) if vm else None,
    }
    return ("pass" if not reasons else "reject"), reasons, summary


def run_robustness_candidate(candidate: dict[str, Any], record: dict[str, Any], local_core: Path) -> None:
    exp_id = int(candidate["experiment_id"])
    asset = str(candidate["asset"])
    timeframe = str(candidate["timeframe"])
    mq5 = generated_ea_path(exp_id, asset, timeframe)
    if not mq5:
        record["robustness"] = {"status": "error", "updated_at": utcnow(), "reasons": ["generated_ea_missing"]}
        log(f"experiment={exp_id} robustness error: generated EA source missing")
        return
    tester, symbol = get_tester_context(local_core, asset)
    source = mq5.read_text(encoding="utf-8", errors="replace")
    inputs = parse_inputs(source)
    variants_plan = parameter_variants(inputs)
    if len(variants_plan) < 4:
        record["robustness"] = {"status": "error", "updated_at": utcnow(), "reasons": ["insufficient_supported_parameter_variants"], "detected_inputs": sorted(inputs)}
        log(f"experiment={exp_id} robustness deferred: insufficient supported inputs")
        return
    log(f"experiment={exp_id} robustness started ({len(ROBUSTNESS_WINDOWS)} rolling windows + {len(variants_plan)} parameter stresses)")
    windows_out: list[dict[str, Any]] = []
    for name, start, end in ROBUSTNESS_WINDOWS:
        try:
            metrics = run_test(tester, mq5, symbol, timeframe, start, end)
            windows_out.append({"name": name, "from": start, "to": end, "ok": True, "metrics": metrics})
            log(f"experiment={exp_id} {name} PF={metrics.get('profit_factor')} DD={metrics.get('equity_drawdown_maximal_pct')} trades={metrics.get('trades')}")
        except Exception as exc:
            windows_out.append({"name": name, "from": start, "to": end, "ok": False, "error": str(exc)})
            log(f"experiment={exp_id} {name} ERROR: {exc}")
    variants_out: list[dict[str, Any]] = []
    work = LOCAL / "generated" / f"experiment_{exp_id}"
    work.mkdir(parents=True, exist_ok=True)
    for name, changes in variants_plan:
        variant_file = work / f"{mq5.stem}_{name}.mq5"
        variant_file.write_text(mutate_source(source, changes), encoding="utf-8")
        try:
            metrics = run_test(tester, variant_file, symbol, timeframe, "2024.01.01", "2026.08.31")
            variants_out.append({"name": name, "changes": changes, "ok": True, "metrics": metrics})
            log(f"experiment={exp_id} {name} PF={metrics.get('profit_factor')} DD={metrics.get('equity_drawdown_maximal_pct')} trades={metrics.get('trades')}")
        except Exception as exc:
            variants_out.append({"name": name, "changes": changes, "ok": False, "error": str(exc)})
            log(f"experiment={exp_id} {name} ERROR: {exc}")
    decision, reasons, summary = evaluate_robustness(windows_out, variants_out)
    record["robustness"] = {"status": decision, "tested_at": utcnow(), "reasons": reasons, "summary": summary, "windows": windows_out, "parameter_stress": variants_out}
    if decision == "pass":
        record.setdefault("forward", {})
        record["forward"].setdefault("status", "collecting")
        record["forward"].setdefault("accepted_at", utcnow())
        log(f"experiment={exp_id} ROBUSTNESS PASS -> shadow forward collecting")
    else:
        log(f"experiment={exp_id} ROBUSTNESS REJECT reasons={','.join(reasons)}")


def forward_due(record: dict[str, Any]) -> bool:
    forward = record.get("forward") or {}
    if forward.get("status") not in {"collecting", "pending"}:
        return False
    last = forward.get("last_tested_at")
    if not last:
        return True
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(str(last).replace("Z", "+00:00")) >= timedelta(days=FORWARD_RETEST_DAYS)
    except Exception:
        return True


def run_forward_candidate(exp_id: int, record: dict[str, Any], local_core: Path) -> None:
    forward = record.setdefault("forward", {})
    accepted_at = forward.get("accepted_at") or utcnow()
    forward["accepted_at"] = accepted_at
    accepted_dt = datetime.fromisoformat(str(accepted_at).replace("Z", "+00:00"))
    start_date = accepted_dt.date()
    end_date = datetime.now(timezone.utc).date() - timedelta(days=1)
    age_days = max(0, (end_date - start_date).days)
    forward.update({"age_days": age_days, "required_age_days": FORWARD_MIN_AGE_DAYS, "required_trades": FORWARD_MIN_TRADES})
    if age_days < 1:
        forward["status"] = "collecting"
        return
    asset, timeframe = str(record["asset"]), str(record["timeframe"])
    mq5 = generated_ea_path(exp_id, asset, timeframe)
    if not mq5:
        forward.update({"status": "error", "error": "generated_ea_missing"})
        return
    tester, symbol = get_tester_context(local_core, asset)
    try:
        metrics = run_test(tester, mq5, symbol, timeframe, start_date.strftime("%Y.%m.%d"), end_date.strftime("%Y.%m.%d"))
    except Exception as exc:
        forward.update({"status": "collecting", "last_error": str(exc), "last_tested_at": utcnow()})
        log(f"experiment={exp_id} shadow forward deferred/error: {exc}")
        return
    forward["last_tested_at"] = utcnow()
    forward["metrics"] = metrics
    trades = int(metric_num(metrics, "trades"))
    pf = metric_num(metrics, "profit_factor")
    dd = metric_num(metrics, "equity_drawdown_maximal_pct", 999.0)
    net = metric_num(metrics, "net_profit")
    sharpe = metric_num(metrics, "sharpe_ratio", -999.0)
    log(f"experiment={exp_id} shadow forward age={age_days}d PF={pf} DD={dd} trades={trades}")
    if age_days < FORWARD_MIN_AGE_DAYS or trades < FORWARD_MIN_TRADES:
        forward["status"] = "collecting"
        return
    reasons: list[str] = []
    if net <= 0: reasons.append("forward_net_profit_not_positive")
    if pf < 1.05: reasons.append("forward_profit_factor_too_low")
    if dd > 15.0: reasons.append("forward_drawdown_too_high")
    if sharpe < 0.0: reasons.append("forward_sharpe_negative")
    forward.update({"reasons": reasons, "status": "pass" if not reasons else "reject", "decided_at": utcnow()})
    if forward["status"] == "pass":
        log(f"experiment={exp_id} SHADOW FORWARD PASS -> release candidate")
        build_release_candidate(exp_id, record, local_core)
    else:
        log(f"experiment={exp_id} SHADOW FORWARD REJECT reasons={','.join(reasons)}")


def build_release_candidate(exp_id: int, record: dict[str, Any], local_core: Path) -> None:
    release = record.setdefault("release", {})
    if release.get("status") == "ready":
        return
    asset, timeframe = str(record["asset"]), str(record["timeframe"])
    mq5 = generated_ea_path(exp_id, asset, timeframe)
    if not mq5:
        release.update({"status": "error", "reason": "generated_ea_missing"})
        return
    try:
        tester, _ = get_tester_context(local_core, asset)
        ex5 = tester.compile_and_install(mq5)
        out = LOCAL / "releases" / f"experiment_{exp_id}"
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ex5, out / ex5.name)
        manifest = {"experiment_id": exp_id, "asset": asset, "timeframe": timeframe, "created_at": utcnow(), "status": "RELEASE_CANDIDATE_ONLY", "live_trading_approved": False, "commercial_release_approved": False}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (out / "README.txt").write_text("VASTcode21 RELEASE CANDIDATE\nNot approved for live trading or sale automatically.\nHuman approval is required.\n", encoding="utf-8")
        release.update({"status": "ready", "created_at": utcnow(), "path": str(out)})
    except Exception as exc:
        release.update({"status": "error", "reason": str(exc)})


def public_projection(state: dict[str, Any]) -> dict[str, Any]:
    candidates = state.get("candidates") or {}
    values = list(candidates.values())
    def count(stage: str, status: str) -> int:
        return sum(1 for r in values if str((r.get(stage) or {}).get("status")) == status)
    safe = []
    for k, r in sorted(candidates.items(), key=lambda kv: int(kv[0])):
        safe.append({"experiment_id": int(k), "asset": r.get("asset"), "timeframe": r.get("timeframe"), "mt5": r.get("mt5_status"), "robustness": (r.get("robustness") or {}).get("status", "pending"), "forward": (r.get("forward") or {}).get("status", "not_started"), "release": (r.get("release") or {}).get("status", "not_ready")})
    return {"updated_at": utcnow(), "version": VERSION, "scope": ["GOLD", "BITCOIN"], "live_trading": False, "paid_services": False, "mode": "autonomous_multistage_validation", "mt5_pass_candidates_seen": len(values), "robustness_pending": sum(1 for r in values if (r.get("robustness") or {}).get("status") in {None, "pending"}), "robustness_passed": count("robustness", "pass"), "robustness_rejected": count("robustness", "reject"), "robustness_errors": count("robustness", "error"), "forward_collecting": count("forward", "collecting"), "forward_passed": count("forward", "pass"), "forward_rejected": count("forward", "reject"), "release_candidates": count("release", "ready"), "candidates": safe[-20:]}


def update_public_status(state: dict[str, Any]) -> None:
    PUBLIC_STATUS.parent.mkdir(parents=True, exist_ok=True)
    projected = public_projection(state)
    old = None
    if PUBLIC_STATUS.exists():
        try: old = json.loads(PUBLIC_STATUS.read_text(encoding="utf-8"))
        except Exception: old = None
    if isinstance(old, dict):
        a, b = dict(old), dict(projected)
        a.pop("updated_at", None); b.pop("updated_at", None)
        if a == b:
            return
    PUBLIC_STATUS.write_text(json.dumps(projected, indent=2), encoding="utf-8")
    safe_publish([PUBLIC_STATUS], "chore: update autonomy validation status")


def register_mt5_passes(state: dict[str, Any]) -> None:
    candidates = state.setdefault("candidates", {})
    for item in load_mt5_pass_results():
        exp_id = int(item["experiment_id"])
        r = candidates.setdefault(str(exp_id), {})
        r.update({"experiment_id": exp_id, "asset": str(item.get("asset")), "timeframe": str(item.get("timeframe")), "broker_symbol": str(item.get("broker_symbol") or ""), "mt5_status": "pass", "mt5_tested_at": item.get("tested_at"), "mt5_metrics": dict(item.get("metrics") or {})})
        r.setdefault("robustness", {"status": "pending"})


def run_once(local_core: Path) -> int:
    state = load_state()
    register_mt5_passes(state)
    candidates = state.get("candidates") or {}
    pending = [(int(k), r) for k, r in candidates.items() if str((r.get("robustness") or {}).get("status", "pending")) == "pending"]
    if pending:
        exp_id, record = sorted(pending, key=lambda x: x[0])[0]
        item = {"experiment_id": exp_id, "asset": record["asset"], "timeframe": record["timeframe"], "metrics": record.get("mt5_metrics") or {}}
        try:
            run_robustness_candidate(item, record, local_core)
        except Exception as exc:
            msg = str(exc)
            if "MT5 terminal is open" in msg:
                log(f"experiment={exp_id} robustness safely deferred: MT5 terminal open")
            else:
                record["robustness"] = {"status": "error", "updated_at": utcnow(), "reasons": [msg]}
                log(f"experiment={exp_id} robustness ERROR: {exc}")
        save_state(state); update_public_status(state); return 0
    due = [(int(k), r) for k, r in candidates.items() if str((r.get("robustness") or {}).get("status")) == "pass" and forward_due(r)]
    if due:
        exp_id, record = sorted(due, key=lambda x: x[0])[0]
        try:
            run_forward_candidate(exp_id, record, local_core)
        except Exception as exc:
            msg = str(exc)
            if "MT5 terminal is open" in msg:
                log(f"experiment={exp_id} shadow forward safely deferred: MT5 terminal open")
            else:
                record.setdefault("forward", {})["last_error"] = msg
                log(f"experiment={exp_id} shadow forward ERROR: {exc}")
    save_state(state); update_public_status(state); return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="VASTcode21 autonomous multi-stage validation pipeline")
    ap.add_argument("--local-core", default=None)
    ap.add_argument("--once", action="store_true", default=True)
    args = ap.parse_args()
    try:
        raise SystemExit(run_once(locate_local_core(args.local_core)))
    except Exception as exc:
        log(f"pipeline ERROR: {type(exc).__name__}: {exc}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
