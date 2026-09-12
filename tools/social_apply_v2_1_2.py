from __future__ import annotations

import subprocess
from pathlib import Path

import install_social_autopilot as installer
import social_autopilot as core
import social_autopilot_runtime as runtime

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    print("VASTcode21 Social Autopilot v2.1.2 Windsor selector repair")
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
        "selector_repaired_at": runtime.iso_now(),
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

    social_rc = subprocess.run(
        [str(py), str(REPO / "tools" / "social_autopilot_runtime.py"), "--dry-run"],
        cwd=str(REPO),
        check=False,
    ).returncode
    business_rc = subprocess.run(
        [str(py), str(REPO / "tools" / "business_autopilot.py")],
        cwd=str(REPO),
        check=False,
    ).returncode

    if social_rc != 0 or business_rc != 0:
        raise SystemExit(
            "ERROR: repair was applied but a validation cycle reported an issue. "
            "Check LOCAL_ONLY\\social\\social.log and LOCAL_ONLY\\business\\business.log"
        )

    print("\nSUCCESS: Windsor selector repaired with authoritative configured account.")
    print(f"Instagram: {state['account_name']}")
    print(f"Windsor selector: {state['account_id']}")
    print("Social + Business daemon: restarted")
    print("Paid ads: OFF | Live trading: OFF | Sales: OFF")


if __name__ == "__main__":
    main()
