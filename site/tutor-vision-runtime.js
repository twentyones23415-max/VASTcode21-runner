(()=>{
  const CONFIG='data/tutor_runtime.json';
  const q=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let runtime=null;

  function baseUrl(value){
    const raw=String(value||'').trim().replace(/\/$/,'');
    if(!raw) return '';
    try{
      const u=new URL(raw);
      if(u.protocol!=='https:' && !['localhost','127.0.0.1'].includes(u.hostname)) return '';
      return u.origin + u.pathname.replace(/\/$/,'');
    }catch(_){return ''}
  }

  function setVisionState(text,online=false){
    document.querySelectorAll('.lab-state').forEach(row=>{
      const label=q('span',row), value=q('b',row);
      if(label?.textContent.trim()==='VISION ENGINE' && value){
        value.textContent=text;
        value.classList.toggle('online',online);
      }
    });
  }

  function ensureResultHost(){
    let host=q('#vision-runtime-result');
    if(host) return host;
    const bar=q('.vision-actionbar');
    if(!bar) return null;
    host=document.createElement('div');
    host.id='vision-runtime-result';
    host.style.cssText='margin-top:16px;padding:18px;border:1px solid #26364d;border-radius:16px;background:#0d1726;display:none';
    bar.insertAdjacentElement('afterend',host);
    return host;
  }

  function status(message,kind='info'){
    const host=ensureResultHost(); if(!host) return;
    host.style.display='block';
    host.innerHTML=`<div style="font-weight:800;margin-bottom:6px">${kind==='error'?'Vision unavailable':'VAST Vision AI'}</div><div style="color:#b8c4d2">${esc(message)}</div>`;
  }

  function list(items){
    return `<ul>${(items||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
  }

  function render(payload){
    const host=ensureResultHost(); if(!host) return;
    const a=payload?.analysis||{};
    const ctx=payload?.context||{};
    const scenarios=a.scenarios||{};
    const scenario=name=>{
      const s=scenarios[name]||{};
      return `<article style="padding:14px;border:1px solid #26364d;border-radius:12px;margin:10px 0"><strong>${name.toUpperCase()}</strong><div><b>Evidence</b>${list(s.evidence)}</div><div><b>Invalidation</b>${list(s.invalidation)}</div></article>`;
    };
    host.style.display='block';
    host.innerHTML=`
      <div style="font-weight:800;font-size:18px;margin-bottom:8px">VAST Vision AI · educational review</div>
      <div style="color:#b8c4d2;margin-bottom:12px">Detected: <b>${esc(a.symbol||'unknown')}</b> · timeframe <b>${esc(a.timeframe||'unknown')}</b></div>
      <p><strong>Visible structure</strong><br>${esc(a.visible_structure||'unknown')}</p>
      ${scenario('bullish')}${scenario('bearish')}${scenario('neutral')}
      <p><strong>Uncertainty</strong><br>${esc(a.uncertainty||'unknown')}</p>
      <p><strong>Educational takeaway</strong><br>${esc(a.educational_takeaway||'')}</p>
      <div style="margin-top:14px;padding-top:12px;border-top:1px solid #26364d;color:#9fb0c4;font-size:13px">
        Event risk: ${esc(ctx.event_risk?.status||'unknown')} · Market prices: ${esc(ctx.market?.status||'unknown')} · News context: ${esc(ctx.market_intelligence?.status||'unknown')}<br>
        Privacy: ${payload?.privacy?.stored===false?'screenshot not stored':'unknown'} · ${esc(payload?.notice||'Educational use only.')}
      </div>`;
  }

  function fileToDataUrl(file){
    return new Promise((resolve,reject)=>{
      const r=new FileReader(); r.onload=()=>resolve(r.result); r.onerror=()=>reject(new Error('Could not read screenshot')); r.readAsDataURL(file);
    });
  }

  async function analyze(){
    const input=q('#vision-file'), btn=q('#vision-analyze');
    const file=input?.files?.[0];
    if(!file){status('Choose a chart screenshot first.','error');return}
    if(!runtime?.base){status('Secure Vision backend is not connected.','error');return}
    btn.disabled=true; btn.textContent='Analyzing securely…';
    try{
      const image_data_url=await fileToDataUrl(file);
      const r=await fetch(`${runtime.base}/v1/vision/analyze`,{
        method:'POST',cache:'no-store',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({image_data_url})
      });
      const d=await r.json().catch(()=>({}));
      if(!r.ok) throw new Error(d.detail||d.error||`Backend HTTP ${r.status}`);
      render(d);
    }catch(e){status(`Analysis could not be completed: ${e.message||e}`,'error')}
    finally{btn.disabled=false;btn.textContent='Analyze screenshot securely'}
  }

  async function init(){
    const btn=q('#vision-analyze'); if(!btn) return;
    ensureResultHost();
    btn.addEventListener('click',analyze);
    try{
      const cr=await fetch(`${CONFIG}?t=${Date.now()}`,{cache:'no-store'});
      if(!cr.ok) throw new Error('runtime config unavailable');
      const cfg=await cr.json();
      const base=baseUrl(cfg.vision_backend_base_url);
      if(cfg.enabled!==true || !base){
        setVisionState('BACKEND NEEDED',false);
        btn.disabled=true; btn.textContent='Secure AI analysis · backend required';
        return;
      }
      const hr=await fetch(`${base}/healthz`,{cache:'no-store'});
      const health=await hr.json().catch(()=>({}));
      if(!hr.ok || health.ok!==true || health.vision_provider_configured!==true) throw new Error('backend not ready');
      runtime={base,health};
      setVisionState('ONLINE',true);
      btn.disabled=false; btn.textContent='Analyze screenshot securely';
      const note=q('.vision-actionbar span'); if(note) note.textContent='Screenshot is sent only to the configured VAST Vision backend for this request and is not retained by the beta server.';
    }catch(e){
      runtime=null; setVisionState('DEGRADED',false); btn.disabled=true; btn.textContent='Secure AI analysis · temporarily unavailable';
    }
  }

  document.addEventListener('DOMContentLoaded',()=>setTimeout(init,0));
})();
