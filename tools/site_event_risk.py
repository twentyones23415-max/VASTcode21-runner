#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'site/data/event_risk.json'
BLS_FALLBACK = ROOT / 'config/bls_schedule_fallback_2026.json'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36'
CONTACT = 'VASTcode21 Event Risk Monitor; https://github.com/twentyones23415-max/VASTcode21-runner'
ET = ZoneInfo('America/New_York')
UTC = timezone.utc

BLS_ICS = 'https://www.bls.gov/schedule/news_release/bls.ics'
BLS_MONTH = 'https://www.bls.gov/schedule/{year}/{month:02d}_sched_list.htm'
BEA_SCHEDULE = 'https://www.bea.gov/news/schedule'
FED_MONTH = 'https://www.federalreserve.gov/newsevents/{year}-{month}.htm'
MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December']
MONTHS = {m: i for i, m in enumerate(MONTH_NAMES, 1)}

HIGH_WORDS = (
    'consumer price index','employment situation','personal income and outlays','fomc meeting',
    'fomc press conference','gross domestic product','gdp (advance','federal funds','monetary policy'
)
MEDIUM_WORDS = (
    'producer price index','job openings','jolts','productivity and costs','employment cost index',
    'international trade','import and export price','economic outlook','speech - chair','speech - vice chair',
    'speech - governor','fomc minutes'
)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'From': CONTACT,
        'Accept': 'text/html,application/xhtml+xml,text/calendar;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', errors='replace')


def clean_text(raw: str) -> list[str]:
    raw = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', raw)
    raw = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</li>|</tr>|</td>|</th>|</h\d>', '\n', raw)
    raw = re.sub(r'(?s)<[^>]+>', ' ', raw)
    raw = html.unescape(raw)
    return [x for x in (' '.join(v.split()) for v in raw.splitlines()) if x]


def impact_for(title: str, source: str) -> str:
    t = title.lower()
    if any(w in t for w in HIGH_WORDS): return 'high'
    if source == 'Federal Reserve' and ('chair' in t or 'fomc' in t): return 'high'
    if any(w in t for w in MEDIUM_WORDS): return 'medium'
    return 'low'


def make_event(title: str, dt: datetime, source: str, link: str, category: str, impact: str | None = None) -> dict:
    return {
        'title': title,
        'source': source,
        'category': category,
        'impact': impact or impact_for(title, source),
        'scheduled_at': dt.isoformat(),
        'link': link,
        'relevance': ['XAUUSD','BTCUSD'],
    }


def parse_ics_datetime(value: str) -> datetime | None:
    value = value.strip()
    for fmt, size in (('%Y%m%dT%H%M%S',15),('%Y%m%dT%H%M',13),('%Y%m%d',8)):
        try:
            dt = datetime.strptime(value[:size], fmt)
            if fmt == '%Y%m%d': return None
            return dt.replace(tzinfo=ET).astimezone(UTC)
        except ValueError:
            pass
    return None


def parse_bls_ics(now: datetime) -> list[dict]:
    text = re.sub(r'\n[ \t]', '', fetch_text(BLS_ICS).replace('\r\n','\n'))
    out = []
    for block in text.split('BEGIN:VEVENT')[1:]:
        if 'END:VEVENT' not in block: continue
        block = block.split('END:VEVENT',1)[0]
        summary = re.search(r'(?m)^SUMMARY(?:;[^:]*)?:(.+)$', block)
        start = re.search(r'(?m)^DTSTART(?:;[^:]*)?:(.+)$', block)
        if not summary or not start: continue
        dt = parse_ics_datetime(start.group(1))
        if dt and now - timedelta(hours=8) <= dt <= now + timedelta(days=14):
            out.append(make_event(summary.group(1).strip(), dt, 'BLS', 'https://www.bls.gov/schedule/', 'macro'))
    return out


