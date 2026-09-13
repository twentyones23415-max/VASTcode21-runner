#!/usr/bin/env python3
from pathlib import Path

p = Path('site/index.html')
s = p.read_text(encoding='utf-8')

required = [
    'VASTcode21 — Tutor AI Workspace',
    'app-shell.css',
    'app-shell.js',
    'tutor-lab.js',
    'tutor-learning.js',
    'tutor-outcome.js',
    'tutor-vision-runtime.js',
]
missing = [item for item in required if item not in s]
if missing:
    raise SystemExit('Tutor app entry point is incomplete; refusing legacy patch: ' + ', '.join(missing))

# The modern Tutor workspace owns its own shell and assets. Legacy vast-upgrade
# injection is intentionally disabled because it can conflict with app routing.
print('Tutor app verified. No legacy site patching applied.')
