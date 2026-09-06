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
  let view = 'structure', focusId = null, zoom = 1, graphWidth = 0, graphHeight = 0;
  let laidOut = false;
  const history = [];
  const stepDuration = 1500, transferDuration = 1100;
  const reducedMotion = matchMedia('(prefers-reduced-motion:reduce)');
  const movingRelations = new Set(['invokes','passes-data','dispatches','reads','writes','emits','consumes','transitions','delegates']);
  let stepStartedAt = 0, transferFrame = null, transferToken = null, transferKey = null;

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
    if (focus && timer) stop();
    // A deliberate selection starts a new inspection, ending the previous
    // connection filter. Keep Back's camera/view history independently.
    if (focus && item.id !== focusId) focusId = null;
    selected = item.id;
    const body = $('panel-body');
    $('panel-status').replaceChildren(statusBadge(item));
    body.replaceChildren();
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
    $('focus-related').hidden = !nodeMap.has(item.id);
    if (focus) {
      returnFocus = document.activeElement;
      $('panel').classList.add('open');
      $('panel').inert = false;
      document.body.classList.add('panel-open');
      if (matchMedia('(max-width:900px)').matches) $('close-panel').focus({preventScroll:true});
      else $('canvas').scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});
      positionPanel();
      if (nodeMap.has(item.id)) revealNode(item.id);
    }
    updateNavigation();positionPanel();paint();
    // Reset after replacing content and sizing the flex body; otherwise the
    // browser can restore the previous evidence list's scroll anchor.
    body.scrollTop = 0;
  }
  function positionPanel() {
    const panel = $('panel');
    if (!panel.classList.contains('open')) return;
    // The mobile sheet uses its own dynamic-viewport limit. Clear desktop
    // coordinates when crossing the breakpoint with the inspector still open.
    if (matchMedia('(max-width:900px)').matches) {
      panel.style.removeProperty('top');
      panel.style.removeProperty('max-height');
      return;
    }
    const frame = $('canvas').parentElement.getBoundingClientRect();
    const inset = 16;
    const top = Math.max(inset, inset-frame.top);
    const bottom = Math.min(frame.height-inset, innerHeight-inset-frame.top);
    // When the map itself leaves the viewport, let its inspector leave with it.
    // Otherwise keep both the panel and its controls inside the visible map.
    const available = bottom-top;
    panel.style.top = (available >= 160 ? top : inset) + 'px';
    panel.style.maxHeight = Math.max(0, available >= 160 ? available :
      Math.min(frame.height-inset*2, innerHeight-inset*2)) + 'px';
  }
  function closePanel(restoreFocus = true) {
    $('panel').classList.remove('open');
    $('panel').inert = true;
    document.body.classList.remove('panel-open');
    if (restoreFocus && returnFocus?.isConnected) returnFocus.focus();
  }
  function wrap(text, length = 13) {
    const characters = Array.from(text);
    const lines = [];
    for (let i = 0; i < characters.length; i += length) lines.push(characters.slice(i, i + length).join(''));
    return lines.length ? lines : [''];
  }
  function draw() {
    clearTransfer();
    const canvas = $('canvas');
    const mobile = canvas.clientWidth < 600;
    const visible = data.nodes.filter(n => detail || n.importance === 'core');
    const visibleIds = new Set(visible.map(n => n.id));
    const edges = data.edges.filter(e => visibleIds.has(e.from) && visibleIds.has(e.to));
    // Graphlib uses object keys internally. Valid IR IDs such as "constructor"
    // must not reach that namespace; keep original IDs for UI and evidence.
    const layoutNodes = new Map(visible.map((n,i) => [n.id,'s2s-node-'+i]));
    const layoutEdges = new Map(edges.map((e,i) => [e.id,'s2s-edge-'+i]));
    const graph = new dagre.graphlib.Graph({multigraph:true});
    graph.setGraph({rankdir:mobile ? 'TB' : 'LR', nodesep:46, edgesep:24, ranksep:86, marginx:40, marginy:38});
    graph.setDefaultEdgeLabel(() => ({}));
    for (const n of visible) {
      const height = 106 + Math.max(0, wrap(n.label, 12).length - 1) * 18;
      graph.setNode(layoutNodes.get(n.id), {width:220, height});
    }
    for (const e of edges) {
      graph.setEdge(layoutNodes.get(e.from), layoutNodes.get(e.to), {width:Math.min(140, Math.max(54, Array.from(e.label).length * 7)),
        height:wrap(e.label, 16).length * 14 + 10, labelpos:'c'}, layoutEdges.get(e.id));
    }
    dagre.layout(graph);
    const layout = graph.graph();
    const width = Math.max(320, layout.width || 0);
    const height = Math.max(260, layout.height || 0);
    const dx = (width - (layout.width || width)) / 2;
    const dy = (height - (layout.height || height)) / 2;
    $('stage').style.width = width + 'px';
    $('stage').style.height = height + 'px';
    const connections = $('connections');
    connections.replaceChildren();
    connections.setAttribute('width', width);
    connections.setAttribute('height', height);
    const defs = svg('defs');
    for (const [name,color] of [['normal','var(--blue)'],['uncertain','var(--amber)'],['structural','var(--violet)'],['data','var(--teal)'],['active','var(--teal)']]) {
      const marker = svg('marker', {id:'arrow-'+name, markerWidth:10, markerHeight:8, refX:9, refY:4,
        orient:'auto', markerUnits:'userSpaceOnUse', viewBox:'0 0 10 8'});
      marker.append(svg('path', {d:'M 0 0 L 10 4 L 0 8 Z', fill:color}));
      defs.append(marker);
    }
    connections.append(defs);
    const layer = $('node-layer');
    layer.replaceChildren();
    for (const e of edges) {
      const result = graph.edge({v:layoutNodes.get(e.from), w:layoutNodes.get(e.to), name:layoutEdges.get(e.id)});
      const relation = ['registers','depends-on'].includes(e.type) ? 'structural' :
        ['passes-data','reads','writes','emits','consumes'].includes(e.type) ? 'data' : 'normal';
      const color = e.displayStatus !== 'confirmed' ? 'uncertain' : relation;
      const group = svg('g', {class:'edge '+e.displayStatus+' '+relation, tabindex:0, role:'button',
        'data-id':e.id, 'aria-label':nodeMap.get(e.from).label+' → '+nodeMap.get(e.to).label+': '+e.label});
      let routed = result.points;
      // Dagre 3.1.1 reserves space for self-edges, but its returned self-edge
      // points do not meet the node boundary. Route within that reserved space.
      if (e.from === e.to) {
        const box = graph.node(layoutNodes.get(e.from));
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
      const position = graph.node(layoutNodes.get(n.id));
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
    graphWidth = width; graphHeight = height;
    if (!laidOut) { fit(true); laidOut = true; }
    else applyZoom();
    updateMini();
    paint();
  }
  function currentStep() {
    return stepIndex >= 0 ? data.scenarios[scenarioIndex]?.steps[stepIndex] : null;
  }
  function stepConnection() {
    if (view !== 'flow') return null;
    const step = currentStep();
    if (!step) return null;
    if (step.edgeId) return edgeMap.get(step.edgeId);
    const previous = data.scenarios[scenarioIndex]?.steps[stepIndex-1];
    // Ordered node captions do not create calls, returns, or an event chain.
    // Use only an unambiguous, checked edge already present in that direction.
    if (!previous?.nodeId || previous.nodeId === step.nodeId ||
        previous.displayStatus !== 'confirmed' || step.displayStatus !== 'confirmed') return null;
    const matches = data.edges.filter(e => e.from === previous.nodeId && e.to === step.nodeId);
    return matches.length === 1 && matches[0].displayStatus === 'confirmed' &&
      movingRelations.has(matches[0].type) ? matches[0] : null;
  }
  function clearTransfer() {
    cancelAnimationFrame(transferFrame);
    transferFrame = null;
    transferToken?.remove();
    transferToken = null;
    transferKey = null;
    document.querySelectorAll('.node.flow-arrived').forEach(n => n.classList.remove('flow-arrived'));
  }
  function syncTransfer(edge) {
    const step = currentStep();
    if (!timer || !edge || edge.displayStatus !== 'confirmed' || step?.displayStatus !== 'confirmed' ||
        !movingRelations.has(edge.type) || reducedMotion.matches || document.hidden) {
      clearTransfer();
      return;
    }
    const key = scenarioIndex+':'+stepIndex+':'+edge.id;
    if (transferKey === key && transferToken?.isConnected) return;
    clearTransfer();
    const group = [...document.querySelectorAll('.edge')].find(n => n.dataset.id === edge.id);
    if (!group) return;
    const route = group.querySelector('.edge-path');
    const length = route.getTotalLength();
    if (!Number.isFinite(length) || length <= 0) return;
    transferKey = key;
    const token = svg('g', {class:'flow-token', 'aria-hidden':'true'});
    token.append(svg('circle',{class:'transfer-halo',r:10}),svg('circle',{class:'transfer-core',r:4.5}));
    group.append(token);
    transferToken = token;
    function frame(now) {
      const progress = Math.max(0,Math.min(1,(now-stepStartedAt)/transferDuration));
      const point = route.getPointAtLength(length*progress);
      token.setAttribute('transform','translate('+point.x+' '+point.y+')');
      token.style.opacity = String(Math.min(1,progress*12,(1-progress)*12));
      if (progress < 1) transferFrame = requestAnimationFrame(frame);
      else {
        transferFrame = null;
        const target = [...document.querySelectorAll('.node')].find(n => n.dataset.id === edge.to);
        target?.classList.add('flow-arrived');
      }
    }
    frame(performance.now());
  }
  function paint() {
    const step = view === 'flow' ? currentStep() : null;
    const edge = stepConnection();
    const activeEdge = edge?.id;
    const activeNodes = new Set(edge ? [edge.from,edge.to] : step ? [step.nodeId] : []);
    const neighbors = focusId ? new Set([focusId]) : null;
    if (neighbors) for (const e of data.edges) {
      if (e.from === focusId) neighbors.add(e.to);
      if (e.to === focusId) neighbors.add(e.from);
    }
    for (const node of document.querySelectorAll('.node')) {
      node.classList.toggle('dim', !!neighbors && !neighbors.has(node.dataset.id));
      node.classList.toggle('selected',node.dataset.id === selected);
      node.classList.toggle('active',activeNodes.has(node.dataset.id));
      node.classList.toggle('flow-origin',node.dataset.id === edge?.from);
      node.classList.toggle('flow-destination',node.dataset.id === edge?.to);
      node.setAttribute('aria-pressed', String(node.dataset.id === selected));
    }
    for (const node of document.querySelectorAll('.edge')) {
      const active = node.dataset.id === activeEdge;
      const relation = edgeMap.get(node.dataset.id);
      node.classList.toggle('dim', !!neighbors && relation.from !== focusId && relation.to !== focusId);
      node.classList.toggle('active',active || node.dataset.id === selected);
      const path = node.querySelector('.edge-path');
      path.setAttribute('marker-end','url(#arrow-'+((active || node.dataset.id === selected) &&
        relation.displayStatus === 'confirmed' ? 'active' : path.dataset.marker)+')');
    }
    const transfer = $('flow-transfer');
    transfer.hidden = !edge;
    transfer.replaceChildren();
    if (edge) {
      transfer.append(element('span',nodeMap.get(edge.from).label,'transfer-from'),
        element('span','→','transfer-arrow'),element('span',nodeMap.get(edge.to).label,'transfer-to'),
        element('span','· '+edge.label,'transfer-relation'),statusBadge(edge));
    }
    syncTransfer(edge);
  }
  function setStep(index, preserveFocus = false) {
    const scenario = data.scenarios[scenarioIndex];
    if (!scenario) return;
    if (!preserveFocus) focusId = null;
    stepIndex = Math.max(0,Math.min(index,scenario.steps.length-1));
    stepStartedAt = performance.now();
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
    if (view === 'flow') {
      const connection = stepConnection();
      if (timer && connection) revealConnection(connection);
      else revealNode(ids[ids.length-1]);
    }
    paint();
  }
  function stop() {
    clearInterval(timer);timer=null;
    $('play').textContent=t('▶ 자동 재생','▶ Play');
    $('play').setAttribute('aria-pressed','false');
    paint();
  }
  function togglePlayback() {
    if (timer) {stop();return;}
    const steps=data.scenarios[scenarioIndex].steps;
    if (stepIndex >= steps.length-1 || stepIndex < 0) setStep(0);
    $('play').textContent=t('Ⅱ 일시 정지','Ⅱ Pause');
    $('play').setAttribute('aria-pressed','true');
    stepStartedAt = performance.now();
    timer=setInterval(() => {
      if (stepIndex >= steps.length-1) stop();
      else setStep(stepIndex+1);
    },stepDuration);
    const connection = stepConnection();
    if (connection) revealConnection(connection);
    else if (currentStep()?.nodeId) revealNode(currentStep().nodeId);
    paint();
  }
  function applyZoom() {
    const canvas = $('canvas');
    $('stage').style.transform = 'scale('+zoom+')';
    // Space around every graph edge lets even the last node move clear of a
    // drawer. Keep this space stable when opening/closing panels for Back.
    $('graph-space').style.width = graphWidth*zoom+2*canvas.clientWidth+'px';
    $('graph-space').style.height = graphHeight*zoom+2*canvas.clientHeight+'px';
    $('stage').style.left = canvas.clientWidth+'px';
    $('stage').style.top = canvas.clientHeight+'px';
    $('zoom-level').textContent = Math.round(zoom*100)+'%';
    $('zoom-out').disabled = zoom <= .2;
    $('zoom-in').disabled = zoom >= 2;
    updateMini();
  }
  function setZoom(value) {
    if (!graphWidth) return;
    const canvas = $('canvas'), stage = $('stage');
    const cx = (canvas.scrollLeft+canvas.clientWidth/2-stage.offsetLeft)/zoom;
    const cy = (canvas.scrollTop+canvas.clientHeight/2-stage.offsetTop)/zoom;
    zoom = Math.max(.2,Math.min(2,value));
    applyZoom();
    canvas.scrollLeft = cx*zoom+stage.offsetLeft-canvas.clientWidth/2;
    canvas.scrollTop = cy*zoom+stage.offsetTop-canvas.clientHeight/2;
    if ($('panel').classList.contains('open') && nodeMap.has(selected)) revealNode(selected);
    updateMini();
  }
  function fit(initial = false) {
    const canvas = $('canvas');
    const ratio = Math.min(1,(canvas.clientWidth-32)/graphWidth,(canvas.clientHeight-32)/graphHeight);
    zoom = Math.max(initial ? (canvas.clientWidth < 600 ? .8 : .55) : .2,ratio);
    applyZoom();
    canvas.scrollLeft=$('stage').offsetLeft+(graphWidth*zoom-canvas.clientWidth)/2;
    canvas.scrollTop=$('stage').offsetTop+(graphHeight*zoom-canvas.clientHeight)/2;
    if ($('panel').classList.contains('open') && nodeMap.has(selected)) revealNode(selected);
    updateMini();
  }
  function updateMini() {
    if (!graphWidth) return;
    const mini=$('mini'), canvas=$('canvas'), stage=$('stage');
    mini.setAttribute('viewBox','0 0 '+graphWidth+' '+graphHeight);
    mini.replaceChildren();
    for (const n of document.querySelectorAll('.node')) mini.append(svg('rect',{
      x:n.offsetLeft,y:n.offsetTop,width:n.offsetWidth,height:n.offsetHeight,rx:8
    }));
    mini.append(svg('rect',{class:'viewport',x:(canvas.scrollLeft-stage.offsetLeft)/zoom,
      y:(canvas.scrollTop-stage.offsetTop)/zoom,width:canvas.clientWidth/zoom,height:canvas.clientHeight/zoom}));
  }
  function visibleFrame() {
    const frame=$('canvas').getBoundingClientRect();
    const area={left:Math.max(0,frame.left)+16,right:Math.min(innerWidth,frame.right)-16,
      top:Math.max(0,frame.top)+16,bottom:Math.min(innerHeight,frame.bottom)-16};
    if ($('panel').classList.contains('open')) {
      const panel=$('panel').getBoundingClientRect();
      if (panel.left<area.right && panel.right>area.left && panel.top<area.bottom && panel.bottom>area.top) {
        if (matchMedia('(max-width:900px)').matches) area.bottom=Math.min(area.bottom,panel.top-16);
        else area.right=Math.min(area.right,panel.left-16);
      }
    }
    return area;
  }
  function revealConnection(edge) {
    const canvas = $('canvas');
    const nodes = [...document.querySelectorAll('.node')].filter(n => n.dataset.id === edge.from || n.dataset.id === edge.to);
    const group = [...document.querySelectorAll('.edge')].find(n => n.dataset.id === edge.id);
    if (!nodes.length || !group) return;
    const elements = [...nodes,group.querySelector('.edge-path'),group.querySelector('.edge-label-bg')];
    const bounds = () => {
      const boxes = elements.map(n => n.getBoundingClientRect());
      return {left:Math.min(...boxes.map(b => b.left)),right:Math.max(...boxes.map(b => b.right)),
        top:Math.min(...boxes.map(b => b.top)),bottom:Math.max(...boxes.map(b => b.bottom))};
    };
    // The play button can be below the map on a narrow screen. Frame the map
    // before fitting this connection, retaining room for an open inspector.
    canvas.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});
    positionPanel();
    let area = visibleFrame();
    if (area.bottom-area.top < 160) {
      canvas.scrollIntoView({block:'start',inline:'nearest',behavior:'instant'});
      positionPanel();area = visibleFrame();
    }
    let box = bounds();
    const ratio = Math.min((area.right-area.left)/(box.right-box.left),
      (area.bottom-area.top)/(box.bottom-box.top),1);
    if (ratio > 0 && ratio < 1) {
      zoom = Math.max(.2,zoom*ratio*.94);
      applyZoom();box = bounds();
    }
    canvas.scrollLeft += (box.left+box.right-area.left-area.right)/2;
    canvas.scrollTop += (box.top+box.bottom-area.top-area.bottom)/2;
    updateMini();
  }
  function revealNode(id) {
    const target=[...document.querySelectorAll('.node')].find(n=>n.dataset.id===id);
    if (!target) return;
    const canvas=$('canvas');
    let box=target.getBoundingClientRect(), area=visibleFrame();
    if (area.bottom-area.top<box.height || area.right-area.left<box.width) {
      // Bring the map above the mobile sheet, or back into the page viewport
      // after using a search/region control elsewhere in the document.
      canvas.scrollIntoView({block:'start',inline:'nearest',behavior:'instant'});
      area=visibleFrame();box=target.getBoundingClientRect();
    }
    if(box.top<area.top||box.bottom>area.bottom||box.left<area.left||box.right>area.right){
      canvas.scrollLeft+=(box.left+box.right-area.left-area.right)/2;
      canvas.scrollTop+=(box.top+box.bottom-area.top-area.bottom)/2;
    }
    updateMini();
  }
  function chooseNode(node) {
    stop();
    if (!detail && node.importance==='detail') {detail=true;$('mode').value='detail';draw();}
    showItem(node,true);
  }
  function changeMode() {
    stop();detail=$('mode').value==='detail';
    if (view==='flow' && data.scenarios.length) {
      stepIndex=-1;draw();setStep(0);
      return;
    }
    const visible=id=>detail||nodeMap.get(id)?.importance==='core';
    if (focusId && !visible(focusId)) focusId=null;
    const edge=edgeMap.get(selected);
    if ((nodeMap.has(selected) && !visible(selected)) || (edge && (!visible(edge.from)||!visible(edge.to)))) {
      selected=null;closePanel(false);
    }
    draw();updateNavigation();
    if (nodeMap.has(selected)) revealNode(selected);
  }
  function updateNavigation() {
    $('structure').setAttribute('aria-pressed',String(view==='structure'));
    $('workflow').setAttribute('aria-pressed',String(view==='flow'));
    $('overview').classList.toggle('active',view==='structure'&&!focusId);
    for(const button of $('flows').children) button.classList.toggle('active',view==='flow'&&Number(button.dataset.index)===scenarioIndex);
    $('crumb').textContent = focusId ? t('연결 강조 중 · ','Connections focused · ')+nodeMap.get(focusId).label : view==='flow' ?
      data.scenarios[scenarioIndex].title : t('설명 범위 / 구성','Explanation scope / structure');
    const focused = !!focusId && focusId === selected;
    $('focus-related').textContent = focused ? t('연결 강조 해제','Clear connection focus') : t('연결된 부분에 집중','Focus on connections');
    $('focus-related').setAttribute('aria-pressed',String(focused));
    $('back').hidden=!history.length;
  }
  function setView(value) {
    if (value !== view) focusId = null;
    stop();view=value;
    $('player').hidden=view!=='flow'||!data.scenarios.length;
    if(view==='flow'&&stepIndex<0)setStep(0);
    updateNavigation();paint();
  }
  function initializeCanvas() {
    const theme=$('theme-toggle');
    function paintTheme() {
      const dark=document.documentElement.dataset.theme==='dark';
      theme.setAttribute('aria-checked',String(dark));
      theme.setAttribute('aria-label',t('다크 모드','Dark mode'));
      theme.title=dark?t('다크 모드 끄기','Turn dark mode off'):t('다크 모드 켜기','Turn dark mode on');
      $('theme-label').textContent=t('다크 모드','Dark mode');
    }
    theme.addEventListener('click',()=>{
      const value=document.documentElement.dataset.theme==='dark'?'light':'dark';
      document.documentElement.dataset.theme=value;
      try{localStorage.setItem('s2s-atlas-theme',value);}catch{/* File storage may be unavailable. */}
      paintTheme();
    });
    paintTheme();
    $('summary-details-title').textContent=t('입력과 결과 보기','Inputs and outputs');
    $('rail').setAttribute('aria-label',t('설명 탐색','Explore explanation'));
    $('rail-label').textContent='EXPLORE';
    $('search').placeholder=t('구성 요소 검색','Search components');
    $('search').setAttribute('aria-label',$('search').placeholder);
    $('overview').textContent=data.layer==='atlas'?t('◈ 전체 구성','◈ Overview'):t('◈ 설명 범위의 구성','◈ Scoped overview');
    $('list-title').textContent=t('구성 요소 목록','Components')+' · '+data.nodes.length;
    $('flows-title').textContent=t('대표 흐름','WALKTHROUGHS');
    $('rail-note').textContent=t('목록에서 부분을 찾거나 지도를 움직여 살펴보세요. 설명 범위와 미확인 내용은 아래에서 확인할 수 있습니다.',
      'Find a part in the list or move around the map. Scope and unresolved details are listed below.');
    $('structure').textContent=t('구성 보기','Structure');
    $('workflow').textContent=t('흐름 따라가기','Walkthrough');
    $('workflow').hidden=!data.scenarios.length;$('flow-list').hidden=!data.scenarios.length;
    $('view-switch').setAttribute('aria-label',t('설명 관점','Explanation view'));
    $('story-note').textContent=t('설명 순서 · 실제 실행 기록이 아닙니다','Explanation sequence · not a recorded execution');
    $('flow-transfer').setAttribute('aria-label',t('이번 단계의 연결 방향','Connection direction for this step'));
    $('scenario').setAttribute('aria-label',t('설명 흐름','Walkthrough'));
    $('back').textContent=t('← 돌아가기','← Back');
    $('zoom-out').setAttribute('aria-label',t('축소','Zoom out'));
    $('zoom-in').setAttribute('aria-label',t('확대','Zoom in'));
    $('fit').textContent=t('전체','Fit');
    $('fit').setAttribute('aria-label',t('지도를 화면에 맞추기','Fit map to view'));
    $('canvas').setAttribute('aria-label',t('관계도. 드래그 또는 방향키로 이동, +와 -로 확대 축소, 0으로 전체 보기',
      'Relationship map. Drag or use arrow keys to move, + and - to zoom, 0 to fit.'));
    $('connections').setAttribute('aria-label',t('구성 요소 사이의 관계','Relationships between components'));
    $('links').setAttribute('aria-label',t('관련 설명','Related explanations'));
    for(const node of data.nodes) {
      const button=element('button',node.label);button.type='button';button.dataset.nodeId=node.id;
      button.append(element('small',node.roleLabel));
      button.addEventListener('click',()=>chooseNode(node));$('component-list').append(button);
    }
    $('search').addEventListener('input',()=>{
      const query=$('search').value.trim().toLocaleLowerCase();
      $('results').replaceChildren();$('results').hidden=!query;
      if(!query)return;
      const matches=data.nodes.filter(n=>[n.label,n.codeName,n.roleLabel].some(v=>v?.toLocaleLowerCase().includes(query)));
      for(const node of matches){const button=element('button',node.label);button.type='button';button.addEventListener('click',()=>chooseNode(node));$('results').append(button);}
      if(!matches.length)$('results').append(element('p',t('일치하는 구성 요소가 없습니다.','No matching components.')));
    });
    data.scenarios.forEach((scenario,index)=>{
      const button=element('button',scenario.title);button.type='button';button.dataset.index=index;
      button.append(element('small',scenario.steps.length+t('개 설명 단계',' explanation steps')));
      button.addEventListener('click',()=>{scenarioIndex=index;$('scenario').value=String(index);setView('flow');setStep(0);});
      $('flows').append(button);
    });
    $('structure').addEventListener('click',()=>setView('structure'));
    $('workflow').addEventListener('click',()=>setView('flow'));
    $('overview').addEventListener('click',()=>{history.length=0;focusId=null;selected=null;closePanel();setView('structure');fit();});
    $('focus-related').addEventListener('click',()=>{
      if(!nodeMap.has(selected))return;
      if(focusId===selected){focusId=null;updateNavigation();paint();return;}
      stop();
      history.push({focusId,selected,zoom,detail,view,scenarioIndex,stepIndex,left:$('canvas').scrollLeft,top:$('canvas').scrollTop});
      focusId=selected;closePanel();revealNode(focusId);updateNavigation();paint();
    });
    $('back').addEventListener('click',()=>{
      const saved=history.pop();if(!saved)return;stop();closePanel();
      ({focusId,selected,zoom,detail,view,scenarioIndex,stepIndex}=saved);
      $('mode').value=detail?'detail':'core';$('scenario').value=String(scenarioIndex);draw();
      if(stepIndex>=0){const selection=selected;setStep(stepIndex,true);selected=selection;}
      setView(view);$('canvas').scrollLeft=saved.left;$('canvas').scrollTop=saved.top;
      if(nodeMap.has(selected))showItem(nodeMap.get(selected));
      updateMini();paint();
    });
    $('zoom-in').addEventListener('click',()=>setZoom(zoom*1.2));
    $('zoom-out').addEventListener('click',()=>setZoom(zoom/1.2));
    $('fit').addEventListener('click',()=>fit());
    $('canvas').addEventListener('scroll',updateMini,{passive:true});
    let drag=null;
    $('canvas').addEventListener('pointerdown',event=>{
      if(event.button!==0||event.pointerType==='touch'||event.target.closest('button,.edge'))return;
      drag={x:event.clientX,y:event.clientY,left:$('canvas').scrollLeft,top:$('canvas').scrollTop};
      $('canvas').setPointerCapture(event.pointerId);$('canvas').classList.add('dragging');
    });
    $('canvas').addEventListener('pointermove',event=>{
      if(!drag)return;
      $('canvas').scrollLeft=drag.left+drag.x-event.clientX;$('canvas').scrollTop=drag.top+drag.y-event.clientY;
    });
    function endDrag(){drag=null;$('canvas').classList.remove('dragging');}
    $('canvas').addEventListener('pointerup',endDrag);$('canvas').addEventListener('pointercancel',endDrag);
    $('canvas').addEventListener('keydown',event=>{
      if(event.target!==$('canvas'))return;
      if(['+','=','-','0','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))event.preventDefault();
      if(['+','='].includes(event.key))setZoom(zoom*1.2);
      if(event.key==='-')setZoom(zoom/1.2);
      if(event.key==='0')fit();
      if(event.key==='ArrowLeft')$('canvas').scrollLeft-=80;
      if(event.key==='ArrowRight')$('canvas').scrollLeft+=80;
      if(event.key==='ArrowUp')$('canvas').scrollTop-=80;
      if(event.key==='ArrowDown')$('canvas').scrollTop+=80;
    });
    updateNavigation();
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
    $('mode').addEventListener('change',changeMode);
    $('close-panel').setAttribute('aria-label',t('설명 닫기','Close explanation'));
    $('close-panel').addEventListener('click',closePanel);
    $('player').hidden=true;
    $('previous').setAttribute('aria-label',t('이전 단계','Previous step'));
    $('next').setAttribute('aria-label',t('다음 단계','Next step'));
    $('previous').addEventListener('click',()=>{stop();setStep(stepIndex-1);});
    $('next').addEventListener('click',()=>{stop();setStep(stepIndex+1);});
    $('play').addEventListener('click',togglePlayback);stop();
    data.scenarios.forEach((s,i)=>{const option=element('option',s.title);option.value=i;$('scenario').append(option);});
    $('scenario').addEventListener('change',()=>{stop();scenarioIndex=Number($('scenario').value);setStep(0);updateNavigation();});
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
      if(data.scenarios.length) setStep(0);
      selected=null;
      closePanel();
      paint();
    }
    let resizeTimer;
    addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{
      if(data.analysis.status!=='insufficient') {
        draw();
        positionPanel();
        if(timer && stepConnection())revealConnection(stepConnection());
        else if($('panel').classList.contains('open') && nodeMap.has(selected))revealNode(selected);
        positionPanel();
      }
    },120);});
    let panelFrame;
    const schedulePanel = () => {
      cancelAnimationFrame(panelFrame);
      panelFrame = requestAnimationFrame(positionPanel);
    };
    addEventListener('scroll',schedulePanel,{passive:true});
    document.addEventListener('toggle',schedulePanel,true);
    reducedMotion.addEventListener('change',()=>paint());
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
    document.addEventListener('keydown',event=>{if(event.key==='Escape' && $('panel').classList.contains('open'))closePanel();});
    initializeCanvas();
    document.documentElement.dataset.ready='true';
  }
  initialize();
})();
