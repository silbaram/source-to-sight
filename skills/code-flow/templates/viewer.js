(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('s2s-data').textContent);
  const ko = data.language.toLowerCase().startsWith('ko');
  const t = (kr, en) => ko ? kr : en;
  const $ = id => document.getElementById(id);
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const svg = (tag, attrs = {}) => {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    return node;
  };
  const labels = {
    confirmed: t('위치·내용 확인', 'Location & claim checked'),
    uncertain: t('추정 · 추가 확인 필요', 'Uncertain · needs review'),
    unverified: t('근거 위치 미확인', 'Location unverified'),
    context: t('설명을 위한 문맥', 'Context only')
  };
  const nodeMap = new Map(data.nodes.map(n => [n.id, n]));
  const edgeMap = new Map(data.edges.map(e => [e.id, e]));
  const evidenceMap = new Map(data.evidence.map(e => [e.id, e]));
  let detail = false, scenarioIndex = 0, stepIndex = -1, timer = null, selected = null;
  let returnFocus = null, announcementTimer = null;

  async function copy(text) {
    try {
      if (!navigator.clipboard) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(text);
    } catch {
      const field = element('textarea', text);
      field.style.cssText = 'position:fixed;left:0;bottom:0;width:1px;height:1px;opacity:.01';
      document.body.append(field);
      field.select();
      const ok = document.execCommand('copy');
      field.remove();
      if (!ok) {
        announce(t('자동 복사가 안 됩니다. 표시된 텍스트를 선택해 복사해 주세요.', 'Select the displayed text to copy it.'));
        return;
      }
    }
    announce(t('복사했습니다.', 'Copied.'));
  }
  function announce(text) {
    clearTimeout(announcementTimer);
    $('announcement').textContent = text;
    $('announcement').classList.add('visible');
    announcementTimer = setTimeout(() => $('announcement').classList.remove('visible'), 3000);
  }
  function statusBadge(item) {
    return element('span', labels[item.displayStatus], 'pill ' + item.displayStatus);
  }
  function list(parent, title, items) {
    if (!items.length) return;
    parent.append(element('h3', title));
    const ul = element('ul');
    items.forEach(text => ul.append(element('li', text)));
    parent.append(ul);
  }
  function linkControl(kind, link, title) {
    const names = {atlas:t('프로젝트 지도', 'Project map'),
                   behavior:t('동작 설명', 'Behavior'), logic:t('규칙과 이유', 'Rules & reasons')};
    if (link.generated) {
      const a = element('a', (title || names[kind]) + ' ↗');
      a.href = link.url;
      return a;
    }
    const button = element('button', (title || names[kind]) + t(' · 생성 명령 복사', ' · copy generation command'));
    button.type = 'button';
    button.title = link.command;
    button.addEventListener('click', () => copy(link.command));
    return button;
  }
  function evidenceSection(parent, ids) {
    if (!ids.length) return;
    parent.append(element('h3', t('확인한 위치', 'Evidence locations')));
    parent.append(element('p', t('소스 코드 본문은 표시하지 않습니다.', 'Source-code bodies are not included.'), 'panel-note'));
    for (const id of ids) {
      const e = evidenceMap.get(id);
      const block = element('div', undefined, 'evidence-item');
      block.append(element('div', e.locationStatus === 'passed' ? t('✓ 위치 일치', '✓ Location matches') :
        t('⚠ 위치를 다시 확인하지 못함', '⚠ Location could not be verified'),
        'evidence-status ' + e.locationStatus));
      block.append(element('div', e.file, 'location'));
      block.append(element('div', t('줄 ', 'Lines ') + e.startLine + '–' + e.endLine, 'location'));
      const button = element('button', t('경로 복사', 'Copy location'));
      button.type = 'button';
      button.addEventListener('click', () => copy(e.file + ':' + e.startLine + '-' + e.endLine));
      block.append(button);
      if (e.locationStatus === 'failed') block.append(element('p',
        t('파일·줄 범위·내용 변경 여부를 원본에서 확인해 주세요.', 'Check the original file, line range, and source revision.'), 'evidence-note'));
      parent.append(block);
    }
  }
  function showItem(item, focus = false) {
    selected = item.id;
    const body = $('panel-body');
    body.replaceChildren(statusBadge(item));
    const title = element('h2', item.label || item.plainText || item.caption);
    title.id = 'panel-title';
    body.append(title);
    if (item.codeName) body.append(element('p', item.codeName, 'code-name'));
    if (edgeMap.has(item.id)) {
      body.append(element('p', nodeMap.get(item.from).label + ' → ' + nodeMap.get(item.to).label, 'description'));
    } else if (item.summary) body.append(element('p', item.summary, 'description'));
    if (item.verificationNote) body.append(element('p', item.verificationNote, 'evidence-note'));
    if (item.actions?.length) {
      body.append(element('h3', t('이 동작에서 하는 일', 'Actions in this behavior')));
      const ul = element('ul');
      for (const action of item.actions) {
        const li = element('li', action.plainText);
        li.append(document.createTextNode(' '), statusBadge(action));
        evidenceSection(li, action.evidenceIds);
        ul.append(li);
      }
      body.append(ul);
    }
    for (const state of data.stateTransitions.filter(s => s.subjectNodeId === item.id)) {
      body.append(element('h3', t('상태 변화', 'State change')));
      const box = element('div', undefined, 'transition');
      box.append(statusBadge(state), element('p', state.from + ' → ' + state.to),
                 element('p', state.plainText));
      list(box, t('변경 조건', 'Changes when'), [state.trigger]);
      box.append(element('p', state.verificationNote, 'evidence-note'));
      evidenceSection(box, state.evidenceIds);
      body.append(box);
    }
    if (item.condition) {
      list(body, t('이 조건이면', 'When'), [item.condition]);
      list(body, t('이렇게 처리합니다', 'Then'), [item.outcome]);
    }
    evidenceSection(body, item.evidenceIds || []);
    for (const sourceId of item.sourceIds || []) {
      const source = data.sources.find(s => s.id === sourceId);
      const a = element('a', source.title + ' · ' + source.version);
      a.href = source.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      body.append(a);
    }
    if (focus || !matchMedia('(max-width:900px)').matches) $('panel').classList.add('open');
    if (focus && matchMedia('(max-width:900px)').matches) {
      returnFocus = document.activeElement;
      $('close-panel').focus();
    }
    paint();
  }
  function closePanel() {
    $('panel').classList.remove('open');
    if (returnFocus?.isConnected) returnFocus.focus();
  }
  function wrap(text, length = 13) {
    const characters = Array.from(text);
    const lines = [];
    for (let i = 0; i < characters.length; i += length) lines.push(characters.slice(i, i + length).join(''));
    return lines.length ? lines : [''];
  }
  function draw() {
    const canvas = $('canvas');
    const mobile = canvas.clientWidth < 600;
    const visible = data.nodes.filter(n => detail || n.importance === 'core');
    const visibleIds = new Set(visible.map(n => n.id));
    const edges = data.edges.filter(e => visibleIds.has(e.from) && visibleIds.has(e.to));
    const graph = new dagre.graphlib.Graph({multigraph:true});
    graph.setGraph({rankdir:mobile ? 'TB' : 'LR', nodesep:46, edgesep:24, ranksep:86, marginx:40, marginy:38});
    graph.setDefaultEdgeLabel(() => ({}));
    for (const n of visible) {
      const height = 106 + Math.max(0, wrap(n.label, 12).length - 1) * 18;
      graph.setNode(n.id, {width:220, height});
    }
    for (const e of edges) {
      graph.setEdge(e.from, e.to, {width:Math.min(140, Math.max(54, Array.from(e.label).length * 7)),
        height:wrap(e.label, 16).length * 14 + 10, labelpos:'c'}, e.id);
    }
    dagre.layout(graph);
    // Keep text legible. A deep graph uses a vertical reading direction instead
    // of shrinking the entire picture into unreadably small labels.
    if (!mobile && graph.graph().width > canvas.clientWidth * 1.15) {
      graph.setGraph({...graph.graph(),rankdir:'TB'});
      dagre.layout(graph);
    }
    const layout = graph.graph();
    const width = Math.max(canvas.clientWidth, layout.width || 0);
    const height = Math.max(330, layout.height || 0);
    const dx = (width - (layout.width || width)) / 2;
    const dy = (height - (layout.height || height)) / 2;
    $('stage').style.width = width + 'px';
    $('stage').style.height = height + 'px';
    const connections = $('connections');
    connections.replaceChildren();
    connections.setAttribute('width', width);
    connections.setAttribute('height', height);
    const defs = svg('defs');
    for (const [name,color] of [['normal','#426da9'],['uncertain','#916000'],['structural','#7656a6'],['data','#087c6b'],['active','#00896b']]) {
      const marker = svg('marker', {id:'arrow-'+name, markerWidth:10, markerHeight:8, refX:9, refY:4,
        orient:'auto', markerUnits:'userSpaceOnUse', viewBox:'0 0 10 8'});
      marker.append(svg('path', {d:'M 0 0 L 10 4 L 0 8 Z', fill:color}));
      defs.append(marker);
    }
    connections.append(defs);
    const layer = $('node-layer');
    layer.replaceChildren();
    for (const e of edges) {
      const result = graph.edge({v:e.from, w:e.to, name:e.id});
      const relation = ['registers','depends-on'].includes(e.type) ? 'structural' :
        ['passes-data','reads','writes','emits','consumes'].includes(e.type) ? 'data' : 'normal';
      const color = e.displayStatus !== 'confirmed' ? 'uncertain' : relation;
      const group = svg('g', {class:'edge '+e.displayStatus+' '+relation, tabindex:0, role:'button',
        'data-id':e.id, 'aria-label':nodeMap.get(e.from).label+' → '+nodeMap.get(e.to).label+': '+e.label});
      let routed = result.points;
      // Dagre 3.1.1 reserves space for self-edges, but its returned self-edge
      // points do not meet the node boundary. Route within that reserved space.
      if (e.from === e.to) {
        const box = graph.node(e.from);
        if (graph.graph().rankdir === 'TB') {
          const right=box.x+box.width/2, outer=Math.max(right+24,result.x-result.width/2-12);
          routed=[{x:right,y:box.y-box.height/4},{x:outer-10,y:box.y-box.height/4},
            {x:outer,y:box.y},{x:outer-10,y:box.y+box.height/4},{x:right,y:box.y+box.height/4}];
        } else {
          const bottom=box.y+box.height/2, outer=Math.max(bottom+24,result.y-result.height/2-12);
          routed=[{x:box.x-box.width/4,y:bottom},{x:box.x-box.width/4,y:outer-10},
            {x:box.x,y:outer},{x:box.x+box.width/4,y:outer-10},{x:box.x+box.width/4,y:bottom}];
        }
      }
      const points = routed.map(p => ({x:p.x+dx, y:p.y+dy}));
      const path = points.map((p,i) => (i ? 'L ' : 'M ')+p.x+' '+p.y).join(' ');
      group.append(svg('path', {class:'edge-hit',d:path}));
      group.append(svg('path', {class:'edge-path',d:path,'marker-end':'url(#arrow-'+color+')', 'data-marker':color}));
      const lines = wrap(e.label, 16);
      group.append(svg('rect', {class:'edge-label-bg',x:result.x+dx-result.width/2-5,
        y:result.y+dy-result.height/2,width:result.width+10,height:result.height}));
      const label = svg('text', {class:'edge-label',x:result.x+dx,y:result.y+dy-(lines.length-1)*7+3});
      for (const [i,line] of lines.entries()) {
        const span = svg('tspan', {x:result.x+dx,dy:i ? 14 : 0});
        span.textContent = line; label.append(span);
      }
      group.append(label);
      group.addEventListener('click', () => {stop();showItem(e,true);});
      group.addEventListener('keydown', event => {
        if (['Enter',' '].includes(event.key)) {event.preventDefault();event.stopPropagation();stop();showItem(e,true);}
      });
      connections.append(group);
    }
    for (const n of visible) {
      const position = graph.node(n.id);
      const button = element('button', undefined, 'node '+n.displayStatus);
      button.type = 'button'; button.dataset.id = n.id; button.dataset.kind = n.kind;
      button.style.cssText = 'left:'+(position.x+dx-position.width/2)+'px;top:'+
        (position.y+dy-position.height/2)+'px;width:'+position.width+'px;height:'+position.height+'px';
      button.setAttribute('aria-label', n.label+' — '+labels[n.displayStatus]);
      button.append(element('span',n.roleLabel,'node-role'),element('span',n.label,'node-label'));
      if (n.codeName) {const code=element('span',n.codeName,'node-code');code.title=n.codeName;button.append(code);}
      button.append(element('span',labels[n.displayStatus],'node-status '+n.displayStatus));
      button.addEventListener('click', () => {stop();showItem(n,true);});
      layer.append(button);
    }
    paint();
  }
  function currentStep() {
    return stepIndex >= 0 ? data.scenarios[scenarioIndex]?.steps[stepIndex] : null;
  }
  function paint() {
    const step = currentStep();
    const activeEdge = step?.edgeId;
    const edge = edgeMap.get(activeEdge);
    const activeNodes = new Set(edge ? [edge.from,edge.to] : step ? [step.nodeId] : []);
    for (const node of document.querySelectorAll('.node')) {
      node.classList.toggle('selected',node.dataset.id === selected);
      node.classList.toggle('active',activeNodes.has(node.dataset.id));
      node.setAttribute('aria-pressed', String(node.dataset.id === selected));
    }
    for (const node of document.querySelectorAll('.edge')) {
      const active = node.dataset.id === activeEdge;
      node.classList.toggle('active',active || node.dataset.id === selected);
      const path = node.querySelector('.edge-path');
      path.setAttribute('marker-end','url(#arrow-'+(active ? 'active' : path.dataset.marker)+')');
    }
  }
  function setStep(index) {
    const scenario = data.scenarios[scenarioIndex];
    if (!scenario) return;
    stepIndex = Math.max(0,Math.min(index,scenario.steps.length-1));
    const step = scenario.steps[stepIndex];
    const edge = edgeMap.get(step.edgeId);
    const ids = edge ? [edge.from,edge.to] : [step.nodeId];
    if (!detail && ids.some(id => nodeMap.get(id)?.importance === 'detail')) {
      detail = true; $('mode').value = 'detail'; draw();
    }
    $('step-count').textContent = String(stepIndex+1).padStart(2,'0')+' / '+String(scenario.steps.length).padStart(2,'0');
    $('caption').replaceChildren(document.createTextNode(step.caption+' '),statusBadge(step));
    $('returns').textContent = step.returns ? '↳ '+step.returns : '';
    $('previous').disabled = stepIndex === 0;
    $('next').disabled = stepIndex === scenario.steps.length-1;
    showItem(edge || nodeMap.get(step.nodeId));
    const target=document.querySelector('.node[data-id="'+ids[ids.length-1]+'"]');
    if(target){
      const canvas=$('canvas'),box=target.getBoundingClientRect(),frame=canvas.getBoundingClientRect();
      if(box.top<frame.top||box.bottom>frame.bottom||box.left<frame.left||box.right>frame.right){
        canvas.scrollTo({top:Math.max(0,target.offsetTop-(canvas.clientHeight-target.offsetHeight)/2),
          left:Math.max(0,target.offsetLeft-(canvas.clientWidth-target.offsetWidth)/2),behavior:'instant'});
      }
    }
    if (stepIndex === scenario.steps.length-1) stop();
    paint();
  }
  function stop() {
    clearInterval(timer);timer=null;
    $('play').textContent=t('▶ 자동 재생','▶ Play');
    $('play').setAttribute('aria-pressed','false');
  }
  function togglePlayback() {
    if (timer) {stop();return;}
    const steps=data.scenarios[scenarioIndex].steps;
    if (stepIndex >= steps.length-1 || stepIndex < 0) setStep(0);
    if (steps.length <= 1) return;
    $('play').textContent=t('Ⅱ 일시 정지','Ⅱ Pause');
    $('play').setAttribute('aria-pressed','true');
    timer=setInterval(() => setStep(stepIndex+1),1500);
  }
  function initialize() {
    document.querySelector('.skip').textContent=t('그림으로 바로 이동','Skip to diagram');
    $('snapshot').textContent=data.snapshot.repository+' · '+(data.snapshot.commit?.slice(0,8)||t('Git 정보 없음','No Git snapshot'))+
      (data.snapshot.workingTreeClean===false ? t(' · 미커밋 변경 있음',' · Uncommitted changes') : '');
    if(data.snapshot.branch) $('snapshot').textContent+=' · '+data.snapshot.branch;
    $('snapshot').textContent+='\n'+data.snapshot.generatedAt;
    $('layer-label').textContent={atlas:t('01 / 프로젝트 지도','01 / PROJECT MAP'),behavior:t('02 / 동작과 협력','02 / HOW IT WORKS'),logic:t('03 / 규칙과 이유','03 / RULES & REASONS')}[data.layer];
    $('status-badge').textContent={complete:t('지정 범위 확인','Scoped analysis'),partial:t('일부 미확인','Partial analysis'),insufficient:t('근거 부족','Insufficient evidence')}[data.analysis.status];
    if(data.analysis.status!=='complete') $('status-badge').classList.add('uncertain');
    $('title').textContent=data.summary.title;$('purpose').textContent=data.summary.purpose;
    $('provenance').textContent=data.provenance.kind==='synthetic' ?
      t('합성 예시 · 화면과 계약을 검증하는 데이터입니다. 실제 프로젝트 분석 결과가 아닙니다.','Synthetic example · tests the viewer contract; not a real project analysis.') :
      data.provenance.description+(data.provenance.humanReviewed?'':t(' · 사람 검토 전',' · Pending human review'));
    for (const [key,label] of [['inputs',t('입력','INPUT')],['outputs',t('결과','OUTPUT')]]) {
      if(!data.summary[key].length) continue;
      if($('io').childElementCount) $('io').append(element('span','→','io-arrow'));
      const box=element('div',undefined,'io-box');
      box.append(element('span',label,'io-tag'),element('span',data.summary[key].join(' · '),'io-text'));
      $('io').append(box);
    }
    for(const [kind,link] of Object.entries(data.links)) $('links').append(linkControl(kind,link));
    $('warnings').hidden=!data.warnings.length;
    $('warnings-title').textContent=t('확인할 점 ','Things to check: ')+data.warnings.length;
    $('warnings').open=data.analysis.status!=='complete'||data.warnings.some(w=>w.severity==='high');
    const warnings=element('ul');
    for(const warning of data.warnings) {
      const li=element('li',warning.message);
      for(const candidate of warning.candidates) li.append(element('div',candidate.label+' · '+candidate.file+':'+candidate.line,'warning-location'));
      warnings.append(li);
    }
    $('warning-list').append(warnings);
    $('diagram-title').textContent=t('그림으로 따라가기','Follow the picture');
    $('diagram-hint').textContent=data.scenarios.length?t('부분을 누르면 역할과 근거를 볼 수 있습니다.','Select a part to see its role and evidence.'):
      t('관계도입니다. 실행 순서를 뜻하지 않습니다.','A relationship map; it does not imply execution order.');
    $('mode-label').textContent=t('보기','View');
    for(const [value,label] of [['core',t('핵심','Core')],['detail',t('상세','Detail')]]) {const option=element('option',label);option.value=value;$('mode').append(option);}
    for(const [label,cls] of [[t('확인한 연결','Checked connection'),''],[t('추정·미확인','Uncertain / unverified'),'dashed'],[t('등록·의존 관계','Registration / dependency'),'relation']]) {
      const item=element('span',undefined,'legend-item');item.append(element('span',undefined,'legend-line '+cls),document.createTextNode(label));$('legend').append(item);
    }
    $('mode').addEventListener('change',()=>{stop();detail=$('mode').value==='detail';stepIndex=-1;draw();if(data.scenarios.length)setStep(0);});
    $('close-panel').setAttribute('aria-label',t('설명 닫기','Close explanation'));
    $('close-panel').addEventListener('click',closePanel);
    $('player').hidden=!data.scenarios.length;
    $('previous').setAttribute('aria-label',t('이전 단계','Previous step'));
    $('next').setAttribute('aria-label',t('다음 단계','Next step'));
    $('previous').addEventListener('click',()=>{stop();setStep(stepIndex-1);});
    $('next').addEventListener('click',()=>{stop();setStep(stepIndex+1);});
    $('play').addEventListener('click',togglePlayback);stop();
    data.scenarios.forEach((s,i)=>{const option=element('option',s.title);option.value=i;$('scenario').append(option);});
    $('scenario').addEventListener('change',()=>{stop();scenarioIndex=Number($('scenario').value);setStep(0);});
    for(const region of data.regions) {
      const block=element('div',undefined,'region');
      block.dataset.id=region.id;
      block.append(statusBadge(region),element('h3',region.label),element('p',region.summary));
      const evidenceButton=element('button',t('구역 근거 확인','View region evidence'));
      evidenceButton.type='button';
      evidenceButton.setAttribute('aria-label',region.label+' · '+t('구역 근거 확인','View region evidence'));
      evidenceButton.addEventListener('click',()=>{stop();showItem(region,true);});
      block.append(evidenceButton);
      for(const id of region.nodeIds) {const button=element('button',nodeMap.get(id).label);button.type='button';button.addEventListener('click',()=>{detail=true;$('mode').value='detail';draw();showItem(nodeMap.get(id),true);});block.append(button);}
      $('regions').append(block);
    }
    for(const subject of data.subjects) $('regions').append(linkControl('behavior',subject.link,subject.label));
    $('rules-section').hidden=!data.rules.length;$('rules-title').textContent=t('어떤 규칙을 따르나요?','What rules apply?');
    for(const rule of data.rules) {
      const box=element('article',undefined,'rule-card');
      box.append(statusBadge(rule),element('p',rule.plainText),element('small',rule.condition+' → '+rule.outcome));
      const button=element('button',t('근거 확인','View evidence'));button.type='button';button.addEventListener('click',()=>showItem(rule,true));box.append(button);$('rules-list').append(box);
    }
    $('scope-title').textContent=t('설명 범위와 한계','Scope and limitations');
    const scope=element('div',undefined,'scope-body-grid');
    const included=element('div');list(included,t('포함한 범위','Included'),data.subject.scope.includes);list(included,t('제외한 범위','Excluded'),data.subject.scope.excludes);
    const limitations=element('div');list(limitations,t('확인하지 못한 내용','Unresolved'),data.analysis.unresolved);list(limitations,t('탐색한 위치','Searched'),data.analysis.searched);list(limitations,t('한계','Limitations'),data.summary.limitations);list(limitations,t('다음 시도','Next attempts'),data.analysis.nextAttempts);
    scope.append(included,limitations);$('scope-body').append(scope);
    $('offline-note').textContent=t('오프라인 설명서 · 하위 페이지를 만든 뒤 상위 페이지를 새로 생성하면 링크가 갱신됩니다.','Offline explanation · regenerate the parent page after creating a child to update its links.');
    if(data.analysis.status==='insufficient') {
      $('workspace').hidden=true;$('insufficient').hidden=false;
      $('insufficient').append(element('h2',t('아직 설명할 근거가 충분하지 않습니다.','There is not enough evidence yet.')));
      list($('insufficient'),t('확인하지 못한 이유','Why'),data.analysis.unresolved);
      list($('insufficient'),t('살펴본 범위','Searched'),data.analysis.searched);
      list($('insufficient'),t('다음에 시도할 것','Next attempts'),data.analysis.nextAttempts);
    } else {
      draw();
      if(data.nodes.length) showItem(data.nodes.find(n=>n.importance==='core')||data.nodes[0]);
      if(data.scenarios.length) setStep(0);
      $('panel').classList.remove('open');
    }
    let resizeTimer;
    addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(data.analysis.status!=='insufficient')draw();},120);});
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape')closePanel();
      if(!data.scenarios.length||event.target.closest('input,select,textarea,[contenteditable]'))return;
      if(event.key==='ArrowRight'){event.preventDefault();stop();setStep(stepIndex+1);}
      if(event.key==='ArrowLeft'){event.preventDefault();stop();setStep(stepIndex-1);}
    });
    document.documentElement.dataset.ready='true';
  }
  initialize();
})();
