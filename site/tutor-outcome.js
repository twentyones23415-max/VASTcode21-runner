(()=>{
  const STORE='vast_outcome_lab_v1';
  const EVENT_FEED='data/event_risk.json';
  const EVENT_MAX_AGE_MS=150*60*1000;
  const q=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function load(){
    try{
      const d=JSON.parse(localStorage.getItem(STORE)||'[]');
      return Array.isArray(d)?d:[];
    }catch{return []}
  }
  function save(rows){
    try{localStorage.setItem(STORE,JSON.stringify(rows.slice(0,100)))}catch{}
  }
  function id(){return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2,8)}`}
  function fmt(ts){try{return new Date(ts).toLocaleString()}catch{return 'unknown'}}

  async function eventSnapshot(){
    try{
      const r=await fetch(`${EVENT_FEED}?t=${Date.now()}`,{cache:'no-store'});
      if(!r.ok) throw new Error('event feed');
      const d=await r.json();
      const updated=new Date(d.updated_at||0);
      const age=Date.now()-updated.getTime();
      if(!Number.isFinite(age)||age<0||age>EVENT_MAX_AGE_MS||d.status==='degraded'){
        return {status:'unknown',label:'Event feed stale/unavailable at capture time'};
      }
      const n=d.nearest;
      if(!n) return {status:'clear',label:'No qualifying scheduled event in current monitoring horizon',updated_at:d.updated_at};
      return {
        status:String(n.risk_state||'watch').toLowerCase(),
        label:`${n.title||'Scheduled event'} · ${n.source||'official source'} · ${n.countdown||'timing available'}`,
        scheduled_at:n.scheduled_at||null,
        source:n.source||null,
        link:n.link||null,
        updated_at:d.updated_at
      };
    }catch{
      return {status:'unknown',label:'Event feed unavailable at capture time'};
    }
  }

  function card(row){
    const done=row.outcome?.status;
    return `<article class="outcome-card" data-id="${esc(row.id)}">
      <div class="outcome-meta"><span>${esc(row.symbol)} · ${esc(row.timeframe)}</span><b>${esc(row.bias)}</b></div>
      <h3>${esc(row.title||'Scenario review')}</h3>
      <p class="outcome-created">Captured ${esc(fmt(row.created_at))}</p>
      <div class="outcome-facts">
        <div><span>Scenario</span><p>${esc(row.scenario)}</p></div>
        <div><span>Invalidation</span><p>${esc(row.invalidation)}</p></div>
        <div><span>Event context</span><p>${esc(row.event?.label||'Unknown')}</p></div>
      </div>
      ${row.notes?`<p class="outcome-notes">${esc(row.notes)}</p>`:''}
      ${done?`<div class="outcome-result"><strong>${esc(done)}</strong><p>${esc(row.outcome.notes||'No review note saved.')}</p><small>Reviewed ${esc(fmt(row.outcome.reviewed_at))}</small></div>`:
      `<div class="outcome-review"><label>What happened?<select data-result><option value="">Choose outcome</option><option>Scenario held</option><option>Scenario invalidated</option><option>Mixed / inconclusive</option></select></label><label>Review note<textarea data-review rows="3" maxlength="600" placeholder="What confirmed or invalidated the original idea?"></textarea></label><button class="btn secondary" type="button" data-save-review>Save outcome review</button></div>`}
      <button class="outcome-delete" type="button" data-delete>Delete local record</button>
    </article>`;
  }

  function renderList(){
    const host=q('#outcome-list'); if(!host) return;
    const rows=load().sort((a,b)=>new Date(b.created_at)-new Date(a.created_at));
    host.innerHTML=rows.length?rows.map(card).join(''):'<div class="intel-empty">No scenarios saved yet. Capture one before the market outcome is known.</div>';
    host.querySelectorAll('[data-id]').forEach(node=>{
      const rid=node.dataset.id;
      node.querySelector('[data-save-review]')?.addEventListener('click',()=>{
        const status=node.querySelector('[data-result]')?.value||'';
        const notes=node.querySelector('[data-review]')?.value.trim()||'';
        if(!status){alert('Choose an outcome before saving the review.');return}
        const rows=load(); const row=rows.find(x=>x.id===rid); if(!row) return;
        row.outcome={status,notes,reviewed_at:new Date().toISOString()}; save(rows); renderList(); updateCount();
      });
      node.querySelector('[data-delete]')?.addEventListener('click',()=>{
        save(load().filter(x=>x.id!==rid)); renderList(); updateCount();
      });
    });
  }

  function updateCount(){
    const rows=load(), el=q('#outcome-count'); if(!el) return;
    const reviewed=rows.filter(x=>x.outcome?.status).length;
    el.textContent=`${rows.length} captured · ${reviewed} reviewed`;
  }

  async function submit(e){
    e.preventDefault();
    const form=e.currentTarget;
    const data=new FormData(form);
    const symbol=String(data.get('symbol')||'').trim().toUpperCase();
    const timeframe=String(data.get('timeframe')||'').trim().toUpperCase();
    const bias=String(data.get('bias')||'').trim();
    const scenario=String(data.get('scenario')||'').trim();
    const invalidation=String(data.get('invalidation')||'').trim();
    if(!symbol||!timeframe||!bias||!scenario||!invalidation){alert('Complete symbol, timeframe, bias, scenario and invalidation.');return}
    const btn=q('[type="submit"]',form); if(btn){btn.disabled=true;btn.textContent='Capturing context…'}
    const row={
      id:id(), created_at:new Date().toISOString(), symbol,timeframe,bias,
      title:String(data.get('title')||'').trim(),scenario,invalidation,
      notes:String(data.get('notes')||'').trim(),event:await eventSnapshot(),outcome:null,
      storage:'local-only'
    };
    const rows=load(); rows.unshift(row); save(rows); form.reset(); renderList(); updateCount();
    if(btn){btn.disabled=false;btn.textContent='Capture scenario locally'}
  }

  function mount(){
    if(q('#outcome-lab-local')) return;
    const slot=q('#outcome-slot');
    const learning=q('#tutor-learning-path')||q('#tutor-ai-lab');
    if(!slot && !learning) return;
    const s=document.createElement('section'); s.id='outcome-lab-local'; s.className='outcome-lab';
    s.innerHTML=`<div class="shell"><div class="outcome-shell">
      <div class="outcome-head"><div><div class="eyebrow">VAST Outcome Lab · local beta</div><h2>Record the idea before you know the answer.</h2><p>Capture a scenario, its invalidation and the currently verified Event Risk context. Return later and review what actually happened. All records stay in this browser during prelaunch.</p></div><div class="outcome-count" id="outcome-count">0 captured</div></div>
      <form class="outcome-form" id="outcome-form">
        <label>Title <input name="title" maxlength="80" placeholder="e.g. Gold NY session range break"></label>
        <label>Symbol <input name="symbol" maxlength="20" required placeholder="XAUUSD"></label>
        <label>Timeframe <input name="timeframe" maxlength="12" required placeholder="M15"></label>
        <label>Bias <select name="bias" required><option value="">Choose</option><option>Bullish scenario</option><option>Bearish scenario</option><option>Neutral / range</option></select></label>
        <label class="wide">Scenario <textarea name="scenario" rows="3" maxlength="700" required placeholder="What would need to happen for this scenario to develop?"></textarea></label>
        <label class="wide">Invalidation <textarea name="invalidation" rows="2" maxlength="500" required placeholder="What observable condition would make the idea wrong?"></textarea></label>
        <label class="wide">Notes <textarea name="notes" rows="2" maxlength="500" placeholder="Optional evidence or lesson focus"></textarea></label>
        <div class="outcome-submit wide"><button class="btn primary" type="submit">Capture scenario locally</button><span>No screenshot, email or journal entry is uploaded by this module.</span></div>
      </form>
      <div class="outcome-list" id="outcome-list"></div>
      <div class="outcome-privacy"><strong>Prelaunch privacy:</strong> records are stored only in browser localStorage. Clearing site data removes them. This is an educational review journal, not a signal or execution tool.</div>
    </div></div>`;
    if(slot){
      slot.querySelectorAll('.module-empty').forEach(n=>n.remove());
      slot.appendChild(s);
    }else{
      learning.insertAdjacentElement('afterend',s);
    }
    q('#outcome-form')?.addEventListener('submit',submit);
    renderList(); updateCount();
  }

  document.addEventListener('DOMContentLoaded',mount);
})();
