(()=>{
  const FEED='data/tutor_curriculum.json';
  const CONFIG='data/tutor_runtime.json';
  const STORE='vast_tutor_foundations_v1';
  const SESSION_KEY='vast_tutor_supabase_session_v1';
  const q=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let runtime=null;
  let curriculum=null;

  function loadState(){
    try{return JSON.parse(localStorage.getItem(STORE)||'{}')}catch{return {}}
  }
  function saveState(state){
    try{localStorage.setItem(STORE,JSON.stringify(state))}catch{}
  }
  function loadSession(){
    try{return JSON.parse(localStorage.getItem(SESSION_KEY)||'null')}catch{return null}
  }
  function percent(done,total){return total?Math.round((done/total)*100):0}

  async function loadRuntime(){
    try{
      const r=await fetch(`${CONFIG}?t=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error('config');
      const d=await r.json();
      if(d.enabled!==true||!d.supabase_url||!d.supabase_publishable_key)return null;
      return {supabase:String(d.supabase_url).replace(/\/$/,''),key:String(d.supabase_publishable_key)};
    }catch{return null}
  }

  function authContext(){
    const s=loadSession();
    const userId=s?.user?.id;
    if(!runtime||!s?.access_token||!userId)return null;
    return {token:s.access_token,userId};
  }

  async function remoteProgress(){
    const auth=authContext();if(!auth)return null;
    const url=`${runtime.supabase}/rest/v1/tutor_progress?select=lesson_id,status,best_score,attempts,completed_at`;
    const r=await fetch(url,{cache:'no-store',headers:{apikey:runtime.key,Authorization:`Bearer ${auth.token}`}});
    if(!r.ok)return null;
    return r.json().catch(()=>null);
  }

  async function syncLesson(lessonId,state,correct){
    const auth=authContext();if(!auth)return false;
    const prev=state.remote?.[lessonId]||{};
    const attempts=Math.max(Number(prev.attempts)||0,Number(state.attempts?.[lessonId])||0);
    const body={
      user_id:auth.userId,
      lesson_id:lessonId,
      status:correct?'completed':'in_progress',
      best_score:correct?100:Math.max(0,Number(prev.best_score)||0),
      attempts,
      completed_at:correct?(prev.completed_at||new Date().toISOString()):null,
      updated_at:new Date().toISOString()
    };
    const r=await fetch(`${runtime.supabase}/rest/v1/tutor_progress?on_conflict=user_id,lesson_id`,{
      method:'POST',
      headers:{'Content-Type':'application/json',apikey:runtime.key,Authorization:`Bearer ${auth.token}`,Prefer:'resolution=merge-duplicates,return=minimal'},
      body:JSON.stringify(body)
    });
    if(r.ok){state.remote=state.remote||{};state.remote[lessonId]=body;saveState(state);return true}
    return false;
  }

  async function hydrateRemote(state){
    const rows=await remoteProgress();
    if(!Array.isArray(rows))return false;
    state.remote=state.remote||{};state.completed=state.completed||{};state.attempts=state.attempts||{};
    for(const row of rows){
      state.remote[row.lesson_id]=row;
      state.attempts[row.lesson_id]=Math.max(Number(state.attempts[row.lesson_id])||0,Number(row.attempts)||0);
      if(row.status==='completed')state.completed[row.lesson_id]=true;
    }
    saveState(state);return true;
  }

  async function addLearning(){
    if(q('#tutor-learning-path')) return;
    const slot=q('#tutor-slot');
    const lab=q('#tutor-ai-lab');
    if(!slot && !lab) return;
    const s=document.createElement('section');
    s.id='tutor-learning-path'; s.className='tutor-learning';
    s.innerHTML='<div class="shell"><div class="learning-shell"><div class="intel-empty">Loading Tutor foundations…</div></div></div>';
    if(slot){slot.querySelectorAll('.module-empty').forEach(n=>n.remove());slot.appendChild(s)}else{lab.insertAdjacentElement('afterend',s)}
    try{
      const [r,rt]=await Promise.all([fetch(`${FEED}?t=${Date.now()}`,{cache:'no-store'}),loadRuntime()]);
      if(!r.ok) throw new Error('curriculum');
      runtime=rt;curriculum=await r.json();
      const state=loadState();state.completed=state.completed||{};state.answers=state.answers||{};state.attempts=state.attempts||{};
      await hydrateRemote(state);
      render(curriculum,state);
    }catch{
      const host=q('.learning-shell',s); if(host) host.innerHTML='<div class="intel-empty">Tutor foundations are temporarily unavailable.</div>';
    }
  }

  function render(data,state=loadState()){
    const host=q('#tutor-learning-path .learning-shell'); if(!host) return;
    const lessons=(data.lessons||[]).sort((a,b)=>(a.order||0)-(b.order||0));
    state.completed=state.completed||{};state.answers=state.answers||{};state.attempts=state.attempts||{};
    const done=lessons.filter(x=>state.completed[x.id]).length;
    const signedIn=!!authContext();
    host.innerHTML=`<div class="learning-head"><div><div class="eyebrow">VAST Tutor · structured learning</div><h2>Foundations that can be measured.</h2><p>${signedIn?'Signed-in progress is synced securely to your private Tutor profile.':'Progress stays on this device until you sign in through Vision AI.'}</p></div><div class="learning-progress"><b>${percent(done,lessons.length)}%</b><span>${done}/${lessons.length} lessons completed</span><div><i style="width:${percent(done,lessons.length)}%"></i></div></div></div><div class="lesson-grid">${lessons.map((x,i)=>lessonCard(x,i,state)).join('')}</div><div class="learning-foot"><span>${signedIn?'PRIVATE SYNC ON':'LOCAL FALLBACK'}</span><p>${signedIn?'Lesson status, score and attempt count are stored in the authenticated backend under row-level security. Screenshots are not stored here.':'Clearing browser storage resets local-only progress. Sign in through Vision AI to enable private cross-device progress sync.'}</p><button type="button" id="learning-reset">Reset local progress</button></div>`;
    bind(lessons,state,data);
  }

  function lessonCard(x,i,state){
    const answered=state.answers[x.id];
    const complete=!!state.completed[x.id];
    const attempts=Number(state.attempts?.[x.id])||0;
    return `<article class="lesson-card ${complete?'complete':''}" data-lesson="${esc(x.id)}"><div class="lesson-meta"><span>${String(i+1).padStart(2,'0')} · ${esc(x.level)}</span><b>${esc(x.minutes)} min${attempts?` · ${attempts} attempt${attempts===1?'':'s'}`:''}</b></div><h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p><ul>${(x.key_points||[]).map(k=>`<li>${esc(k)}</li>`).join('')}</ul><div class="quiz-box"><strong>Checkpoint</strong><p>${esc(x.quiz?.question||'')}</p><div class="quiz-options">${(x.quiz?.options||[]).map((o,idx)=>`<button type="button" data-answer="${idx}" ${answered!==undefined?'disabled':''}>${esc(o)}</button>`).join('')}</div><div class="quiz-result ${answered===undefined?'':'show'}">${answered===undefined?'':resultText(x,answered)}</div></div><div class="lesson-complete">${complete?'✓ Completed':'Complete the checkpoint to finish this lesson'}</div></article>`;
  }

  function resultText(x,answer){
    const ok=Number(answer)===Number(x.quiz?.correct_index);
    return `<b>${ok?'Correct':'Review this'}</b><span>${esc(x.quiz?.explanation||'')}</span>`;
  }

  function bind(lessons,state,data){
    q('#learning-reset')?.addEventListener('click',()=>{try{localStorage.removeItem(STORE)}catch{}render(data,{completed:{},answers:{},attempts:{},remote:{}})});
    lessons.forEach(x=>{
      const card=q(`[data-lesson="${CSS.escape(x.id)}"]`); if(!card) return;
      card.querySelectorAll('[data-answer]').forEach(btn=>btn.addEventListener('click',async()=>{
        const answer=Number(btn.dataset.answer);
        const correct=answer===Number(x.quiz?.correct_index);
        state.answers[x.id]=answer;
        state.attempts[x.id]=(Number(state.attempts[x.id])||0)+1;
        if(correct) state.completed[x.id]=true;
        saveState(state);
        await syncLesson(x.id,state,correct);
        render(data,state);
      }));
    });
  }

  window.addEventListener('storage',e=>{if(e.key===SESSION_KEY&&curriculum)hydrateRemote(loadState()).then(()=>render(curriculum))});
  document.addEventListener('DOMContentLoaded',addLearning);
})();