def parse_bls_html_month(year: int, month: int, now: datetime) -> list[dict]:
    url = BLS_MONTH.format(year=year, month=month)
    lines = clean_text(fetch_text(url))
    out = []
    date_rx = re.compile(
        r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+'
        r'(\d{1,2}),\s+(\d{4})$', re.I)
    time_rx = re.compile(r'^(\d{1,2}:\d{2})\s+([AP]M)$', re.I)
    for i, line in enumerate(lines[:-2]):
        dm = date_rx.match(line)
        tm = time_rx.match(lines[i+1]) if dm else None
        if not dm or not tm: continue
        title = lines[i+2]
        clock = datetime.strptime(f'{tm.group(1)} {tm.group(2).upper()}', '%I:%M %p').time()
        local = datetime(int(dm.group(3)), MONTHS[dm.group(1).title()], int(dm.group(2)), clock.hour, clock.minute, tzinfo=ET)
        dt = local.astimezone(UTC)
        if now - timedelta(hours=8) <= dt <= now + timedelta(days=14):
            out.append(make_event(title, dt, 'BLS', url, 'macro'))
    return out


def parse_bls_checked_fallback(now: datetime) -> list[dict]:
    if not BLS_FALLBACK.exists(): return []
    data = json.loads(BLS_FALLBACK.read_text(encoding='utf-8'))
    link = data.get('source_url','https://www.bls.gov/schedule/')
    out = []
    for row in data.get('events',[]):
        try:
            dt = datetime.fromisoformat(row['local']).replace(tzinfo=ET).astimezone(UTC)
        except Exception:
            continue
        if now - timedelta(hours=8) <= dt <= now + timedelta(days=14):
            out.append(make_event(row['title'], dt, 'BLS', link, 'macro', row.get('impact')))
    return out


def parse_bls(now: datetime) -> tuple[list[dict], str]:
    try:
        items = parse_bls_ics(now)
        if items: return items, 'live_ics'
    except Exception:
        pass
    local = now.astimezone(ET)
    try:
        items = []
        for offset in (0,1):
            y = local.year + (local.month + offset - 1)//12
            m = (local.month + offset - 1)%12 + 1
            items.extend(parse_bls_html_month(y,m,now))
        if items: return items, 'live_html'
    except Exception:
        pass
    return parse_bls_checked_fallback(now), 'checked_fallback'


