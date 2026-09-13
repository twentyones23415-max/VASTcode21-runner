#!/usr/bin/env python3
from pathlib import Path

p=Path('site/index.html')
s=p.read_text(encoding='utf-8')
css='<link rel="stylesheet" href="vast-upgrade.css">'
js='<script src="vast-upgrade.js" defer></script>'
if css not in s:
    s=s.replace('</head>',f'  {css}\n</head>')
if js not in s:
    s=s.replace('</body>',f'  {js}\n</body>')
p.write_text(s,encoding='utf-8')
print('Patched site/index.html for VASTcode21 branded upgrades.')
