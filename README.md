# VASTcode21 GitHub Zero-Card Runner v0.8

This package is a zero-payment-method cloud research runner for **GOLD/USD and BITCOIN/USD only**.
It is designed for a **public GitHub repository** so standard GitHub-hosted Actions runners are free.

## Security model

- The VASTcode21 research core is stored only as `payload/core.enc` (AES-GCM encrypted).
- The decryption key stays in a GitHub Actions secret named `VC21_CORE_KEY`.
- Broker-seeded historical OHLC data is stored encrypted as `payload/seed.enc`.
- Research state/database and generated candidate queue are stored encrypted as `state/state.enc`.
- The public status file contains only non-sensitive counters.
- Live trading and paid services remain OFF.

## Runtime model

The workflow runs every 3 hours at minute 17 and can also be started manually.
Each job starts a temporary GitHub runner, decrypts the core and datasets, runs one cloud research cycle,
re-encrypts the new state, and commits only encrypted state + a small public summary back to the repository.
The PC can be OFF during these runs.

This is not a permanently-running VPS. It is scheduled autonomous research.
Final MT5 real-tick validation still requires the Windows/MT5 machine when available.

## What not to upload

Never commit `LOCAL_ONLY/VC21_CORE_KEY.txt` or any broker password/login.
The `.gitignore` already excludes `LOCAL_ONLY/`.

## Setup flow

1. Create a GitHub account if needed.
2. Create a **PUBLIC** repository named `VASTcode21-runner`.
3. Upload everything in this folder except `LOCAL_ONLY/` (Git normally respects `.gitignore`).
4. In GitHub: Settings -> Secrets and variables -> Actions -> New repository secret.
5. Secret name: `VC21_CORE_KEY`. Value: the exact one-line value inside `LOCAL_ONLY/VC21_CORE_KEY.txt`.
6. On the Windows MT5 machine, create the encrypted seed payload using `tools/build_seed_payload_windows.py`.
7. Upload/commit the resulting `payload/seed.enc`.
8. Actions -> `VASTcode21 autonomous research` -> Run workflow.

## Cost policy

No card, paid API, paid VPS, paid AI, or live trading is required by this runner.
GitHub can change plans/limits in the future; the workflow is intentionally modest (one cycle every 3 hours).
