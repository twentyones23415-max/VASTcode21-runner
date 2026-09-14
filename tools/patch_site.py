#!/usr/bin/env python3
from pathlib import Path

landing = Path('site/index.html')
app = Path('site/app.html')
css = Path('site/onescreen.css')
js = Path('site/onescreen.js')
deck = Path('site/investor-deck.html')

for path in (landing, app, css, js, deck):
    if not path.exists():
        raise SystemExit(f'Missing required site file: {path}')

landing_text = landing.read_text(encoding='utf-8')
app_text = app.read_text(encoding='utf-8')
css_text = css.read_text(encoding='utf-8')
deck_text = deck.read_text(encoding='utf-8')
combined_public = landing_text + '\n' + deck_text

for asset in ('onescreen.css', 'onescreen.js', 'vastcode21-instagram-logo.svg'):
    if asset not in landing_text:
        raise SystemExit(f'Landing page asset missing: {asset}')
if 'app.html' not in landing_text:
    raise SystemExit('Product beta navigation is incomplete')
if 'overflow:hidden' not in css_text or '100dvh' not in css_text:
    raise SystemExit('No-scroll viewport contract is missing')

banned_personal = (
    'Stefanos Tsormpatzoglou', 'Tsormpatzoglou',
    '8 years', '4 years', 'eight years', 'four years',
    '>8y<', '>4y<'
)
for phrase in banned_personal:
    if phrase.lower() in combined_public.lower():
        raise SystemExit(f'Personal detail leaked in public materials: {phrase}')

for banned_visible_phrase in ('Investor deck', 'INVESTOR ROOM', 'Pre-seed: €500,000', 'Open investor deck'):
    if banned_visible_phrase in landing_text:
        raise SystemExit(f'Public landing page contains hidden funding copy: {banned_visible_phrase}')

if 'logo-mark.svg' in landing_text:
    raise SystemExit('Landing page is using the wrong logo asset')
if 'Tutor AI Workspace' not in app_text or 'app-shell.js' not in app_text:
    raise SystemExit('Tutor app is incomplete')

print('VASTcode21 verified: one-screen, responsive, original logo, personal details removed.')