def parse_bea(now: datetime) -> list[dict]:
    lines = clean_text(fetch_text(BEA_SCHEDULE))
    out = []
    # BEA's text extraction can place month/day/time on one line.
    rx = re.compile(r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\s+(\d{1,2}:\d{2}\s+[AP]M)$', re.I)
    for i,line in enumerate(lines):
        m = rx.match(line)
        if not m: continue
        clock = datetime.strptime(m.group(3).upper(), '%I:%M %p').time()
        local = datetime(now.astimezone(ET).year, MONTHS[m.group(1).title()], int(m.group(2)), clock.hour, clock.minute, tzinfo=ET)
        dt = local.astimezone(UTC)
        if not (now - timedelta(hours=8) <= dt <= now + timedelta(days=14)): continue
        title = next((c for c in lines[i+1:i+8] if len(c)>=8 and c.lower() not in {'news','data','article','view'} and not c.startswith('Release Schedule')), '')
        if title: out.append(make_event(title, dt, 'BEA', BEA_SCHEDULE, 'macro'))
    return out


def parse_fed_month(year: int, month: int, now: datetime) -> list[dict]:
    url = FED_MONTH.format(year=year, month=MONTH_NAMES[month-1].lower())
    try: lines = clean_text(fetch_text(url))
    except Exception: return []
    out = []
    time_rx = re.compile(r'^(\d{1,2}:\d{2})\s*([ap])\.m\.$', re.I)
    for i,line in enumerate(lines):
        tm = time_rx.match(line)
        if not tm: continue
        title, day = '', None
        for candidate in lines[i+1:i+12]:
            if not title and (candidate.lower().startswith('speech') or candidate.lower().startswith('fomc')): title = candidate
            if re.fullmatch(r'\d{1,2}', candidate):
                d = int(candidate)
                if 1 <= d <= 31: day = d; break
        if not title or day is None: continue
        clock = datetime.strptime(f'{tm.group(1)} {tm.group(2).upper()}M','%I:%M %p').time()
        try: local = datetime(year,month,day,clock.hour,clock.minute,tzinfo=ET)
        except ValueError: continue
        dt = local.astimezone(UTC)
        if now - timedelta(hours=8) <= dt <= now + timedelta(days=14):
            out.append(make_event(title, dt, 'Federal Reserve', url, 'fed'))
    return out


def risk_state(minutes: int, impact: str) -> str:
    if -30 <= minutes <= 30: return 'ACTIVE'
    if 0 < minutes <= 90 and impact == 'high': return 'HIGH'
    if 0 < minutes <= 240 and impact in ('high','medium'): return 'ELEVATED'
    if 0 < minutes <= 1440: return 'WATCH'
    if -120 <= minutes < -30 and impact == 'high': return 'POST-EVENT'
    return 'SCHEDULED'


def main() -> None:
    now = datetime.now(UTC)
    errors, items = [], []
    bls_mode = 'unavailable'
    try:
        bls_items, bls_mode = parse_bls(now)
        items.extend(bls_items)
        if not bls_items: errors.append({'source':'BLS','error':'No BLS events available from live endpoints or checked fallback in the current horizon.'})
    except Exception as exc:
        errors.append({'source':'BLS','error':str(exc)[:180]})
    try: items.extend(parse_bea(now))
    except Exception as exc: errors.append({'source':'BEA','error':str(exc)[:180]})

    local = now.astimezone(ET)
    for offset in (0,1):
        y = local.year + (local.month + offset - 1)//12
        m = (local.month + offset - 1)%12 + 1
        try: items.extend(parse_fed_month(y,m,now))
        except Exception as exc: errors.append({'source':f'Federal Reserve {y}-{m:02d}','error':str(exc)[:180]})

    dedup = {}
    for x in items:
        dedup[(re.sub(r'\W+',' ',x['title'].lower()).strip(),x['scheduled_at'])] = x
    items = sorted(dedup.values(), key=lambda x:x['scheduled_at'])
    for x in items:
        mins = int((datetime.fromisoformat(x['scheduled_at'])-now).total_seconds()//60)
        x['minutes_from_now'] = mins
        x['risk_state'] = risk_state(mins,x['impact'])
        if mins >= 0:
            x['countdown'] = f'{mins}m' if mins < 60 else (f'{mins//60}h {mins%60}m' if mins < 1440 else f'{mins//1440}d {(mins%1440)//60}h')
        else:
            x['countdown'] = 'released' if mins > -120 else 'past'

    visible = [x for x in items if x['impact'] in ('high','medium')][:32]
    urgent = [x for x in visible if x['risk_state'] in ('ACTIVE','HIGH','ELEVATED','POST-EVENT')]
    nearest = next((x for x in visible if x['minutes_from_now'] >= -120),None)
    out = {
        'version':'1.2',
        'status':'active' if visible else ('degraded' if errors else 'clear'),
        'updated_at':now.isoformat(),
        'horizon_days':14,
        'sources':['U.S. Bureau of Labor Statistics','U.S. Bureau of Economic Analysis','Federal Reserve Board'],
        'source_modes':{'BLS':bls_mode},
        'urgent':urgent[:8],
        'nearest':nearest,
        'events':visible,
        'source_errors':errors,
        'notice':'Event risk is contextual information, not a trading instruction. Times can change at the source; verify critical releases with the linked official source.'
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Event Risk Shield: {len(visible)} market-relevant events, urgent={len(urgent)}, errors={len(errors)}, bls={bls_mode}')


if __name__ == '__main__': main()
