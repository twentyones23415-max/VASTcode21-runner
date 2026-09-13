(()=>{
  const EVENT_FEED='data/event_risk.json';
  const MARKET_FEED='data/market_intelligence.json';
  const EVENT_MAX_AGE_MS=150*60*1000;
  const NEWS_MAX_AGE_MS=150*60*1000;
  const q=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function clearPlaceholder(slot){slot?.querySelectorAll('.module-empty').forEach(n=>n.remove())}

  function setLabState(label,state,online=false){
    document.querySelectorAll('.lab-state').forEach(row=>{
      const span=q('span',row), b=q('b',row);
      if(span&&b&&span.textContent.trim()===label){b.textContent=state;b.classList.toggle('online',online)}
    });
  }

  function mountVision(){
    if(q('#tutor-ai-lab')) return;
    const slot=q('#vision-slot');
    if(!slot) return;
    clearPlaceholder(slot);
    const s=document.createElement('section');
    s.id='tutor-ai-lab'; s.className='tutor-lab';
    s.innerHTML=`<div class="shell"><div class="tutor-console">
      <div class="tutor-console-main">
        <div class="upload-zone" id="vision-drop" tabindex="0" role="button" aria-label="Choose chart screenshot">
          <input id="vision-file" type="file" accept="image/png,image/jpeg,image/webp" hidden>
          <div class="upload-icon">◇</div><h3>Drop a chart screenshot here</h3>
          <p>PNG, JPG or WEBP · maximum 8 MB</p>
          <button class="btn secondary" type="button" id="vision-choose">Choose screenshot</button>
        </div>
        <div class="vision-preview" id="vision-preview" hidden><img id="vision-img" alt="Local chart screenshot preview"><div class="vision-preview-meta"><div><span>LOCAL PREVIEW</span><b id="vision-name">chart</b></div><button type="button" id="vision-clear">Remove</button></div></div>
        <div class="vision-actionbar"><button class="btn primary" type="button" id="vision-analyze" disabled>Secure AI analysis · checking backend</button><span>Screenshot stays local until you request analysis.</span></div>
      </div>
      <aside class="tutor-console-side">
        <div class="lab-state"><span>VISION ENGINE</span><b>CHECKING</b></div>
        <div class="lab-state"><span>EVENT RISK SHIELD</span><b>CHECKING</b></div>
        <div class="lab-state"><span>NEWS CONTEXT</span><b>CHECKING</b></div>
        <div class="lab-state"><span>LIVE MARKET API</span><b>NOT CONNECTED</b></div>
        <div class="lab-trust"><strong>Trust rule</strong><p>Screenshot evidence and verified context are labelled separately. Missing information stays unknown instead of being invented.</p></div>
      </aside>
    </div></div>`;
    slot.appendChild(s);
    bindUpload();
    loadNewsContext();
  }

  function bindUpload(){
    const input=q('#vision-file'), drop=q('#vision-drop'), choose=q('#vision-choose'), preview=q('#vision-preview'), img=q('#vision-img'), name=q('#vision-name'), clear=q('#vision-clear');
    if(!input||!drop) return;
    let previewUrl='';
    const reset=()=>{
      if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=''}
      img?.removeAttribute('src'); input.value=''; preview.hidden=true; drop.hidden=false;
      document.dispatchEvent(new CustomEvent('vast:vision-cleared'));
    };
    const show=file=>{
      if(!file||!/^image\/(png|jpeg|webp)$/.test(file.type)){alert('Please choose a PNG, JPG or WEBP chart screenshot.');return}
      if(file.size>8*1024*1024){alert('Please use an image smaller than 8 MB.');return}
      if(previewUrl)URL.revokeObjectURL(previewUrl);
      previewUrl=URL.createObjectURL(file);img.src=previewUrl;name.textContent=file.name;preview.hidden=false;drop.hidden=true;
      document.dispatchEvent(new CustomEvent('vast:vision-image-changed'));
    };
    choose?.addEventListener('click',e=>{e.stopPropagation();input.click()});
    drop.addEventListener('click',()=>input.click());
    drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();input.click()}});
    input.addEventListener('change',()=>show(input.files?.[0]));
    ['dragenter','dragover'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add('drag')}));
    ['dragleave','drop'].forEach(evt=>drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove('drag')}));
    drop.addEventListener('drop',e=>{const file=e.dataTransfer?.files?.[0];if(file){try{const dt=new DataTransfer();dt.items.add(file);input.files=dt.files}catch{}show(file)}});
    clear?.addEventListener('click',reset);
  }

  async function loadNewsContext(){
    setLabState('NEWS CONTEXT','CHECKING',false);
    try{
      const r=await fetch(`${MARKET_FEED}?t=${Date.now()}`,{cache:'no-store'});
      if(!r.ok)throw new Error('news feed');
      const d=await r.json();
      const updated=new Date(d.updated_at||0);
      const age=Date.now()-updated.getTime();
      const hasItems=Array.isArray(d.items)&&d.items.length>0;
      const fresh=Number.isFinite(age)&&age>=0&&age<=NEWS_MAX_AGE_MS&&d.status==='active'&&hasItems;
      if(fresh)setLabState('NEWS CONTEXT','VERIFIED',true);
      else setLabState('NEWS CONTEXT','UNAVAILABLE',false);
    }catch{
      setLabState('NEWS CONTEXT','UNAVAILABLE',false);
    }
  }

  function mountContext(){
    if(q('#event-risk-shield')) return;
    const slot=q('#context-slot');
    if(!slot) return;
    clearPlaceholder(slot);
    const s=document.createElement('section');s.id='event-risk-shield';s.className='event-shield';
    s.innerHTML=`<div class="shell"><div class="event-shell"><div class="event-head"><div><div class="eyebrow">VAST Event Risk Shield</div><h2>Verified event context</h2><p>Official-source monitoring for scheduled U.S. macro and Federal Reserve events that can materially affect XAUUSD and BTCUSD volatility.</p></div><div class="risk-orb" id="risk-orb"><span>SCANNING</span><b>—</b></div></div><div class="event-alert" id="event-alert">Checking event-risk freshness…</div><div class="event-grid" id="event-grid"></div><div class="event-foot" id="event-foot">Stale or incomplete data is shown as unavailable.</div></div></div>`;
    slot.appendChild(s);loadEvents();
  }

  async function loadEvents(){
    const alert=q('#event-alert'),grid=q('#event-grid'),orb=q('#risk-orb'),foot=q('#event-foot');if(!grid)return;
    try{
      const r=await fetch(`${EVENT_FEED}?t=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error('events');
      const d=await r.json();const updated=new Date(d.updated_at||0);const age=Date.now()-updated.getTime();const fresh=Number.isFinite(age)&&age>=0&&age<=EVENT_MAX_AGE_MS&&d.status!=='degraded';
      if(!fresh){setLabState('EVENT RISK SHIELD','DEGRADED',false);orb.dataset.state='degraded';orb.innerHTML='<span>EVENT RISK</span><b>DEGRADED</b>';alert.className='event-alert warn';alert.textContent='Verified event-risk data is stale or incomplete. Timing is unavailable until the feed refreshes.';grid.innerHTML='';if(foot)foot.textContent=`Last snapshot: ${Number.isFinite(updated.getTime())?updated.toLocaleString():'unknown'}`;return}
      setLabState('EVENT RISK SHIELD','ONLINE',true);
      const events=(d.events||[]).slice(0,8),n=d.nearest;const urgent=d.urgent||[];let state='CLEAR';if(urgent.some(x=>x.risk_state==='ACTIVE'))state='ACTIVE';else if(urgent.some(x=>x.risk_state==='HIGH'))state='HIGH';else if(urgent.length)state='ELEVATED';else if(n)state='WATCH';
      orb.dataset.state=state.toLowerCase();orb.innerHTML=`<span>EVENT RISK</span><b>${state}</b>`;
      alert.className='event-alert';alert.textContent=n?`${n.title||'Scheduled event'} · ${n.source||'official source'} · ${n.countdown||'timing available'}`:'No qualifying event is inside the current monitoring horizon.';
      grid.innerHTML=events.map(x=>`<a class="event-card impact-${esc(x.impact)}" href="${esc(x.link)}" target="_blank" rel="noopener noreferrer"><div class="event-meta"><span>${esc(x.source)}</span><b>${esc(x.impact).toUpperCase()}</b></div><h3>${esc(x.title)}</h3><div class="event-time"><strong>${esc(x.countdown)}</strong><span>${new Date(x.scheduled_at).toLocaleString()}</span></div><div class="event-state">${esc(x.risk_state)} · official source ↗</div></a>`).join('')||'<div class="intel-empty">No qualifying events in the current window.</div>';
      if(foot)foot.textContent=`Last verified: ${updated.toLocaleString()} · official source remains the final reference.`;
    }catch{setLabState('EVENT RISK SHIELD','DEGRADED',false);orb.dataset.state='degraded';orb.innerHTML='<span>EVENT RISK</span><b>DEGRADED</b>';alert.className='event-alert warn';alert.textContent='Verified event-risk data is temporarily unavailable.';grid.innerHTML=''}
  }

  document.addEventListener('DOMContentLoaded',()=>{mountVision();mountContext()});
})();
