(()=>{
  const EVENT_FEED='https://raw.githubusercontent.com/twentyones23415-max/VASTcode21-runner/main/site/data/event_risk.json';
  const PRODUCT_FEED='data/tutor_product.json';
  const EARLY='https://eepurl.com/cN6dWhHhtP';
  const MENTOR_DM='https://ig.me/m/vast.code21';
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function addTutorLab(){
    if(q('#tutor-ai-lab')) return;
    const mentor=q('#mentor'); if(!mentor) return;
    const s=document.createElement('section');
    s.id='tutor-ai-lab'; s.className='tutor-lab';
    s.innerHTML=`<div class="shell">
      <div class="section-head"><div><div class="eyebrow">VAST Tutor AI · product lab</div><h2>Learn. Upload. Analyze.<br>Review what happened.</h2></div><p>A paid educational AI product being built around structured learning, screenshot analysis, event-risk awareness and prediction-to-outcome review. No fake live mode: features go public only when their backend is genuinely connected.</p></div>
      <div class="tutor-console">
        <div class="tutor-console-main">
          <div class="tutor-modebar"><span class="active">VISION LAB</span><span>TUTOR</span><span>OUTCOME LAB</span><b>PRELAUNCH</b></div>
          <div class="upload-zone" id="vision-drop" tabindex="0" role="button" aria-label="Choose chart screenshot">
            <input id="vision-file" type="file" accept="image/png,image/jpeg,image/webp" hidden>
            <div class="upload-icon">◇</div><h3>Drop a chart screenshot here</h3>
            <p>PNG, JPG or WEBP · local preview only during prelaunch</p>
            <button class="btn secondary" type="button" id="vision-choose">Choose screenshot</button>
          </div>
          <div class="vision-preview" id="vision-preview" hidden><img id="vision-img" alt="Local chart screenshot preview"><div class="vision-preview-meta"><div><span>LOCAL PREVIEW</span><b id="vision-name">chart</b></div><button type="button" id="vision-clear">Remove</button></div></div>
          <div class="vision-actionbar"><button class="btn primary" type="button" id="vision-analyze" disabled>Secure AI analysis · backend required</button><span>Your image is not uploaded by this prototype.</span></div>
        </div>
        <aside class="tutor-console-side">
          <div class="lab-state"><span>VISION ENGINE</span><b>BUILDING</b></div>
          <div class="lab-state"><span>EVENT RISK SHIELD</span><b class="online">ONLINE</b></div>
          <div class="lab-state"><span>NEWS CONTEXT</span><b class="online">ONLINE</b></div>
          <div class="lab-state"><span>LIVE MARKET API</span><b>PLANNED</b></div>
          <div class="lab-state"><span>OUTCOME REVIEW</span><b>PLANNED</b></div>
          <div class="lab-trust"><strong>Trust rule</strong><p>Screenshot evidence, live market data and news context will always be labelled separately. The system must say “unknown” instead of inventing missing information.</p></div>
        </aside>
      </div>
      <div class="tutor-pricing" id="tutor-pricing"><div class="intel-empty">Loading planned paid beta tiers…</div></div>
    </div>`;
    mentor.insertAdjacentElement('afterend',s);
    bindUpload();
    loadProduct();
  }

  function bindUpload(){
    const input=q('#vision-file'), drop=q('#vision-drop'), choose=q('#vision-choose'), preview=q('#vision-preview'), img=q('#vision-img'), name=q('#vision-name'), clear=q('#vision-clear');
    if(!input||!drop) return;
    const show=file=>{
      if(!file || !/^image\/(png|jpeg|webp)$/.test(file.type)){ alert('Please choose a PNG, JPG or WEBP chart screenshot.'); return; }
      if(file.size>12*1024*1024){ alert('Please use an image smaller than 12 MB.'); return; }
      const url=URL.createObjectURL(file); img.src=url; name.textContent=file.name; preview.hidden=false; drop.hidden=true;
    };
    choose?.addEventListener('click',e=>{e.stopPropagation();input.click()});
    drop.addEventListener('click',()=>input.click());
    drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();input.click()}});
    input.addEventListener('change',()=>show(input.files?.[0]));
    ['dragenter','dragover'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add('drag')}));
    ['dragleave','drop'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove('drag')}));
    drop.addEventListener('drop',e=>show(e.dataTransfer?.files?.[0]));
    clear?.addEventListener('click',()=>{if(img.src.startsWith('blob:'))URL.revokeObjectURL(img.src);img.removeAttribute('src');input.value='';preview.hidden=true;drop.hidden=false});
  }

  async function loadProduct(){
    const host=q('#tutor-pricing'); if(!host) return;
    try{
      const r=await fetch(`${PRODUCT_FEED}?t=${Date.now()}`,{cache:'no-store'}); if(!r.ok) throw new Error('product');
      const d=await r.json();
      host.innerHTML=(d.pricing||[]).map((p,i)=>`<article class="tutor-tier ${i===1?'featured':''}"><div class="tag">${i===1?'Most balanced':'Paid beta plan'}</div><h3>${esc(p.name)}</h3><div class="tier-price">€${esc(p.price_eur_month)} <small>/ month</small></div><div class="tier-credit">${esc(p.screenshot_analyses_month)} Vision analyses / month</div><ul>${(p.features||[]).map(x=>`<li>✓ ${esc(x)}</li>`).join('')}</ul><a class="btn ${i===1?'primary':'secondary'}" href="${EARLY}" target="_blank" rel="noopener noreferrer">Join paid-beta updates ↗</a><div class="micro">Checkout stays closed until the advertised AI features are genuinely functional.</div></article>`).join('');
    }catch(e){host.innerHTML='<div class="intel-empty">Paid beta configuration is temporarily unavailable.</div>'}
  }

  function eventShield(){
    if(q('#event-risk-shield')) return;
    const markets=q('#markets'); if(!markets) return;
    const s=document.createElement('section'); s.id='event-risk-shield'; s.className='event-shield';
    s.innerHTML=`<div class="shell"><div class="event-shell"><div class="event-head"><div><div class="eyebrow">VAST Event Risk Shield</div><h2>Know what can hit the market next.</h2><p>Official-source monitoring for scheduled U.S. macro and Federal Reserve events that can materially change volatility in XAUUSD and BTCUSD.</p></div><div class="risk-orb" id="risk-orb"><span>SCANNING</span><b>—</b></div></div><div class="event-alert" id="event-alert">Connecting to official event calendars…</div><div class="event-grid" id="event-grid"></div><div class="event-foot">Sources are checked automatically. Critical release times can change; the linked official source remains the final reference.</div></div></div>`;
    markets.insertAdjacentElement('afterend',s);
    loadEvents();
  }

  async function loadEvents(){
    const alert=q('#event-alert'), grid=q('#event-grid'), orb=q('#risk-orb'); if(!grid) return;
    try{
      const r=await fetch(`${EVENT_FEED}?t=${Date.now()}`,{cache:'no-store'}); if(!r.ok) throw new Error('events');
      const d=await r.json(); const urgent=d.urgent||[], events=(d.events||[]).slice(0,8), n=d.nearest;
      let state='CLEAR';
      if(urgent.some(x=>x.risk_state==='ACTIVE')) state='ACTIVE'; else if(urgent.some(x=>x.risk_state==='HIGH')) state='HIGH'; else if(urgent.length) state='ELEVATED'; else if(n) state='WATCH';
      orb.dataset.state=state.toLowerCase(); orb.innerHTML=`<span>EVENT RISK</span><b>${state}</b>`;
      if(n){
        const when=n.minutes_from_now>=0?`in ${esc(n.countdown)}`:'recently released';
        alert.className=`event-alert ${['ACTIVE','HIGH','ELEVATED'].includes(n.risk_state)?'warn':''}`;
        alert.innerHTML=`<strong>${esc(n.risk_state)}</strong><span>${esc(n.title)} · ${esc(n.source)} · ${when}</span>`;
      } else alert.textContent='No medium/high-impact official-source event is currently inside the monitoring horizon.';
      grid.innerHTML=events.map(x=>`<a class="event-card impact-${esc(x.impact)}" href="${esc(x.link)}" target="_blank" rel="noopener noreferrer"><div class="event-meta"><span>${esc(x.source)}</span><b>${esc(x.impact).toUpperCase()}</b></div><h3>${esc(x.title)}</h3><div class="event-time"><strong>${esc(x.countdown)}</strong><span>${new Date(x.scheduled_at).toLocaleString()}</span></div><div class="event-state">${esc(x.risk_state)} · official source ↗</div></a>`).join('') || '<div class="intel-empty">No qualifying events in the current 14-day window.</div>';
    }catch(e){
      orb.innerHTML='<span>EVENT RISK</span><b>DEGRADED</b>'; alert.textContent='Official event-risk snapshot is temporarily unavailable.'; grid.innerHTML='';
    }
  }

  function nav(){
    const links=q('.navlinks'); if(!links) return; const faq=q('a[href="#faq"]',links);
    if(!q('a[href="#tutor-ai-lab"]',links)){const a=document.createElement('a');a.href='#tutor-ai-lab';a.textContent='Tutor AI';links.insertBefore(a,faq||links.lastElementChild)}
  }

  document.addEventListener('DOMContentLoaded',()=>{addTutorLab();eventShield();nav()});
})();
