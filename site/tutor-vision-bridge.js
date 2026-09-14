(()=>{
  const KEY='vast_latest_vision_learning_focus_v1';
  const q=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function readFocus(){
    try{return JSON.parse(sessionStorage.getItem(KEY)||'null')}catch{return null}
  }
  function writeFocus(value){
    try{sessionStorage.setItem(KEY,JSON.stringify(value))}catch{}
  }
  function clearFocus(){
    try{sessionStorage.removeItem(KEY)}catch{}
  }
  function cleanLabel(text,label){return String(text||'').replace(label,'').trim()}

  function chooseLesson(text){
    const t=String(text||'').toLowerCase();
    if(/risk|volatil|event|confidence|exposure/.test(t))return 'foundation-risk';
    if(/invalid|scenario|review|outcome|hindsight/.test(t))return 'foundation-review';
    return 'foundation-context';
  }

  function captureLiveVisionResult(host){
    const title=host.firstElementChild?.textContent||'';
    if(!/educational review/i.test(title))return false;
    const paragraphs=[...host.querySelectorAll('p')];
    const takeawayNode=paragraphs.find(p=>/Educational takeaway/i.test(p.textContent||''));
    const uncertaintyNode=paragraphs.find(p=>/^Uncertainty/i.test((p.textContent||'').trim()));
    const detected=[...host.querySelectorAll('b')].map(x=>x.textContent?.trim()).filter(Boolean).slice(0,2);
    const takeaway=cleanLabel(takeawayNode?.textContent,'Educational takeaway');
    const uncertainty=cleanLabel(uncertaintyNode?.textContent,'Uncertainty');
    if(!takeaway&&!uncertainty)return false;
    const lessonId=chooseLesson(`${takeaway} ${uncertainty}`);
    writeFocus({takeaway,uncertainty,lessonId,detected,source:'current-review',created_at:new Date().toISOString()});
    return true;
  }

  function capturePrivateHistory(host){
    if(!/Secure beta session active/i.test(host.textContent||''))return false;
    const historyLabel=[...host.querySelectorAll('div')].find(el=>(el.textContent||'').trim()==='RECENT PRIVATE HISTORY');
    const historyList=historyLabel?.nextElementSibling;
    const card=historyList?.querySelector('article');
    if(!card)return false;
    const identity=q('b',card)?.textContent?.trim()||'';
    const parts=identity.split('·').map(x=>x.trim()).filter(Boolean);
    const takeaway=[...card.querySelectorAll('div')].map(x=>(x.textContent||'').trim()).filter(Boolean).at(-1)||'';
    const createdAt=q('span',card)?.textContent?.trim()||'';
    if(!takeaway)return false;
    const existing=readFocus();
    if(existing?.source==='current-review')return false;
    const lessonId=chooseLesson(takeaway);
    writeFocus({takeaway,uncertainty:'',lessonId,detected:parts.slice(0,2),source:'private-history',created_at:createdAt||new Date().toISOString()});
    return true;
  }

  function captureVisionResult(){
    const host=q('#vision-runtime-result');
    if(!host||host.style.display==='none')return;
    const text=host.textContent||'';
    if(/VAST Tutor Beta · secure sign in/i.test(text)||/Sign in to use secure Vision analysis/i.test(text)){
      clearFocus();
      renderTutorFocus();
      return;
    }
    if(captureLiveVisionResult(host)||capturePrivateHistory(host))renderTutorFocus();
  }

  function lessonTitle(id){
    return id==='foundation-risk'?'Risk before prediction':id==='foundation-review'?'Prediction → outcome review':'Evidence layers';
  }

  function revealLesson(lessonId,attempt=0){
    const lesson=q(`[data-lesson="${CSS.escape(lessonId)}"]`);
    if(lesson){
      lesson.scrollIntoView({behavior:'smooth',block:'center'});
      lesson.animate?.([{outline:'2px solid rgba(114,217,237,.7)'},{outline:'2px solid transparent'}],{duration:1400});
      return;
    }
    if(attempt<8)setTimeout(()=>revealLesson(lessonId,attempt+1),120);
  }

  function openTutorLesson(lessonId){
    const tutorNav=q('[data-page="tutor"]');
    if(tutorNav)tutorNav.click();
    else if(location.hash!=='#tutor')location.hash='tutor';
    requestAnimationFrame(()=>revealLesson(lessonId));
  }

  function renderTutorFocus(){
    const slot=q('#tutor-slot');
    if(!slot)return;
    const focus=readFocus();
    let card=q('#vision-tutor-focus');
    if(!focus){card?.remove();return}
    if(!card){
      card=document.createElement('section');
      card.id='vision-tutor-focus';
      card.style.cssText='margin:0 0 12px;padding:14px 16px;border:1px solid #23506a;border-radius:14px;background:#081521';
      slot.prepend(card);
    }
    const origin=focus.source==='private-history'?'YOUR LATEST SAVED VISION REVIEW':'YOUR LATEST VISION REVIEW';
    card.innerHTML=`<div style="font-size:10px;font-weight:900;letter-spacing:.1em;color:#72d9ed">CONTINUE FROM ${origin}</div>
      <div style="font-weight:800;font-size:16px;margin-top:7px">Suggested lesson: ${esc(lessonTitle(focus.lessonId))}</div>
      <div style="color:#9cb0bd;font-size:12px;line-height:1.5;margin-top:6px">${esc(focus.takeaway||focus.uncertainty||'Use the latest chart review as your learning focus.')}</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px"><button type="button" class="btn secondary" id="vision-focus-open">Open suggested lesson</button><span style="color:#647d8d;font-size:10px">Only the saved educational review is reused; no screenshot or trade signal is stored here.</span></div>`;
    q('#vision-focus-open',card)?.addEventListener('click',()=>openTutorLesson(focus.lessonId));
  }

  function observeVision(){
    const attach=()=>{
      const host=q('#vision-runtime-result');
      if(!host)return false;
      const obs=new MutationObserver(captureVisionResult);
      obs.observe(host,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['style']});
      captureVisionResult();
      return true;
    };
    if(attach())return;
    const bodyObs=new MutationObserver(()=>{if(attach())bodyObs.disconnect()});
    bodyObs.observe(document.body,{childList:true,subtree:true});
  }

  document.addEventListener('DOMContentLoaded',()=>{
    observeVision();
    renderTutorFocus();
    const tutor=q('#tutor-slot');
    if(tutor)new MutationObserver(renderTutorFocus).observe(tutor,{childList:true,subtree:false});
  });
})();
