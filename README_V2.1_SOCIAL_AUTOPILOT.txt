VASTcode21 SOCIAL AUTOPILOT v2.1

Purpose
-------
Automate organic Instagram publishing for the connected VASTcode21 Business account while keeping the existing research/MT5 safety policy intact.

Automatic flow
--------------
1. GitHub marketing planner reads verified public research/validation status.
2. It builds a compliance-filtered organic content queue.
3. A free Pillow-based builder creates branded 1080x1350 JPEG assets in marketing/assets.
4. The Windows Social Autopilot reads the latest queue/assets and publishes at most one organic Instagram image post per day through Windsor.ai.
5. Posted IDs are stored only under LOCAL_ONLY to prevent duplicate posting.

Security
--------
- Windsor API key is entered once locally and protected with Windows DPAPI.
- The key is never printed, committed to GitHub, or stored in public files.
- LOCAL_ONLY remains gitignored.
- No password is requested by VASTcode21.

Safety policy
-------------
- Paid ads: OFF.
- Live trading: OFF.
- Maximum organic posting rate: 1 post/day.
- Profit guarantees / risk-free claims are blocked.
- Historical/backtest disclaimer is added to posts.
- Only the organic Instagram create_image_post action is used by this release.
- No automatic ad campaign creation, boosting, budget changes, or paid promotion.

Installation
------------
Run tools/install_social_autopilot.py once on the Windows VASTcode21 machine. It securely asks for the Windsor API key, validates the connected Instagram account, adds a Startup entry, launches the daemon, and performs a dry-run check.

Operation
---------
The Social Autopilot checks every 30 minutes. Default publication window begins at 19:00 local Windows time. If no new compliant asset is ready, it does nothing.
