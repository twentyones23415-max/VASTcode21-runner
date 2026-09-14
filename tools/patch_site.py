#!/usr/bin/env python3
from pathlib import Path

landing = Path('site/index.html')
app = Path('site/app.html')

for path in (landing, app):
    if not path.exists():
        raise SystemExit(f'Missing required site file: {path}')

landing_text = landing.read_text(encoding='utf-8')
app_text = app.read_text(encoding='utf-8')

if 'future.css' not in landing_text or 'future.js' not in landing_text:
    raise SystemExit('Landing page assets are not wired correctly')
if 'investor-deck.html' not in landing_text or 'app.html' not in landing_text:
    raise SystemExit('Landing page navigation is incomplete')
if 'Tutor AI Workspace' not in app_text or 'app-shell.js' not in app_text:
    raise SystemExit('Tutor app is incomplete')

print('VASTcode21 site verified.')
