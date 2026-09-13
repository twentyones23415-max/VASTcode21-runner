#!/usr/bin/env python3
from pathlib import Path

p=Path('site/index.html')
s=p.read_text(encoding='utf-8')
assets=[
    ('</head>','  <link rel="stylesheet" href="vast-upgrade.css">\n'),
    ('</head>','  <link rel="stylesheet" href="tutor-lab.css">\n'),
    ('</body>','  <script src="vast-upgrade.js" defer></script>\n'),
    ('</body>','  <script src="tutor-lab.js" defer></script>\n'),
]
for marker, asset in assets:
    if asset.strip() not in s:
        s=s.replace(marker,asset+marker)
p.write_text(s,encoding='utf-8')
print('Patched site/index.html for VASTcode21 branded upgrades, Tutor AI Lab and Event Risk Shield.')
