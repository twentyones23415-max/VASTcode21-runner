VASTcode21 v1.2 — Automatic Windows MT5 Bridge

Adds zero-cost hands-off local validation:
- Cloud research keeps running while the PC is OFF.
- When Windows is ON and the user is signed in, the MT5 bridge starts automatically.
- It checks the encrypted cloud queue immediately and every 30 minutes.
- It validates up to 2 pending candidates per cycle with MT5 real-tick Strategy Tester.
- It uploads only encrypted validation envelopes back to GitHub.
- The next cloud cycle consumes the results and updates evolutionary memory.
- No broker password, account password, or VC21_CORE_KEY is committed.
- Live trading OFF. Paid services OFF.

One-time local installation command after this patch is committed/pushed:
  & "$HOME\VASTcode21\VASTcode21_local_v0.6\.venv\Scripts\python.exe" .\tools\install_local_mt5_bridge_startup.py

The startup entry lives in the current Windows user's Startup folder and needs no admin rights.
