from __future__ import annotations

import subprocess
from pathlib import Path

import install_social_autopilot as installer
import social_autopilot as core
import social_autopilot_runtime as runtime

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    print("VASTcode21 Social Autopilot v2.1.1 account-selector repair")
    print("Using the already encrypted local Windsor key; no key input is required.\n")

    try:
        api_key = core.load_key()
    except Exception as exc:
        raise SystemExit(f"ERROR: local Windsor key is not available: {exc}")

    config = runtime.load_json(runtime.CONFIG_FILE, runtime.default_config())
    try:
        result = runtime.validate_configuration(api_key, config)
    except Exception as exc:
        raise SystemExit(f"ERROR: Windsor validation failed: {exc}") from None

    state = runtime.load_json(runtime.STATE_FILE, {})
    state.update({
        "version": runtime.VERSION,
        "account_id": result["account"]["account_id"],
        "account_name": result["account"]["account_name"],
        "connector": result["connector"],
        "write_action_ready": True,
        "paid_ads": False,
        "live_trading": False,
        "account_selector_repaired_at": runtime.iso_now(),
    })
    state.pop("analytics_last_refreshed_at", None)
    runtime.save_json(runtime.STATE_FILE, state)

    py, pyw = installer.locate_python()
    installer.stop_existing_daemon()
    subprocess.Popen(
        [str(pyw), str(REPO / "tools" / "social_autopilot_daemon.py")],
        cwd=str(REPO),
        creationflags=0x00000008 | 0x00000200,
    )

    dry = subprocess.run(
        [str(py), str(REPO / "tools" / "social_autopilot_runtime.py"), "--dry-run"],
        cwd=str(REPO),
        check=False,
    )
    if dry.returncode != 0:
        raise SystemExit("ERROR: v2.1.1 dry-run did not pass. Check LOCAL_ONLY\\social\\social.log")

    print("\nSUCCESS: Windsor Instagram account selector repaired.")
    print(f"Instagram: {state['account_name']}")
    print("Social daemon: restarted")
    print("Paid ads: OFF | Live trading: OFF")


if __name__ == "__main__":
    main()
