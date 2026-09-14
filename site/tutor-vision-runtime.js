(()=>{
  const CONFIG='data/tutor_runtime.json';
  const SESSION_KEY='vast_tutor_supabase_session_v1';
  const MAX_IMAGE_BYTES=8*1024*1024;
  const REQUEST_TIMEOUT_MS=30000;
  const CONFIG_TIMEOUT_MS=10000;
  const ALLOWED_IMAGE_TYPES=new Set(['image/png','image/jpeg','image/webp']);
  const q=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let runtime=null;
  let session=null;

  function httpsUrl(value){
    try{
      const u=new URL(String(value||'').trim());
      if(u.protocol!=='https:' && !['localhost','127.0.0.1'].includes(u.hostname)) return '';
      return u.href.replace(/\/$/,'');
    }catch(_){return ''}
  }

  async function timedFetch(url,options={},timeoutMs=REQUEST_TIMEOUT_MS){
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),timeoutMs);
    try{return await fetch(url,{...options,signal:controller.signal})}
    catch(e){if(e?.name==='AbortError')throw new Error('REQUEST_TIMEOUT');throw e}
    finally{clearTimeout(timer)}
  }

  function loadSession(){
    try{return JSON.parse(localStorage.getItem(SESSION_KEY)||'null')}catch{return null}
  }
  function saveSession(value){
    session=value||null;
    try{
      if(session)localStorage.setItem(SESSION_KEY,JSON.stringify(session));
      else localStorage.removeItem(SESSION_KEY);
    }catch{}
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

  function authPanel(message='Sign in to use secure Vision analysis and private history.'){
    const host=ensureResultHost(); if(!host) return;
    host.style.display='block';
    host.innerHTML=`<div style="font-weight:800;font-size:18px;margin-bottom:7px">VAST Tutor Beta · secure sign in</div>
      <div style="color:#b8c4d2;margin-bottom:14px">${esc(message)}</div>
      <div style="display:grid;gap:10px;max-width:440px">
        <input id="vast-auth-email" type="email" autocomplete="email" placeholder="Email" style="padding:12px;border-radius:10px;border:1px solid #31455f;background:#07111d;color:#eef3f8">
        <input id="vast-auth-password" type="password" autocomplete="current-password" minlength="8" placeholder="Password · minimum 8 characters" style="padding:12px;border-radius:10px;border:1px solid #31455f;background:#07111d;color:#eef3f8">
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn primary" type="button" id="vast-auth-login">Sign in</button><button class="btn secondary" type="button" id="vast-auth-signup">Create beta account</button></div>
        <div id="vast-auth-note" style="color:#8294a8;font-size:12px">Credentials go directly to the connected Supabase Auth service over HTTPS. Passwords are never sent to GitHub or stored by this page.</div>
      </div>`;
    q('#vast-auth-login')?.addEventListener('click',()=>authSubmit('login'));
    q('#vast-auth-signup')?.addEventListener('click',()=>authSubmit('signup'));
  }

  async function authRequest(path,body){
    const r=await timedFetch(`${runtime.supabase}${path}`,{
      method:'POST',cache:'no-store',
      headers:{'Content-Type':'application/json','apikey':runtime.key},
      body:JSON.stringify(body)
    });
    const d=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(d.msg||d.message||d.error_description||d.error||`Auth HTTP ${r.status}`);
    return d;
  }

  async function authSubmit(mode){
    const email=q('#vast-auth-email')?.value.trim();
    const password=q('#vast-auth-password')?.value||'';
    const note=q('#vast-auth-note');
    if(!email || password.length<8){if(note)note.textContent='Enter a valid email and a password with at least 8 characters.';return}
    if(note)note.textContent=mode==='signup'?'Creating secure beta account…':'Signing in…';
    try{
      const d=mode==='signup'
        ? await authRequest('/auth/v1/signup',{email,password})
        : await authRequest('/auth/v1/token?grant_type=password',{email,password});
      if(d.access_token){
        saveSession({access_token:d.access_token,refresh_token:d.refresh_token,expires_at:Math.floor(Date.now()/1000)+(Number(d.expires_in)||3600),user:d.user||null});
        await refreshVisionHealth();
      }else{
        authPanel('Account created. Check your email for the Supabase confirmation message, then return here and sign in.');
      }
    }catch(e){
      if(note)note.textContent=(e.message||e)==='REQUEST_TIMEOUT'?'The secure sign-in service did not respond in time. Try again.':`Could not ${mode==='signup'?'create account':'sign in'}: ${e.message||e}`
    }
  }

  async function refreshSession(){
    if(!session?.refresh_token) return false;
    try{
      const d=await authRequest('/auth/v1/token?grant_type=refresh_token',{refresh_token:session.refresh_token});
      if(!d.access_token)return false;
      saveSession({access_token:d.access_token,refresh_token:d.refresh_token||session.refresh_token,expires_at:Math.floor(Date.now()/1000)+(Number(d.expires_in)||3600),user:d.user||session.user||null});
      return true;
    }catch{saveSession(null);return false}
  }

  async function validSession(){
    session=loadSession();
    if(!session?.access_token)return false;
    if(Number(session.expires_at||0)-60<=Math.floor(Date.now()/1000)) return refreshSession();
    return true;
  }

  async function backendFetch(method,body){
    if(!(await validSession())) throw new Error('AUTH_REQUIRED');
    const make=()=>timedFetch(runtime.fn,{
      method,cache:'no-store',
      headers:{'Content-Type':'application/json','apikey':runtime.key,'Authorization':`Bearer ${session.access_token}`},
      body:body===undefined?undefined:JSON.stringify(body)
    });
    let r=await make();
    if(r.status===401 && await refreshSession()) r=await make();
    const d=await r.json().catch(()=>({}));
    if(!r.ok){
      if(r.status===401){saveSession(null);throw new Error('AUTH_REQUIRED')}
      throw new Error(d.detail||d.error||`Backend HTTP ${r.status}`);
    }
    return d;
  }

  function list(items){return `<ul>${(items||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`}

  function fmtContextTime(value){
    if(!value)return 'time unavailable';
    try{return new Date(value).toLocaleString()}catch{return 'time unavailable'}
  }

  function verifiedContext(ctx){
    const event=ctx?.event_risk||{};
    const intel=ctx?.market_intelligence||{};
    const nearest=event.status==='verified' && event.nearest && typeof event.nearest==='object'?event.nearest:null;
    const items=intel.status==='verified' && Array.isArray(intel.items)?intel.items.slice(0,3):[];
    const eventHtml=nearest
      ? `<div style="margin-top:7px"><b>Nearest verified event</b><div style="color:#b8c4d2;margin-top:3px">${esc(nearest.title||'Scheduled event')} · ${esc(nearest.countdown||fmtContextTime(nearest.scheduled_at))}${nearest.source?` · ${esc(nearest.source)}`:''}</div></div>`
      : `<div style="margin-top:7px;color:#8294a8">Event feed: ${event.status==='verified'?'verified; no qualifying nearby event':'unavailable or stale'}</div>`;
    const newsHtml=items.length
      ? `<div style="margin-top:10px"><b>Fresh verified context</b><div style="display:grid;gap:6px;margin-top:6px">${items.map(x=>`<div style="padding:7px 9px;border:1px solid #20394d;border-radius:8px;background:#08131f"><div style="color:#c9d6df">${esc(x.title||'Context item')}</div><div style="color:#6f8798;font-size:10px;margin-top:2px">${esc(x.source||'source unavailable')}${x.published_at?` · ${esc(fmtContextTime(x.published_at))}`:''}</div></div>`).join('')}</div></div>`
      : `<div style="margin-top:10px;color:#8294a8">News/context feed: ${intel.status==='verified'?'verified; no current items':'unavailable or stale'}</div>`;
    return `<div style="margin-top:14px;padding:12px;border:1px solid #20394d;border-radius:10px;background:#091521"><div style="font-size:11px;font-weight:900;letter-spacing:.08em;color:#72d9ed">VERIFIED CONTEXT USED FOR THIS REVIEW</div>${eventHtml}${newsHtml}<div style="margin-top:9px;color:#6f8798;font-size:10px">Market prices remain ${esc(ctx?.market?.status||'unknown')}; contextual headlines are never treated as live prices or proof of direction.</div></div>`;
  }

  function render(payload){
    const host=ensureResultHost(); if(!host) return;
    const a=payload?.analysis||{}, ctx=payload?.context||{}, scenarios=a.scenarios||{};
    const scenario=name=>{const s=scenarios[name]||{};return `<article style="padding:14px;border:1px solid #26364d;border-radius:12px;margin:10px 0"><strong>${name.toUpperCase()}</strong><div><b>Evidence</b>${list(s.evidence)}</div><div><b>Invalidation</b>${list(s.invalidation)}</div></article>`};
    const usage=payload?.usage||{};
    host.style.display='block';
    host.innerHTML=`<div style="font-weight:800;font-size:18px;margin-bottom:8px">VAST Vision AI · educational review</div>
      <div style="color:#b8c4d2;margin-bottom:12px">Detected: <b>${esc(a.symbol||'unknown')}</b> · timeframe <b>${esc(a.timeframe||'unknown')}</b></div>
      <p><strong>Visible structure</strong><br>${esc(a.visible_structure||'unknown')}</p>
      ${scenario('bullish')}${scenario('bearish')}${scenario('neutral')}
      <p><strong>Uncertainty</strong><br>${esc(a.uncertainty||'unknown')}</p>
      <p><strong>Educational takeaway</strong><br>${esc(a.educational_takeaway||'')}</p>
      ${verifiedContext(ctx)}
      <div style="margin-top:14px;padding-top:12px;border-top:1px solid #26364d;color:#9fb0c4;font-size:13px">Event risk: ${esc(ctx.event_risk?.status||'unknown')} · Market prices: ${esc(ctx.market?.status||'unknown')} · News context: ${esc(ctx.market_intelligence?.status||'unknown')}<br>Privacy: ${payload?.privacy?.screenshot_stored===false?'screenshot not stored':'unknown'} · Analysis history: ${payload?.privacy?.analysis_saved?'saved securely':'not saved'} · Usage today: ${esc(usage.today??'—')}/${esc(usage.daily_limit??'—')}<br>${esc(payload?.notice||'Educational use only.')}</div>`;
  }

  function fileToDataUrl(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(new Error('Could not read screenshot'));r.readAsDataURL(file)})}

  function validateClientFile(file){
    if(!ALLOWED_IMAGE_TYPES.has(file.type))return 'Use a PNG, JPEG or WEBP chart screenshot.';
    if(!Number.isFinite(file.size)||file.size<=0)return 'The selected screenshot is empty or unreadable.';
    if(file.size>MAX_IMAGE_BYTES)return 'Screenshot exceeds the secure 8 MB beta limit. Export a smaller PNG, JPEG or WEBP image.';
    return '';
  }

  function releaseLocalPreview(){
    const input=q('#vision-file'), img=q('#vision-img'), preview=q('#vision-preview'), drop=q('#vision-drop');
    if(img?.src?.startsWith('blob:')){try{URL.revokeObjectURL(img.src)}catch{}}
    img?.removeAttribute('src');
    if(input)input.value='';
    if(preview)preview.hidden=true;
    if(drop)drop.hidden=false;
    document.dispatchEvent(new CustomEvent('vast:vision-cleared'));
  }

  async function analyze(){
    const input=q('#vision-file'), btn=q('#vision-analyze'), file=input?.files?.[0];
    if(!file){status('Choose a chart screenshot first.','error');return}
    const fileError=validateClientFile(file);
    if(fileError){status(fileError,'error');return}
    if(!runtime?.fn){status('Secure Vision backend is not connected.','error');return}
    btn.disabled=true;btn.textContent='Analyzing securely…';
    try{
      const image_data_url=await fileToDataUrl(file);
      const d=await backendFetch('POST',{image_data_url});
      render(d);
    }catch(e){
      if((e.message||e)==='AUTH_REQUIRED')authPanel('Your secure session expired. Sign in again to continue.');
      else if((e.message||e)==='REQUEST_TIMEOUT')status('The secure analysis service did not respond within 30 seconds. No result was invented; choose the screenshot again and retry when the backend is available.','error');
      else status(`Analysis could not be completed: ${e.message||e}`,'error');
    }finally{
      releaseLocalPreview();
      await refreshVisionHealth(true);
    }
  }

  async function signOut(){
    if(session?.access_token){
      try{await timedFetch(`${runtime.supabase}/auth/v1/logout`,{method:'POST',headers:{apikey:runtime.key,Authorization:`Bearer ${session.access_token}`}},CONFIG_TIMEOUT_MS)}catch{}
    }
    saveSession(null);setVisionState('SIGN IN',false);authPanel();
    const btn=q('#vision-analyze');if(btn){btn.disabled=true;btn.textContent='Sign in for secure AI analysis'}
  }

  function historyCards(items){
    if(!Array.isArray(items)||!items.length)return '<div style="margin-top:12px;color:#73889b;font-size:12px">No saved Vision reviews yet.</div>';
    return `<div style="margin-top:14px"><div style="font-size:11px;font-weight:900;letter-spacing:.08em;color:#72d9ed;margin-bottom:8px">RECENT PRIVATE HISTORY</div><div style="display:grid;gap:8px">${items.map(x=>`<article style="padding:10px 12px;border:1px solid #20394d;border-radius:10px;background:#08131f"><div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><b>${esc(x.symbol||'unknown')} · ${esc(x.timeframe||'unknown')}</b><span style="font-size:10px;color:#6f8798">${esc(x.created_at?new Date(x.created_at).toLocaleString():'')}</span></div><div style="margin-top:5px;color:#9aafbd;font-size:11px;line-height:1.4">${esc(x.educational_takeaway||x.visible_structure||'Saved educational review')}</div></article>`).join('')}</div></div>`;
  }

  function signedInPanel(health){
    const host=ensureResultHost();if(!host)return;
    const configured=health?.vision_provider_configured===true;
    const usage=health?.usage||{};
    const privacy=health?.privacy||{};
    host.style.display='block';
    host.innerHTML=`<div style="display:flex;justify-content:space-between;gap:14px;align-items:center;flex-wrap:wrap"><div><div style="font-weight:800">Secure beta session active</div><div style="color:#8294a8;font-size:12px;margin-top:4px">Vision backend ${configured?'is ready':'is connected but awaits the AI provider secret'} · usage ${esc(usage.today??0)}/${esc(usage.daily_limit??health?.daily_vision_limit??'—')} today</div><div style="color:#6f8798;font-size:11px;margin-top:4px">Screenshots are not stored · analysis history ${privacy.save_analysis===false?'off':`on (${esc(privacy.analysis_retention_days??30)} days)`}</div></div><button type="button" id="vast-auth-logout" class="btn secondary">Sign out</button></div>${historyCards(health?.recent_history)}`;
    q('#vast-auth-logout')?.addEventListener('click',signOut);
  }

  async function refreshVisionHealth(silent=false){
    const btn=q('#vision-analyze');if(!btn)return;
    if(!(await validSession())){
      setVisionState('SIGN IN',false);btn.disabled=true;btn.textContent='Sign in for secure AI analysis';if(!silent)authPanel();return;
    }
    try{
      const health=await backendFetch('GET');
      runtime.health=health;
      if(health.vision_provider_configured===true){
        setVisionState('ONLINE',true);btn.disabled=false;btn.textContent='Analyze screenshot securely';
        const note=q('.vision-actionbar span');if(note)note.textContent='Screenshot is processed for this request and is not retained by the beta server.';
      }else{
        setVisionState('BACKEND READY',true);btn.disabled=true;btn.textContent='Vision AI · provider connection required';
      }
      if(!silent)signedInPanel(health);
    }catch(e){
      if((e.message||e)==='AUTH_REQUIRED'){setVisionState('SIGN IN',false);btn.disabled=true;btn.textContent='Sign in for secure AI analysis';if(!silent)authPanel();return}
      setVisionState('DEGRADED',false);btn.disabled=true;btn.textContent='Secure AI analysis · temporarily unavailable';if(!silent)status((e.message||e)==='REQUEST_TIMEOUT'?'Backend health check timed out. Live analysis remains disabled until the secure backend responds.':`Backend check failed: ${e.message||e}`,'error');
    }
  }

  async function init(){
    const btn=q('#vision-analyze');if(!btn)return;
    ensureResultHost();btn.addEventListener('click',analyze);
    try{
      const cr=await timedFetch(`${CONFIG}?t=${Date.now()}`,{cache:'no-store'},CONFIG_TIMEOUT_MS);if(!cr.ok)throw new Error('runtime config unavailable');
      const cfg=await cr.json();
      const supabase=httpsUrl(cfg.supabase_url), fn=httpsUrl(cfg.vision_function_url), key=String(cfg.supabase_publishable_key||'').trim();
      if(cfg.enabled!==true||!supabase||!fn||!key){setVisionState('BACKEND NEEDED',false);btn.disabled=true;btn.textContent='Secure AI analysis · backend required';return}
      runtime={supabase,fn,key,health:null};
      await refreshVisionHealth(false);
    }catch(e){runtime=null;setVisionState('DEGRADED',false);btn.disabled=true;btn.textContent='Secure AI analysis · temporarily unavailable';status((e.message||e)==='REQUEST_TIMEOUT'?'Secure runtime configuration timed out. Try again when connectivity is stable.':'Secure runtime configuration could not be loaded.','error')}
  }

  document.addEventListener('DOMContentLoaded',()=>setTimeout(init,0));
})();