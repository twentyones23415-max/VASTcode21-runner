#!/usr/bin/env python3
from pathlib import Path

landing = Path('site/index.html')
app = Path('site/app.html')
css = Path('site/onescreen.css')
js = Path('site/onescreen.js')
legacy_deck = Path('site/investor-deck.html')
company_deck = Path('site/company-deck.html')

for path in (landing, app, css, js, legacy_deck, company_deck):
    if not path.exists():
        raise SystemExit(f'Missing required site file: {path}')

landing_text = landing.read_text(encoding='utf-8')
app_text = app.read_text(encoding='utf-8')
css_text = css.read_text(encoding='utf-8')
legacy_text = legacy_deck.read_text(encoding='utf-8')
company_text = company_deck.read_text(encoding='utf-8')
combined_public = landing_text + '\n' + legacy_text + '\n' + company_text

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
    if banned_visible_phrase.lower() in landing_text.lower() or banned_visible_phrase.lower() in company_text.lower():
        raise SystemExit(f'Public content contains unwanted funding-facing copy: {banned_visible_phrase}')

if 'logo-mark.svg' in landing_text or 'logo-mark.svg' in company_text:
    raise SystemExit('Public pages are using the wrong logo asset')
if 'company-deck.html' not in legacy_text:
    raise SystemExit('Legacy deck URL does not redirect to the company deck')
if 'Tutor AI Workspace' not in app_text or 'app-shell.js' not in app_text:
    raise SystemExit('Tutor app is incomplete')

print('VASTcode21 verified: one-screen, responsive, original logo, private founder details removed.')
