(()=>{
  const EARLY='https://eepurl.com/cN6dWhHhtP';
  const NEWS_FEED='https://raw.githubusercontent.com/twentyones23415-max/VASTcode21-runner/main/site/data/market_intelligence.json';
  const progress=42;
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];

  function fixBrand(){
    const brand=q('.brand');
    const mark=q('.brand .mark');
    if(mark) mark.innerHTML='<img src="logo-mark.svg" alt="" width="34" height="34">';
    if(brand) brand.title='VASTcode21';
  }

  function fixEarlyAccess(){
    qa('a').forEach(a=>{
      const t=(a.textContent||'').toLowerCase();
      const h=a.getAttribute('href')||'';
      if(t.includes('early access') || h.includes('VAST%20Early%20Access')){
        a.href=EARLY; a.target='_blank'; a.rel='noopener noreferrer';
      }
    });
  }

  function cleanInternalStatus(){
    qa('.metric').forEach(m=>{
      const label=q('span',m);
      if(label && label.textContent.trim().toLowerCase()==='paid ads'){
        label.textContent='Market watch'; const b=q('b',m); if(b)b.textContent='24/7';
      }
    });
    qa('.manifesto .state').forEach(s=>{
      const label=q('span',s);
      if(label && label.textContent.trim().toLowerCase()==='paid ads') s.remove();
    });
  }

  function addProgress(){
    const p=q('.process'); if(!p || q('.roadmap-progress',p)) return;
    const box=document.createElement('div');
    box.className='roadmap-progress';
    box.innerHTML=`<div class="roadmap-head"><div><span>Roadmap progress</span><br><strong>${progress}%</strong></div><span>toward release gate · 100%</span></div><div class="roadmap-bar" role="progressbar" aria-label="VAST roadmap progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress}"><div class="roadmap-fill"></div></div><div class="roadmap-note">Milestone-based development progress — not a trading-performance metric.</div>`;
    const steps=q('.steps',p); p.insertBefore(box,steps);
  }

  function marketSection(){
    if(q('#markets')) return;
    const vast=q('#vast'); if(!vast) return;
    const s=document.createElement('section'); s.id='markets'; s.className='market-desk';
    s.innerHTML=`<div class="shell"><div class="section-head"><div><div class="eyebrow">VASTcode21 market desk</div><h2>XAUUSD + BTCUSD.<br>One research view.</h2></div><p>Live market charts sit inside our own VASTcode21 monitoring layer. They are context tools — not trade signals.</p></div><div class="market-grid"><article class="market-card"><div class="market-top"><div class="market-symbol"><i class="pulse-dot"></i><div><b>XAUUSD</b><span>Gold / U.S. Dollar</span></div></div><div class="market-state">MONITORING</div></div><div class="vast-scanline"></div><div class="tv-shell" id="tv-xau"></div><div class="market-badge"><b>VAST PULSE</b> · validation context layer</div></article><article class="market-card"><div class="market-top"><div class="market-symbol"><i class="pulse-dot"></i><div><b>BTCUSD</b><span>Bitcoin / U.S. Dollar</span></div></div><div class="market-state">MONITORING</div></div><div class="vast-scanline"></div><div class="tv-shell" id="tv-btc"></div><div class="market-badge"><b>VAST PULSE</b> · validation context layer</div></article></div><div class="market-disclaimer"><strong>Chart data:</strong> external market-data visualization. VASTcode21 overlays are research/branding elements and do not constitute signals.</div><div class="intel-wrap" id="intelligence"><div class="intel-head"><div><div class="eyebrow">Market Intelligence 24/7</div><div class="intel-live"><i></i> monitoring active</div></div><div class="intel-updated" id="intel-updated">Loading latest monitored headlines…</div></div><div class="news-grid" id="news-grid"><div class="intel-empty">Connecting to the VASTcode21 news monitor…</div></div></div></div>`;
    vast.insertAdjacentElement('afterend',s);
    loadTV('tv-xau','OANDA:XAUUSD');
    loadTV('tv-btc','BITSTAMP:BTCUSD');
    loadNews();
  }

  function loadTV(id,symbol){
    const host=document.getElementById(id); if(!host) return;
    const wrap=document.createElement('div'); wrap.className='tradingview-widget-container'; wrap.style.height='100%'; wrap.style.width='100%';
    const widget=document.createElement('div'); widget.className='tradingview-widget-container__widget'; widget.style.height='100%'; widget.style.width='100%';
    const script=document.createElement('script'); script.type='text/javascript'; script.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'; script.async=true;
    script.text=JSON.stringify({autosize:true,symbol,interval:'60',timezone:'Etc/UTC',theme:'dark',style:'1',locale:'en',allow_symbol_change:false,calendar:false,support_host:'https://www.tradingview.com',backgroundColor:'rgba(5, 12, 19, 1)',gridColor:'rgba(39, 55, 71, 0.28)',hide_top_toolbar:false,hide_legend:false,save_image:false});
    wrap.append(widget,script); host.appendChild(wrap);
  }

  function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  async function loadNews(){
    const grid=q('#news-grid'), updated=q('#intel-updated'); if(!grid) return;
    try{
      const r=await fetch(`${NEWS_FEED}?t=${Date.now()}`,{cache:'no-store'}); if(!r.ok) throw new Error('feed');
      const d=await r.json(); const items=(d.items||[]).slice(0,8);
      if(updated) updated.textContent=d.updated_at?`Last monitor refresh · ${new Date(d.updated_at).toLocaleString()}`:'Monitor active';
      if(!items.length){grid.innerHTML='<div class="intel-empty">Monitor is active; no new qualifying headlines are available in the current window.</div>';return;}
      grid.innerHTML=items.map(x=>`<a class="news-item" href="${esc(x.link)}" target="_blank" rel="noopener noreferrer"><div class="news-meta"><span class="news-tag">${esc((x.category||'market').replaceAll('_',' '))}</span><span>${esc(x.age||'')}</span></div><div class="news-title">${esc(x.title)}</div><div class="news-source">${esc(x.source||'Monitored source')} ↗</div></a>`).join('');
    }catch(e){
      if(updated) updated.textContent='Monitor feed refresh pending';
      grid.innerHTML='<div class="intel-empty">The monitoring engine is running, but the public headline snapshot is temporarily unavailable.</div>';
    }
  }

  function addNavLinks(){
    const links=q('.navlinks'); if(!links) return;
    if(!q('a[href="#markets"]',links)){
      const a=document.createElement('a');a.href='#markets';a.textContent='Markets';
      const faq=q('a[href="#faq"]',links);links.insertBefore(a,faq||links.lastElementChild);
    }
  }

  document.addEventListener('DOMContentLoaded',()=>{fixBrand();fixEarlyAccess();cleanInternalStatus();addProgress();marketSection();addNavLinks();});
})();