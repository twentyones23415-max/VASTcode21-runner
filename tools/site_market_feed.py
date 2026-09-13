#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/context_sources.json'
OUT=ROOT/'site/data/market_intelligence.json'
UA='VASTcode21-MarketMonitor/1.1 (+https://github.com/twentyones23415-max/VASTcode21-runner)'

GOLD_MARKET_WORDS={
    'price','prices','market','markets','futures','bullion','ounce','ounces','metal','metals',
    'demand','reserve','reserves','central bank','investor','investors','etf','rally','rallies',
    'rise','rises','rising','gain','gains','climb','climbs','fall','falls','falling','drop','drops',
    'slip','slips','forecast','outlook','record high','safe haven','dollar','yield','yields','fed',
    'inflation','rates','rate cut','geopolitical','tariff','treasury'
}
CRYPTO_MARKET_WORDS={
    'price','prices','market','markets','etf','exchange','regulation','regulatory','institutional',
    'treasury','reserve','reserves','miner','miners','mining','wallet','on-chain','liquidity',
    'futures','options','funding','volatility','rally','falls','rises','drops','gains','outlook',
    'adoption','stablecoin','hack','custody'
}

def text(node, name):
    e=node.find(name)
    return (e.text or '').strip() if e is not None and e.text else ''

def age_string(dt):
    if not dt: return ''
    now=datetime.now(timezone.utc); d=max(0,int((now-dt).total_seconds()))
    if d<3600: return f'{max(1,d//60)}m ago'
    if d<86400: return f'{d//3600}h ago'
    return f'{d//86400}d ago'

def parse_date(raw):
    if not raw: return None
    try:
        dt=parsedate_to_datetime(raw)
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        try: return datetime.fromisoformat(raw.replace('Z','+00:00')).astimezone(timezone.utc)
        except Exception: return None

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/rss+xml, application/xml, text/xml;q=0.9, */*;q=0.8'})
    with urllib.request.urlopen(req,timeout=20) as r: return r.read()

def source_name(item, fallback):
    src=item.find('source')
    if src is not None and src.text: return src.text.strip()
    title=text(item,'title')
    if ' - ' in title: return title.rsplit(' - ',1)[-1][:70]
    return fallback.replace('_',' ').title()

def relevant(title: str, feed_name: str) -> bool:
    t=' '.join(title.lower().split())
    name=feed_name.lower()
    if 'fed' in name:
        return True
    if 'gold' in name:
        if 'xau' in t or 'bullion' in t or 'precious metal' in t:
            return True
        if 'gold' not in t:
            return False
        return any(word in t for word in GOLD_MARKET_WORDS)
    if 'bitcoin' in name:
        if 'bitcoin' in t or ' btc' in f' {t}' or t.startswith('btc'):
            return True
        if 'crypto' in t:
            return any(word in t for word in CRYPTO_MARKET_WORDS)
        return False
    return True

def main():
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    feeds=cfg.get('news',{}).get('rss',[])
    items=[]; errors=[]
    for f in feeds:
        try:
            root=ET.fromstring(fetch(f['url']))
            found=root.findall('.//item')
            for it in found[:30]:
                title=text(it,'title'); link=text(it,'link')
                if not title or not link or not relevant(title, f.get('name','')):
                    continue
                dt=parse_date(text(it,'pubDate') or text(it,'date'))
                category=f.get('category','market_news')
                if 'gold' in f.get('name',''): category='gold / macro'
                elif 'bitcoin' in f.get('name',''): category='bitcoin / crypto'
                elif 'fed' in f.get('name',''): category='fed / macro'
                items.append({'title':title,'link':link,'source':source_name(it,f.get('name','source')),'category':category,'published_at':dt.isoformat() if dt else None,'age':age_string(dt)})
        except Exception as e:
            errors.append({'feed':f.get('name','unknown'),'error':str(e)[:180]})
    seen=set(); clean=[]
    items.sort(key=lambda x:x.get('published_at') or '',reverse=True)
    for x in items:
        k=' '.join(x['title'].lower().split())
        if k in seen: continue
        seen.add(k); clean.append(x)
        if len(clean)>=16: break
    out={'version':'1.1','status':'active' if clean else 'degraded','updated_at':datetime.now(timezone.utc).isoformat(),'scope':['XAUUSD','BTCUSD','macro'],'items':clean,'feed_errors':errors}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Published {len(clean)} relevant public market-intelligence headlines; errors={len(errors)}')

if __name__=='__main__': main()
