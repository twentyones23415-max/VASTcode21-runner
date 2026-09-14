(()=>{
  const SESSION_KEY='vast_tutor_supabase_session_v1';
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const pageMap={home:'page-home',vision:'page-vision',tutor:'page-tutor',mentor:'page-mentor',outcome:'page-outcome',context:'page-context',pricing:'page-pricing'};

  function route(name,replace=false){
    if(!pageMap[name])name='home';
    qa('.app-page').forEach(p=>p.classList.toggle('active',p.id===pageMap[name]));
    qa('[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===name));
    const hash=`#${name}`;
    if(location.hash!==hash){if(replace)history.replaceState(null,'',hash);else history.pushState(null,'',hash)}
  }

  function move(id,slot){
    const node=q(id),host=q(slot);if(!node||!host)return;
    host.querySelectorAll('.module-empty').forEach(n=>n.remove());
    if(node.parentElement!==host)host.appendChild(node);
  }
  function normalizeModules(){
    move('#tutor-ai-lab','#vision-slot');
    move('#tutor-learning-path','#tutor-slot');
    move('#outcome-lab-local','#outcome-slot');
    move('#event-risk-shield','#context-slot');
  }
  function clearVisionResult(){
    const host=q('#vision-runtime-result');if(host){host.innerHTML='';host.style.display='none'}
  }
  function accountLabel(){
    const el=q('#account-pill');if(!el)return;
    try{const s=JSON.parse(localStorage.getItem(SESSION_KEY)||'null');const email=s?.user?.email||'';el.textContent=email?email.split('@')[0]:'Beta workspace'}catch{el.textContent='Beta workspace'}
  }

  function reviewField(host,label){
    const p=qa('p',host).find(node=>q('strong',node)?.textContent.trim()===label);
    if(!p)return '';
    return p.textContent.replace(label,'').trim();
  }

  function prefillOutcome(review){
    route('outcome');
    const apply=()=>{
      const form=q('#outcome-form');
      if(!form)return false;
      if(form.elements.symbol)form.elements.symbol.value=review.symbol==='unknown'?'':review.symbol;
      if(form.elements.timeframe)form.elements.timeframe.value=review.timeframe==='unknown'?'':review.timeframe;
      if(form.elements.title&&!form.elements.title.value)form.elements.title.value=`Vision review · ${review.symbol} ${review.timeframe}`.slice(0,80);
      const notes=[
        review.structure&&`Visible structure: ${review.structure}`,
        review.uncertainty&&`Uncertainty: ${review.uncertainty}`,
        review.takeaway&&`Educational takeaway: ${review.takeaway}`
      ].filter(Boolean).join('\n');
      if(form.elements.notes&&!form.elements.notes.value)form.elements.notes.value=notes.slice(0,500);
      form.scrollIntoView({behavior:'smooth',block:'start'});
      return true;
    };
    if(!apply())setTimeout(apply,120);
  }

  function wireVisionBridge(){
    const host=q('#vision-runtime-result');
    if(!host||host.dataset.workflowBridge==='1')return;
    if(!host.textContent.includes('VAST Vision AI · educational review'))return;
    const detected=qa('b',host);
    const review={
      symbol:(detected[0]?.textContent||'unknown').trim(),
      timeframe:(detected[1]?.textContent||'unknown').trim(),
      structure:reviewField(host,'Visible structure'),
      uncertainty:reviewField(host,'Uncertainty'),
      takeaway:reviewField(host,'Educational takeaway')
    };
    const actions=document.createElement('div');
    actions.style.cssText='display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px solid #26364d';
    actions.innerHTML='<button type="button" class="btn secondary" data-vision-tutor>Continue in Tutor</button><button type="button" class="btn secondary" data-vision-outcome>Use in Outcome Lab</button><span style="align-self:center;color:#6f8798;font-size:10px">Only review text is transferred in this browser; the screenshot is not copied or stored.</span>';
    host.appendChild(actions);
    q('[data-vision-tutor]',actions)?.addEventListener('click',()=>{route('tutor');q('#tutor-learning-path')?.scrollIntoView({behavior:'smooth',block:'start'})});
    q('[data-vision-outcome]',actions)?.addEventListener('click',()=>prefillOutcome(review));
    host.dataset.workflowBridge='1';
  }

  document.addEventListener('DOMContentLoaded',()=>{
    qa('[data-page]').forEach(btn=>btn.addEventListener('click',()=>route(btn.dataset.page)));
    qa('[data-go]').forEach(btn=>btn.addEventListener('click',()=>route(btn.dataset.go)));
    window.addEventListener('popstate',()=>route((location.hash||'#home').slice(1),true));
    document.addEventListener('click',e=>{if(e.target.closest?.('#vision-clear'))clearVisionResult()},true);
    document.addEventListener('change',e=>{if(e.target?.id==='vision-file')clearVisionResult()},true);
    document.addEventListener('vast:vision-cleared',clearVisionResult);
    document.addEventListener('vast:vision-image-changed',clearVisionResult);
    const observer=new MutationObserver(()=>{normalizeModules();wireVisionBridge()});observer.observe(document.body,{childList:true,subtree:true});
    normalizeModules();wireVisionBridge();accountLabel();setInterval(accountLabel,5000);
    route((location.hash||'#home').slice(1),true);
  });
})();