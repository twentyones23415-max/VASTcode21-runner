(()=>{
  const FEED='data/tutor_curriculum.json';
  const STORE='vast_tutor_foundations_v1';
  const q=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function loadState(){
    try{return JSON.parse(localStorage.getItem(STORE)||'{}')}catch{return {}}
  }
  function saveState(state){
    try{localStorage.setItem(STORE,JSON.stringify(state))}catch{}
  }
  function percent(done,total){return total?Math.round((done/total)*100):0}

  async function addLearning(){
    if(q('#tutor-learning-path')) return;
    const slot=q('#tutor-slot');
    const lab=q('#tutor-ai-lab');
    if(!slot && !lab) return;
    const s=document.createElement('section');
    s.id='tutor-learning-path'; s.className='tutor-learning';
    s.innerHTML='<div class="shell"><div class="learning-shell"><div class="intel-empty">Loading Tutor foundations…</div></div></div>';
    if(slot){
      slot.querySelectorAll('.module-empty').forEach(n=>n.remove());
      slot.appendChild(s);
    }else{
      lab.insertAdjacentElement('afterend',s);
    }
    try{
      const r=await fetch(`${FEED}?t=${Date.now()}`,{cache:'no-store'}); if(!r.ok) throw new Error('curriculum');
      render(await r.json());
    }catch{
      const host=q('.learning-shell',s); if(host) host.innerHTML='<div class="intel-empty">Tutor foundations are temporarily unavailable.</div>';
    }
  }

  function render(data){
    const host=q('#tutor-learning-path .learning-shell'); if(!host) return;
    const lessons=(data.lessons||[]).sort((a,b)=>(a.order||0)-(b.order||0));
    const state=loadState(); state.completed=state.completed||{}; state.answers=state.answers||{};
    const done=lessons.filter(x=>state.completed[x.id]).length;
    host.innerHTML=`<div class="learning-head"><div><div class="eyebrow">VAST Tutor · structured learning</div><h2>Foundations that can be measured.</h2><p>${esc(data.storage_notice||'Progress is stored locally during prelaunch.')}</p></div><div class="learning-progress"><b>${percent(done,lessons.length)}%</b><span>${done}/${lessons.length} lessons completed</span><div><i style="width:${percent(done,lessons.length)}%"></i></div></div></div><div class="lesson-grid">${lessons.map((x,i)=>lessonCard(x,i,state)).join('')}</div><div class="learning-foot"><span>PRELAUNCH PRIVACY</span><p>No name, email, screenshot or quiz result is sent to a server by this module. Clearing browser storage resets this progress.</p><button type="button" id="learning-reset">Reset local progress</button></div>`;
    bind(lessons,state,data);
  }

  function lessonCard(x,i,state){
    const answered=state.answers[x.id];
    const complete=!!state.completed[x.id];
    return `<article class="lesson-card ${complete?'complete':''}" data-lesson="${esc(x.id)}"><div class="lesson-meta"><span>${String(i+1).padStart(2,'0')} · ${esc(x.level)}</span><b>${esc(x.minutes)} min</b></div><h3>${esc(x.title)}</h3><p>${esc(x.summary)}</p><ul>${(x.key_points||[]).map(k=>`<li>${esc(k)}</li>`).join('')}</ul><div class="quiz-box"><strong>Checkpoint</strong><p>${esc(x.quiz?.question||'')}</p><div class="quiz-options">${(x.quiz?.options||[]).map((o,idx)=>`<button type="button" data-answer="${idx}" ${answered!==undefined?'disabled':''}>${esc(o)}</button>`).join('')}</div><div class="quiz-result ${answered===undefined?'':'show'}">${answered===undefined?'':resultText(x,answered)}</div></div><div class="lesson-complete">${complete?'✓ Completed':'Complete the checkpoint to finish this lesson'}</div></article>`;
  }

  function resultText(x,answer){
    const ok=Number(answer)===Number(x.quiz?.correct_index);
    return `<b>${ok?'Correct':'Review this'}</b><span>${esc(x.quiz?.explanation||'')}</span>`;
  }

  function bind(lessons,state,data){
    q('#learning-reset')?.addEventListener('click',()=>{
      try{localStorage.removeItem(STORE)}catch{}
      render(data);
    });
    lessons.forEach(x=>{
      const card=q(`[data-lesson="${CSS.escape(x.id)}"]`); if(!card) return;
      card.querySelectorAll('[data-answer]').forEach(btn=>btn.addEventListener('click',()=>{
        const answer=Number(btn.dataset.answer);
        state.answers[x.id]=answer;
        if(answer===Number(x.quiz?.correct_index)) state.completed[x.id]=true;
        saveState(state);
        render(data);
      }));
    });
  }

  document.addEventListener('DOMContentLoaded',addLearning);
})();
