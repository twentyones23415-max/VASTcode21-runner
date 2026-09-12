VASTcode21 v1.2.1 HOTFIX

Purpose
- Prevent MT5 Strategy Tester report failures when the same terminal installation is already open.
- Never force-close the user's MT5 terminal. The bridge defers safely and retries on the next daemon cycle.
- Remove the Python tarfile deprecation warning where supported.

Safety
- Live trading remains OFF.
- Paid services remain OFF.
- Pending MT5 candidates are not consumed when validation is deferred.

Expected behavior
- If terminal64.exe is already open: daemon logs a safe defer message and retries later.
- If MT5 is closed: bridge launches Strategy Tester normally and validates pending candidates.
