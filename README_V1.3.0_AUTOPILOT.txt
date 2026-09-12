VASTcode21 AUTOPILOT v1.3.0

Purpose
-------
One-time install, then automatic guarded operation while the Windows PC is on.

Key safeguards
--------------
- Live trading remains OFF.
- Paid services remain OFF.
- No force-push.
- No automatic git reset --hard.
- Never disables Defender or SmartScreen.
- Existing MT5 terminal is never force-closed by this daemon.
- Prevents duplicate validations while encrypted handoff envelopes await cloud ingest.
- Uses a local lock so two daemon cycles cannot modify the repo at the same time.
- Pulls cloud state before every cycle.
- If git is dirty or a pull fails, it defers rather than trying destructive recovery.
- Logs all activity to LOCAL_ONLY/mt5_bridge/daemon.log.
- Writes machine-readable status to LOCAL_ONLY/mt5_bridge/autopilot_status.json.

Cloud research
--------------
GitHub Actions continues independently on its schedule while the PC is off.
Local real-tick MT5 validation runs only while this Windows PC is on.

Current scope
-------------
GOLD and BITCOIN only. Broker symbols remain auto-resolved.
