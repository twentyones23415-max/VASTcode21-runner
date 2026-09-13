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
  function cleanLabel(text,label){return String(text||'').replace(label,'').trim()}

  function chooseLesson(text){
    const t=String(text||'').toLowerCase();
    if(/risk|volatil|event|confidence|exposure/.test(t))return 'foundation-risk';
    if(/invalid|scenario|review|outcome|hindsight/.test(t))return 'foundation-review';
    return 'foundation-context';
  }

  function captureVisionResult(){
    const host=q('#vision-runtime-result');
    if(!host||host.style.display==='none')return;
    const title=host.firstElementChild?.textContent||'';
    if(!/educational review/i.test(title))return;
    const paragraphs=[...host.querySelectorAll('p')];
    const takeawayNode=paragraphs.find(p=>/Educational takeaway/i.test(p.textContent||''));
    const uncertaintyNode=paragraphs.find(p=>/^Uncertainty/i.test((p.textContent||'').trim()));
    const detected=[...host.querySelectorAll('b')].map(x=>x.textContent?.trim()).filter(Boolean).slice(0,2);
    const takeaway=cleanLabel(takeawayNode?.textContent,'Educational takeaway');
    const uncertainty=cleanLabel(uncertaintyNode?.textContent,'Uncertainty');
    if(!takeaway&&!uncertainty)return;
    const lessonId=chooseLesson(`${takeaway} ${uncertainty}`);
    writeFocus({takeaway,uncertainty,lessonId,detected,created_at:new Date().toISOString()});
    renderTutorFocus();
  }

  function lessonTitle(id){
    return id==='foundation-risk'?'Risk before prediction':id==='foundation-review'?'Prediction → outcome review':'Evidence layers';
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
    card.innerHTML=`<div style="font-size:10px;font-weight:900;letter-spacing:.1em;color:#72d9ed">CONTINUE FROM YOUR LATEST VISION REVIEW</div>
      <div style="font-weight:800;font-size:16px;margin-top:7px">Suggested lesson: ${esc(lessonTitle(focus.lessonId))}</div>
      <div style="color:#9cb0bd;font-size:12px;line-height:1.5;margin-top:6px">${esc(focus.takeaway||focus.uncertainty||'Use the latest chart review as your learning focus.')}</div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px"><button type="button" class="btn secondary" id="vision-focus-open">Open suggested lesson</button><span style="color:#647d8d;font-size:10px">This recommendation is deterministic from the returned educational review; it is not a trade signal.</span></div>`;
    q('#vision-focus-open',card)?.addEventListener('click',()=>{
      const lesson=q(`[data-lesson="${CSS.escape(focus.lessonId)}"]`);
      if(lesson){lesson.scrollIntoView({behavior:'smooth',block:'center'});lesson.animate?.([{outline:'2px solid rgba(114,217,237,.7)'},{outline:'2px solid transparent'}],{duration:1400});}
    });
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
