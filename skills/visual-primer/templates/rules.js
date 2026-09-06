(() => {
  'use strict';
  const data=JSON.parse(document.getElementById('s2s-data').textContent);
  const ko=data.language.toLowerCase().startsWith('ko');
  const t=(kr,en)=>ko?kr:en;
  const theme=document.getElementById('theme-toggle');
  function paintTheme(){
    const dark=document.documentElement.dataset.theme==='dark';
    theme.setAttribute('aria-checked',String(dark));
    theme.setAttribute('aria-label',t('다크 모드','Dark mode'));
    theme.title=dark?t('다크 모드 끄기','Turn dark mode off'):t('다크 모드 켜기','Turn dark mode on');
    document.getElementById('theme-label').textContent=t('다크 모드','Dark mode');
  }
  theme.addEventListener('click',()=>{
    const value=document.documentElement.dataset.theme==='dark'?'light':'dark';
    document.documentElement.dataset.theme=value;
    try{localStorage.setItem('s2s-atlas-theme',value);}catch{/* The page also works without storage. */}
    paintTheme();
  });
  paintTheme();
  for(const figure of document.querySelectorAll('.rule-figure.comparison')){
    const controls=figure.querySelector('.case-controls');
    const cases=[...figure.children].filter(n=>n.classList.contains('rule-case'));
    const buttons=[...controls.querySelectorAll('button')];
    function select(index){
      cases.forEach((item,i)=>{item.hidden=i!==index;});
      buttons.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
    }
    buttons.forEach((button,index)=>button.addEventListener('click',()=>select(index)));
    controls.hidden=false;
    select(0);
  }
  let noticeTimer;
  for(const button of document.querySelectorAll('.copy-command'))button.addEventListener('click',async()=>{
    let message=t('복사했습니다.','Copied.');
    try{await navigator.clipboard.writeText(button.dataset.command);}
    catch{
      const field=document.createElement('textarea');field.value=button.dataset.command;button.after(field);field.select();
      let copied=false;
      try{copied=document.execCommand('copy');}catch{/* Keep the command available for manual copying. */}
      if(copied)field.remove();
      else message=t('표시된 명령을 선택해 복사해 주세요.','Select and copy the displayed command.');
    }
    const notice=document.getElementById('announcement');notice.textContent=message;notice.classList.add('visible');
    clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>notice.classList.remove('visible'),3000);
  });
  document.getElementById('offline-note').textContent=t('오프라인 설명서 · 조건을 비교하고 근거를 확인할 수 있습니다.','Offline explanation · compare conditions and inspect their evidence.');
  document.documentElement.dataset.ready='true';
})();
