VASTcode21 Cloud/MT5 Bridge v1.1

Adds a safe two-way handoff:
- Cloud keeps researching while the PC is off.
- Cloud survivors stay in encrypted MT5 validation queue.
- When the Windows PC is on, tools/local_mt5_bridge.py pulls the newest encrypted state,
  validates pending candidates in MT5 Strategy Tester using Model=4 real ticks, and pushes
  only encrypted result envelopes to handoff/inbox/.
- The next cloud run decrypts/ingests those envelopes, marks validation passed/rejected,
  stores metrics in encrypted state, and removes the consumed envelope from the public repo.
- MT5-passed strategies receive highest evolutionary parent priority.
- Live trading remains OFF. Paid services remain OFF.

No broker password, account password, or core key is committed to GitHub.
