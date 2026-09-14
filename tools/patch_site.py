#!/usr/bin/env python3
from pathlib import Path

landing = Path('site/index.html')
app = Path('site/app.html')
responsive = Path('site/responsive.css')

for path in (landing, app, responsive):
    if not path.exists():
        raise SystemExit(f'Missing required site file: {path}')

landing_text = landing.read_text(encoding='utf-8')
app_text = app.read_text(encoding='utf-8')

for asset in ('future.css', 'responsive.css', 'future.js'):
    if asset not in landing_text:
        raise SystemExit(f'Landing page asset missing: {asset}')
if 'app.html' not in landing_text:
    raise SystemExit('Product beta navigation is incomplete')
for banned_visible_phrase in ('Investor deck', 'INVESTOR ROOM', 'Pre-seed: €500,000', 'Open investor deck'):
    if banned_visible_phrase in landing_text:
        raise SystemExit(f'Public landing page contains hidden funding copy: {banned_visible_phrase}')
if 'Tutor AI Workspace' not in app_text or 'app-shell.js' not in app_text:
    raise SystemExit('Tutor app is incomplete')

print('VASTcode21 public site verified: product-first and responsive assets wired.')
