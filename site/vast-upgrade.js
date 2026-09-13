(()=>{
  const EARLY='https://eepurl.com/cN6dWhHhtP';
  const MENTOR_DM='https://ig.me/m/vast.code21';
  const NEWS_FEED='https://raw.githubusercontent.com/twentyones23415-max/VASTcode21-runner/main/site/data/market_intelligence.json';
  const progress=42;
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];

  function fixBrand(){
    const brand=q('.brand');
    const mark=q('.brand .mark');
    if(mark) mark.innerHTML='<img src="logo-original.webp" alt="VASTcode21 logo" width="34" height="34">';
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

  function mentorSection(){
    if(q('#mentor')) return;
    const services=q('#services'); if(!services) return;
    const s=document.createElement('section');
    s.id='mentor'; s.className='mentor-section';
    s.innerHTML=`<div class="shell">
      <div class="mentor-hero">
        <div class="mentor-copy">
          <div class="eyebrow">VAST Mentor · Personal Trading Education</div>
          <h2>Your own learning path.<br><span>One step at a time.</span></h2>
          <p>Private, structured education for traders who want to understand MT5, market context, risk discipline and the VAST workflow without depending on signals. The goal is to make you more independent, not more dependent.</p>
          <div class="mentor-chips"><span>1-to-1 guidance</span><span>MT5 practice</span><span>XAUUSD / BTCUSD context</span><span>Progress tracking</span></div>
          <a class="btn primary mentor-main-cta" href="${MENTOR_DM}" target="_blank" rel="noopener noreferrer">Apply for VAST Mentor ↗</a>
          <div class="mentor-note">Educational coaching only · No account management · No personalized investment advice</div>
        </div>
        <div class="mentor-map">
          <div class="mentor-map-head"><span>Your learning path</span><b>PERSONALIZED</b></div>
          <div class="mentor-level active"><i>01</i><div><b>Foundation</b><span>MT5, order types, platform hygiene</span></div><em>START</em></div>
          <div class="mentor-rail"><span style="width:38%"></span></div>
          <div class="mentor-level"><i>02</i><div><b>Market structure</b><span>XAUUSD / BTCUSD context and volatility</span></div><em>NEXT</em></div>
          <div class="mentor-level"><i>03</i><div><b>Risk discipline</b><span>Position sizing, limits and journaling</span></div><em>LOCKED</em></div>
          <div class="mentor-level"><i>04</i><div><b>VAST workflow</b><span>Buy · Sell · Exit · Wait states</span></div><em>LOCKED</em></div>
          <div class="mentor-level"><i>05</i><div><b>Independent review</b><span>Build your own repeatable routine</span></div><em>GOAL</em></div>
          <div class="mentor-map-foot"><span>Progress is based on completed learning milestones, not trading P&amp;L.</span></div>
        </div>
      </div>

      <div class="mentor-plans">
        <article class="mentor-plan">
          <div class="tag">Private session</div>
          <h3>VAST Mentor 1:1</h3>
          <div class="mentor-price">€79 <small>/ 50 min</small></div>
          <p>A focused private lesson built around your current level and the specific skill you want to improve.</p>
          <ul><li>Personal level check</li><li>Live MT5 walkthrough</li><li>One focused topic per session</li><li>Action notes for your next practice block</li></ul>
          <a href="${MENTOR_DM}" target="_blank" rel="noopener noreferrer" class="btn secondary">Request a mentor session ↗</a>
        </article>
        <article class="mentor-plan featured">
          <div class="tag">Structured program</div>
          <h3>4-Week Mentorship</h3>
          <div class="mentor-price">€249 <small>/ 4 weeks</small></div>
          <p>A guided learning track for people who want structure, accountability and measurable educational progress.</p>
          <ul><li>4 private mentor sessions</li><li>Personal learning roadmap</li><li>MT5 + risk + market-context curriculum</li><li>Weekly practice objectives</li><li>End-of-program review</li></ul>
          <a href="${MENTOR_DM}" target="_blank" rel="noopener noreferrer" class="btn primary">Apply for 4-week track ↗</a>
        </article>
        <article class="mentor-plan planned">
          <div class="tag">In development</div>
          <h3>VAST Tutor AI</h3>
          <div class="mentor-price">24/7 <small>study companion</small></div>
          <p>A future on-site learning assistant for explanations, quizzes and guided practice. It is not being sold until the experience is genuinely functional.</p>
          <ul><li>Concept explanations</li><li>Practice questions</li><li>Personal lesson checkpoints</li><li>Educational use only</li></ul>
          <a href="${EARLY}" target="_blank" rel="noopener noreferrer" class="btn secondary">Join development updates ↗</a>
        </article>
      </div>
    </div>`;
    services.insertAdjacentElement('afterend',s);
  }

  function mentorFaq(){
    const questions=q('#faq .questions'); if(!questions || q('[data-mentor-faq]',questions)) return;
    const block=document.createElement('div'); block.setAttribute('data-mentor-faq','true');
    block.innerHTML=`<details><summary>What is VAST Mentor?</summary><p>VAST Mentor is private trading education focused on MT5 skills, market context, risk discipline and a structured VAST workflow. It is coaching and education, not a signal service or investment-advisory relationship.</p></details><details><summary>Do I need to be an experienced trader?</summary><p>No. The learning path starts from your actual level. Beginners can start with platform and risk foundations; more experienced users can focus on systematic workflow, validation and execution discipline.</p></details><details><summary>Does mentorship tell me what to buy or sell?</summary><p>No. The service teaches process, tools and decision discipline. It does not provide personalized buy/sell instructions, manage accounts or promise trading outcomes.</p></details>`;
    [...block.children].forEach(x=>questions.appendChild(x));
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
    const faq=q('a[href="#faq"]',links);
    if(!q('a[href="#mentor"]',links)){
      const a=document.createElement('a');a.href='#mentor';a.textContent='Mentor';links.insertBefore(a,faq||links.lastElementChild);
    }
    if(!q('a[href="#markets"]',links)){
      const a=document.createElement('a');a.href='#markets';a.textContent='Markets';links.insertBefore(a,faq||links.lastElementChild);
    }
  }

  document.addEventListener('DOMContentLoaded',()=>{fixBrand();fixEarlyAccess();cleanInternalStatus();mentorSection();mentorFaq();addProgress();marketSection();addNavLinks();});
})();