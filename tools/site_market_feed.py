#!/usr/bin/env python3
from __future__ import annotations
import json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config/context_sources.json'
OUT=ROOT/'site/data/market_intelligence.json'
UA='VASTcode21-MarketMonitor/1.4 (+https://github.com/twentyones23415-max/VASTcode21-runner)'

GOLD_MARKET_WORDS={
    'price','prices','market','markets','futures','bullion','ounce','ounces','metal','metals','demand',
    'reserve','reserves','central bank','investor','investors','etf','rally','rallies','rise','rises',
    'rising','gain','gains','climb','climbs','fall','falls','falling','drop','drops','slip','slips',
    'forecast','outlook','record high','safe haven','dollar','yield','yields','fed','inflation','rates',
    'rate cut','geopolitical','tariff','treasury'
}
FED_MARKET_WORDS={
    'monetary','fomc','federal open market','interest rate','interest rates','rate cut','rate hike',
    'inflation','economic outlook','economy','employment','labor market','unemployment','gdp',
    'financial conditions','treasury','balance sheet','powell','waller','governor','chair'
}
BLOCKED_SOURCES={
    'facebook.com','instagram.com','tiktok.com','x.com','twitter.com','moomoo.com'
}
LOW_VALUE_TITLE_TERMS={
    'prediction market','crypto prediction market','price range on','price on sep'
}

def text(node, name):
    e=node.find(name)
    return (e.text or '').strip() if e is not None and e.text else ''

def age_string(dt):
    if not dt: return ''
    d=max(0,int((datetime.now(timezone.utc)-dt).total_seconds()))
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
        return any(word in t for word in FED_MARKET_WORDS)
    if 'gold' in name:
        if 'xau' in t or 'bullion' in t or 'precious metal' in t: return True
        return 'gold' in t and any(word in t for word in GOLD_MARKET_WORDS)
    if 'bitcoin' in name:
        return 'bitcoin' in t or ' btc' in f' {t}' or t.startswith('btc')
    return True

def quality_allowed(title: str, source: str) -> bool:
    t=' '.join(title.lower().split())
    s=source.lower().strip()
    if s in BLOCKED_SOURCES:
        return False
    if any(term in t for term in LOW_VALUE_TITLE_TERMS):
        return False
    return True

def main():
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
    feeds=cfg.get('news',{}).get('rss',[])
    items=[]; errors=[]; filtered=0
    for f in feeds:
        try:
            root=ET.fromstring(fetch(f['url']))
            for it in root.findall('.//item')[:40]:
                title=text(it,'title'); link=text(it,'link')
                if not title or not link or not relevant(title,f.get('name','')): continue
                source=source_name(it,f.get('name','') or 'source')
                if not quality_allowed(title,source):
                    filtered+=1
                    continue
                dt=parse_date(text(it,'pubDate') or text(it,'date'))
                name=f.get('name','')
                category='gold / macro' if 'gold' in name else 'bitcoin / crypto' if 'bitcoin' in name else 'fed / macro' if 'fed' in name else f.get('category','market_news')
                items.append({'title':title,'link':link,'source':source,'category':category,'published_at':dt.isoformat() if dt else None,'age':age_string(dt)})
        except Exception as e:
            errors.append({'feed':f.get('name','unknown'),'error':str(e)[:180]})

    items.sort(key=lambda x:x.get('published_at') or '',reverse=True)
    seen=set(); buckets={'gold / macro':[],'bitcoin / crypto':[],'fed / macro':[]}; other=[]
    for x in items:
        k=' '.join(x['title'].lower().split())
        if k in seen: continue
        seen.add(k)
        (buckets.get(x['category'],other)).append(x)

    clean=[]
    # Interleave categories so the visible cards stay balanced: BTC -> GOLD -> macro.
    for i in range(6):
        for cat in ('bitcoin / crypto','gold / macro','fed / macro'):
            if i < len(buckets[cat]): clean.append(buckets[cat][i])
            if len(clean)>=16: break
        if len(clean)>=16: break
    if len(clean)<16:
        leftovers=[]
        for cat in buckets: leftovers.extend(buckets[cat][6:])
        leftovers.extend(other)
        leftovers.sort(key=lambda x:x.get('published_at') or '',reverse=True)
        clean.extend(leftovers[:16-len(clean)])

    out={'version':'1.4','status':'active' if clean else 'degraded','updated_at':datetime.now(timezone.utc).isoformat(),'scope':['XAUUSD','BTCUSD','macro'],'items':clean,'feed_errors':errors,'quality_filtered':filtered}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Published {len(clean)} interleaved market-intelligence headlines; filtered={filtered}; errors={len(errors)}')

if __name__=='__main__': main()
