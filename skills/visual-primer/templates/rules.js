(() => {
  'use strict';
  const data=JSON.parse(document.getElementById('s2s-data').textContent);
  const ko=data.language.toLowerCase().startsWith('ko');
  const t=(kr,en)=>ko?kr:en;
  // Shared navigation/copy handlers do not own links or controls inside scenes.
  const navigationSelector='#explanation > .primer-intro > .links';
  // The return value contains only map state. The destination remains the
  // identity-checked relative atlas link from the page's own metadata.
  const returnAtlas=new URLSearchParams(location.search).get('s2s-atlas');
  if(returnAtlas?.startsWith('#s2s=1&')&&returnAtlas.length<16000) {
    for(const link of document.querySelectorAll(navigationSelector+' > a[data-layer]')) {
      const target=new URL(link.getAttribute('href'),location.href);
      if(link.dataset.layer==='atlas')target.hash=returnAtlas;
      else target.searchParams.set('s2s-atlas',returnAtlas);
      link.href=target.href;
    }
  }
  // Node selection is scoped to the already identity-checked behavior/lesson pair.
  // Match the builder's rule bindings, never scene-owned navigation or markup.
  const params=new URLSearchParams(location.search);
  const selectedNode=data.nodes.find(node=>node.id===params.get('s2s-node'));
  const behaviorState=params.get('s2s-behavior');
  if(selectedNode) {
    const ruleIds=new Set(data.rules.filter(rule=>rule.nodeIds.includes(selectedNode.id)).map(rule=>rule.id));
    const figures=[...document.querySelectorAll('#explanation > .rule-figure')];
    const matches=figures.filter(figure=>[...figure.querySelectorAll('[data-rule-id]')].some(rule=>ruleIds.has(rule.dataset.ruleId)));
    const context=document.createElement('div');context.className='node-lesson-context';
    const label=document.createElement('p');label.textContent=t('선택한 처리 · ','Selected step · ')+selectedNode.label;context.append(label);
    const reset=document.createElement('button');reset.type='button';reset.textContent=t('이 기능의 다른 규칙도 보기','Show the other rules in this capability');context.append(reset);
    document.querySelector('#explanation > .primer-intro').after(context);
    if(matches.length) {
      for(const figure of figures)figure.hidden=!matches.includes(figure)&&!figure.classList.contains('withheld');
      for(const link of document.querySelectorAll('#explanation > .primer-contents > a')) {
        const target=document.getElementById(link.getAttribute('href').slice(1));link.hidden=!!target?.hidden;
      }
    } else label.textContent+=' · '+t('연결된 그림이 없어 전체 설명을 표시합니다.','No linked picture; showing the full explanation.');
    reset.addEventListener('click',()=>{
      for(const figure of figures)figure.hidden=false;
      for(const link of document.querySelectorAll('#explanation > .primer-contents > a'))link.hidden=false;
      label.textContent=t('전체 규칙 그림','All rule pictures');reset.hidden=true;
    });
    if(behaviorState?.startsWith('#s2s=1&')&&behaviorState.length<16000) {
      for(const link of document.querySelectorAll(navigationSelector+' > a[data-layer="behavior"]')) {
        const url=new URL(link.getAttribute('href'),location.href);url.hash=behaviorState;link.href=url.href;
      }
    }
  }
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
  // Only the builder's top-level legacy figures own these controls. Authored
  // scenes may use the same class names without opting into this behavior.
  for(const figure of document.querySelectorAll('#explanation > .rule-figure[data-kind="comparison"]')){
    const controls=figure.querySelector(':scope > .case-controls');
    const cases=[...figure.children].filter(n=>n.classList.contains('rule-case'));
    if(!controls||cases.length<2)continue;
    const buttons=[...controls.children].filter(n=>n.matches('button[data-case]'));
    if(buttons.length!==cases.length)continue;
    function select(index){
      cases.forEach((item,i)=>{item.hidden=i!==index;});
      buttons.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
    }
    buttons.forEach((button,index)=>button.addEventListener('click',()=>select(index)));
    controls.hidden=false;
    select(0);
  }
  let noticeTimer;
  for(const button of document.querySelectorAll(navigationSelector+' > button.copy-command[data-command]'))button.addEventListener('click',async()=>{
    const command=button.dataset.command;
    if(!command?.trim())return;
    let message=t('복사했습니다.','Copied.');
    try{await navigator.clipboard.writeText(command);}
    catch{
      const field=document.createElement('textarea');field.value=command;button.after(field);field.select();
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
