(()=>{
  const SESSION_KEY='vast_tutor_supabase_session_v1';
  const q=(s,r=document)=>r.querySelector(s);
  const qa=(s,r=document)=>[...r.querySelectorAll(s)];
  const pageMap={home:'page-home',vision:'page-vision',tutor:'page-tutor',outcome:'page-outcome',context:'page-context'};

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

  document.addEventListener('DOMContentLoaded',()=>{
    qa('[data-page]').forEach(btn=>btn.addEventListener('click',()=>route(btn.dataset.page)));
    qa('[data-go]').forEach(btn=>btn.addEventListener('click',()=>route(btn.dataset.go)));
    window.addEventListener('popstate',()=>route((location.hash||'#home').slice(1),true));
    document.addEventListener('click',e=>{if(e.target.closest?.('#vision-clear'))clearVisionResult()},true);
    document.addEventListener('change',e=>{if(e.target?.id==='vision-file')clearVisionResult()},true);
    document.addEventListener('vast:vision-cleared',clearVisionResult);
    document.addEventListener('vast:vision-image-changed',clearVisionResult);
    const observer=new MutationObserver(normalizeModules);observer.observe(document.body,{childList:true,subtree:true});
    normalizeModules();accountLabel();setInterval(accountLabel,5000);
    route((location.hash||'#home').slice(1),true);
  });
})();