VASTcode21 AUTONOMY v2.0.0

This upgrade extends the existing Windows Autopilot into a multi-stage autonomous validation pipeline.

Automatic stages
----------------
1. Cloud research generates GOLD/BITCOIN candidates.
2. Local MT5 bridge performs real-tick validation.
3. MT5 PASS candidates automatically enter robustness testing:
   - 2024 regime test
   - 2025 regime test
   - 2026 recent-period test
   - four small parameter perturbation tests
4. Robustness PASS candidates automatically enter shadow-forward observation.
5. Shadow-forward candidates are re-tested periodically and require at least 45 days plus minimum trade count before a decision.
6. A candidate that clears all automatic gates is compiled and packaged locally as RELEASE_CANDIDATE_ONLY.

Safety / business rules
-----------------------
- Scope stays GOLD and BITCOIN only.
- Broker symbols remain auto-resolved.
- Live trading stays OFF.
- Paid services stay OFF.
- No automatic live orders are sent.
- No automatic commercial release is approved.
- Release candidates still require explicit human approval before live trading or sale.
- Existing user-open MT5 sessions are never force-closed.
- Force-push and automatic hard reset are not used.
- Strategy specifications, detailed metrics, reports and release binaries remain under LOCAL_ONLY.
- Public status exposes only safe stage/counter information.

Operation
---------
The already-installed v1.3 Windows daemon pulls main automatically. The updated local bridge calls the new autonomy pipeline on future cycles, so no new Startup entry or new Windows installer is required.

Cloud research continues on GitHub Actions when the PC is off. Real-tick, robustness and shadow-forward MT5 testing require the Windows PC to be on and MT5 not already open interactively.
