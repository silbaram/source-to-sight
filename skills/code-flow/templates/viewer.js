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
  const scenarioLabels = {
    typical:t('기본 경로','Typical path'), alternate:t('대안 경로','Alternate path'),
    error:t('오류 경로','Error path'), retry:t('재시도 경로','Retry path'), lifecycle:t('생명주기','Lifecycle')
  };
  const branchLabels = {
    normal:t('진행','Continue'), alternate:t('다른 경로','Alternative'), error:t('오류','Error'),
    retry:t('재시도','Retry'), stop:t('종료','Stop')
  };
  const executionLabels = {
    sequential:t('순서대로 진행','Sequential'), parallel:t('병렬 구간 · 내부 순서 미정','Parallel · no internal order'),
    unordered:t('대상 순서 미정','Unspecified target order')
  };
  const nonSequential = step => ['parallel','unordered'].includes(step?.execution);
  const nodeMap = new Map(data.nodes.map(n => [n.id, n]));
  const edgeMap = new Map(data.edges.map(e => [e.id, e]));
  const evidenceMap = new Map(data.evidence.map(e => [e.id, e]));
  let detail = false, scenarioIndex = 0, stepIndex = -1, timer = null, selected = null;
  let returnFocus = null, copyReturnFocus = null, announcementTimer = null;
  let view = 'structure', focusId = null, zoom = 1, graphWidth = 0, graphHeight = 0;
  let laidOut = false;
  const history = [];
  const stepDuration = 1500, transferDuration = 1100;
  const reducedMotion = matchMedia('(prefers-reduced-motion:reduce)');
  const movingRelations = new Set(['invokes','passes-data','dispatches','reads','writes','emits','consumes','transitions','delegates']);
  let stepStartedAt = 0, transferFrame = null, transferToken = null, transferKey = null;
  let stepElapsed = 0, playbackFrame = null, playbackState = 'idle';
  const isPlaying = () => playbackState === 'playing';
  const cameraDuration = 360;
  let cameraMotion = null, cameraFrame = null, preparingStep = false;
  let playbackRate = 1, navigationReady = false, restoringLocation = false;
  const isAtlas=data.layer==='atlas';
  if(isAtlas)view='overview';
  const regionMap=new Map(data.regions.map(r=>[r.id,r]));
  const subjectMap=new Map(data.subjects.map(s=>[s.id,s.scope?s:{...nodeMap.get(s.nodeId),...s}]));
  const selectedNodeId=()=>nodeMap.has(selected)?selected:subjectMap.get(selected)?.nodeId;
  let regionId=null;
  let entryTab='roles', entryQuery='', entryGroup='', entryAvailability='', entrySelected=null;
  let closeEntryPalette=()=>{}, closeEntryContext=()=>{}, openEntryContext=()=>{};
  const itemMap = new Map([...data.nodes,...data.edges,...data.rules,...data.regions,...data.stateTransitions,...subjectMap.values()].map(item=>[item.id,item]));
  const incomingAtlas=new URLSearchParams(location.search).get('s2s-atlas');
  const returnAtlas=incomingAtlas?.startsWith('#s2s=1&')&&incomingAtlas.length<16000?incomingAtlas:null;

  async function copy(text) {
    const trigger=document.activeElement;
    copyReturnFocus=trigger;
    try {
      if (!navigator.clipboard) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(text);
    } catch {
      // Clipboard permission can settle after a dialog has been dismissed or
      // replaced. Do not move focus into a stale or now-inert copy surface.
      if(!trigger.isConnected||trigger.closest('[hidden],[inert]')) {
        announce(t('복사하지 못했습니다. 필요하면 다시 시도해 주세요.','Copy failed. Try again if needed.'));return;
      }
      const field = element('textarea', text);
      field.style.cssText = 'position:fixed;left:0;bottom:0;width:1px;height:1px;opacity:.01';
      (isAtlas&&!$('entry-context').hidden?$('entry-context'):document.body).append(field);
      field.select();
      let ok = false;
      try {ok = document.execCommand('copy');} catch {/* Manual copying remains available. */}
      field.remove();
      if (!ok) {
        $('copy-fallback').hidden=false;
        $('copy-text').value=text;
        $('copy-text').focus();$('copy-text').select();
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
  function list(parent, title, items, seen) {
    const values=seen ? items.filter(value=>!seen.has(value)) : items;
    if (!values.length) return;
    if (seen) values.forEach(value=>seen.add(value));
    parent.append(element('h3', title));
    const ul = element('ul');
    values.forEach(text => ul.append(element('li', text)));
    parent.append(ul);
  }
  function linkControl(kind, link, title) {
    const names = {atlas:t('프로젝트 지도', 'Project map'),
                   behavior:t('동작 설명', 'Behavior'), logic:t('규칙과 이유', 'Rules & reasons')};
    if (link.generated) {
      const a = element('a', (title || names[kind]) + ' ↗');
      a.href = link.url;
      const update=()=>{
        const state=isAtlas&&kind==='behavior'?savedAtlasLocation():returnAtlas;
        if(!state)return;
        const url=new URL(link.url,location.href);
        if(kind==='atlas')url.hash=state;
        else url.searchParams.set('s2s-atlas',state);
        a.href=url.href;
      };
      update();a.addEventListener('click',update);a.addEventListener('auxclick',update);
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
    if (focus) stop();
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
    const description = edgeMap.has(item.id) ? nodeMap.get(item.from).label + ' → ' + nodeMap.get(item.to).label : item.summary;
    if (description) body.append(element('p', description, 'description'));
    // Different fields can carry the same sentence. Keep distinct review notes,
    // but do not repeat text already visible in this item's title or summary.
    const normalize = text => (text || '').replace(/\s+/g,' ').trim();
    const note = normalize(item.verificationNote);
    if (note && ![title.textContent,description].some(text => normalize(text) === note)) {
      body.append(element('p', item.verificationNote, 'evidence-note'));
    }
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
    if(isAtlas) {
      if(subjectMap.has(item.id)) {
        if(item.scope){list(body,t('설명할 범위','Explanation scope'),item.scope.includes);list(body,t('제외하는 범위','Excluded'),item.scope.excludes);}
        const navigation=element('div',undefined,'capability-action');
        navigation.append(linkControl('behavior',item.link));body.append(navigation);
      } else {
        if(regionMap.has(item.id)) {
          const enter=element('button',t('이 구역 펼쳐 보기','Explore this region'),'enter-region');
          enter.type='button';enter.addEventListener('click',()=>enterRegion(item.id));body.append(enter);
        }
        const owned=data.subjects.filter(s=>s.nodeId===item.id||item.nodeIds?.includes(s.nodeId));
        if(owned.length){body.append(element('h3',t('이 부분의 주요 기능','Capabilities in this part')));for(const s of owned)body.append(capabilityButton(s));}
      }
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
      positionPanel();
      if (nodeMap.has(item.id)) revealNode(item.id,!restoringLocation);
      else if (edgeMap.has(item.id)) revealConnection(item,!restoringLocation);
      else if(subjectMap.has(item.id))revealNode(item.nodeId,!restoringLocation);
      else moveCamera({...readCamera(),pageTop:mapPageTop()},!restoringLocation);
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
    const mobile=matchMedia('(max-width:900px)').matches;
    $('panel-size').hidden=!mobile;
    $('panel-size').textContent=document.body.classList.contains('panel-expanded')?t('그림 더 보기','More map'):t('설명 확대','More explanation');
    $('panel-size').setAttribute('aria-expanded',String(document.body.classList.contains('panel-expanded')));
    if (mobile) {
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
    finishCamera();
    $('panel').classList.remove('open');
    $('panel').inert = true;
    document.body.classList.remove('panel-open');
    if (restoreFocus && returnFocus?.isConnected) returnFocus.focus();
    syncLocation();
  }
  function wrap(text, length = 13) {
    const characters = Array.from(text);
    const lines = [];
    for (let i = 0; i < characters.length; i += length) lines.push(characters.slice(i, i + length).join(''));
    return lines.length ? lines : [''];
  }
  function draw(anchorId) {
    clearTransfer();
    const canvas = $('canvas');
    const focusedId=document.activeElement.closest?.('.node,.edge')?.dataset.id;
    const anchor = () => [...document.querySelectorAll('.node')].find(n => n.dataset.id === anchorId)?.getBoundingClientRect();
    const before = anchorId ? anchor() : null;
    const mobile = canvas.clientWidth < 600;
    const visible = visibleNodes();
    const visibleIds = new Set(visible.map(n => n.id));
    const edges = data.edges.filter(e => visibleIds.has(e.from) && visibleIds.has(e.to));
    // Graphlib uses object keys internally. Valid IR IDs such as "constructor"
    // must not reach that namespace; keep original IDs for UI and evidence.
    const layoutNodes = new Map(visible.map((n,i) => [n.id,'s2s-node-'+i]));
    const layoutEdges = new Map(edges.map((e,i) => [e.id,'s2s-edge-'+i]));
    const graph = new dagre.graphlib.Graph({multigraph:true,compound:isAtlas});
    // Compound groups reserve half a separation above their members. Keep
    // room for a 44px region control in either layout direction.
    graph.setGraph({rankdir:mobile ? 'TB' : 'LR', nodesep:isAtlas?112:46, edgesep:24, ranksep:isAtlas?112:86, marginx:40, marginy:38});
    graph.setDefaultEdgeLabel(() => ({}));
    for (const n of visible) {
      const height = 106 + Math.max(0, wrap(n.label, 12).length - 1) * 18;
      graph.setNode(layoutNodes.get(n.id), {width:220, height});
    }
    const groups=isAtlas?data.regions.filter(r=>r.nodeIds.some(id=>visibleIds.has(id))):[];
    const layoutGroups=new Map(groups.map((r,i)=>[r.id,'s2s-region-'+i]));
    for(const region of groups) {
      const id=layoutGroups.get(region.id);graph.setNode(id,{width:260,height:48});
      for(const child of region.nodeIds.filter(n=>visibleIds.has(n)))graph.setParent(layoutNodes.get(child),id);
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
    for (const [name,color] of [['normal','var(--blue)'],['uncertain','var(--amber)'],['structural','var(--violet)'],['data','var(--data)'],['active','var(--accent)']]) {
      const marker = svg('marker', {id:'arrow-'+name, markerWidth:10, markerHeight:8, refX:9, refY:4,
        orient:'auto', markerUnits:'userSpaceOnUse', viewBox:'0 0 10 8'});
      marker.append(svg('path', {d:'M 0 0 L 10 4 L 0 8 Z', fill:color}));
      defs.append(marker);
    }
    connections.append(defs);
    $('region-layer').replaceChildren();
    for(const region of groups) {
      const box=graph.node(layoutGroups.get(region.id));
      const block=element('div',undefined,'map-region '+region.displayStatus);
      block.dataset.id=region.id;
      block.style.cssText='left:'+(box.x+dx-box.width/2)+'px;top:'+(box.y+dy-box.height/2)+'px;width:'+box.width+'px;height:'+box.height+'px';
      const label=element('button',region.label,'map-region-label');label.type='button';
      label.setAttribute('aria-label',region.label+' · '+labels[region.displayStatus]);
      label.append(element('span',labels[region.displayStatus],'map-region-status'));
      label.addEventListener('click',()=>showItem(region,true));block.append(label);$('region-layer').append(block);
    }
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
    const after = before ? anchor() : null;
    if (after) {
      canvas.scrollLeft += (after.left+after.right-before.left-before.right)/2;
      canvas.scrollTop += (after.top+after.bottom-before.top-before.bottom)/2;
    }
    updateMini();
    paint();
    if(focusedId) [...document.querySelectorAll('.node,.edge')].find(n=>n.dataset.id===focusedId)?.focus({preventScroll:true});
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
    if (nonSequential(step) || nonSequential(previous) || !previous?.nodeId || previous.nodeId === step.nodeId ||
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
  function canAnimateTransfer(edge) {
    const step = currentStep();
    // A named, checked dispatch/call/join can cross a parallel boundary. It
    // describes that relationship, not an order between concurrent workers.
    // Node-only captions still cannot infer a transfer across that boundary.
    const explicit = step?.edgeId === edge?.id;
    return isPlaying() && !cameraMotion && !preparingStep && !!edge && (!nonSequential(step) || explicit) && edge.displayStatus === 'confirmed' &&
      step?.displayStatus === 'confirmed' && movingRelations.has(edge.type) && !reducedMotion.matches && !document.hidden;
  }
  function syncTransfer(edge) {
    if (!canAnimateTransfer(edge)) {
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
      const progress = Math.max(0,Math.min(1,elapsedStep(now)/transferDuration));
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
  function syncPlayback() {
    cancelAnimationFrame(playbackFrame);
    playbackFrame = null;
    const step = currentStep(), scenario = data.scenarios[scenarioIndex];
    if (view !== 'flow' || !step) return;
    const status = isPlaying() ? (cameraMotion ? t('다음 위치로 이동 중','Moving to the next focus') :
      step.execution === 'parallel' ? t('병렬 구간 설명 중','Explaining a parallel group') :
      step.execution === 'unordered' ? t('대상 순서 미정 · 설명 중','Explaining unspecified target order') :
      t('현재 단계 설명 중','Explaining this step')) : playbackState === 'complete' ? t('설명 재생 완료','Walkthrough complete') :
      playbackState === 'paused' ? t('일시 정지','Paused') : t('자동 재생 준비','Ready to play');
    $('playback-status').textContent = status;
    const progress = $('playback-progress');
    progress.setAttribute('aria-valuemax',String(scenario.steps.length));
    progress.setAttribute('aria-valuenow',String(stepIndex+1));
    progress.setAttribute('aria-valuetext',(stepIndex+1)+' / '+scenario.steps.length+' · '+status);
    // This is explanation progress, independent of whether a checked transfer
    // exists. Parallel groups must not look paused or acquire serial edges.
    function frame(now) {
      const elapsed = elapsedStep(now);
      const fraction = reducedMotion.matches ? (playbackState === 'complete' ? 1 : 0) : elapsed/stepDuration;
      $('playback-fill').style.transform = 'scaleX('+((stepIndex+fraction)/scenario.steps.length)+')';
      if (isPlaying() && !reducedMotion.matches && !document.hidden) playbackFrame = requestAnimationFrame(frame);
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
      node.classList.toggle('selected',node.dataset.id === (subjectMap.get(selected)?.nodeId||selected));
      node.classList.toggle('active',activeNodes.has(node.dataset.id));
      node.classList.toggle('flow-origin',node.dataset.id === edge?.from);
      node.classList.toggle('flow-destination',node.dataset.id === edge?.to);
      node.classList.toggle('explaining',isPlaying() && !cameraMotion && !preparingStep && activeNodes.has(node.dataset.id) && !canAnimateTransfer(edge) && !reducedMotion.matches);
      node.setAttribute('aria-current',node.dataset.id === (edge?.to || step?.nodeId) ? 'step' : 'false');
      node.setAttribute('aria-pressed', String(node.dataset.id === (subjectMap.get(selected)?.nodeId||selected)));
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
    syncPlayback();
    for(const button of document.querySelectorAll('[data-capability-id]'))button.classList.toggle('active',button.dataset.capabilityId===selected);
    for(const button of $('atlas-regions').children)button.classList.toggle('active',button.dataset.regionId===regionId);
    for(const block of $('region-layer').children)block.classList.toggle('selected',block.dataset.id===selected);
    syncLocation();
  }
  function setStep(index, preserveFocus = false) {
    const scenario = data.scenarios[scenarioIndex];
    if (!scenario) return;
    clearTimeout(timer);timer=null;
    cancelCamera();
    preparingStep = true;
    if (!preserveFocus) focusId = null;
    stepIndex = Math.max(0,Math.min(index,scenario.steps.length-1));
    stepElapsed = 0;
    if (!isPlaying()) playbackState = 'idle';
    stepStartedAt = performance.now();
    const step = scenario.steps[stepIndex];
    const edge = edgeMap.get(step.edgeId);
    const ids = edge ? [edge.from,edge.to] : [step.nodeId];
    if (!detail && ids.some(id => nodeMap.get(id)?.importance === 'detail')) {
      detail = true; $('mode').value = 'detail'; draw(edge?.from);
    }
    $('step-count').textContent = String(stepIndex+1).padStart(2,'0')+' / '+String(scenario.steps.length).padStart(2,'0');
    if($('step-picker').dataset.scenario!==scenario.id) {
      $('step-picker').replaceChildren();
      scenario.steps.forEach((item,i)=>{const option=element('option',(i+1)+'. '+item.caption);option.value=String(i);$('step-picker').append(option);});
      $('step-picker').dataset.scenario=scenario.id;
    }
    $('step-picker').value=String(stepIndex);
    $('caption').replaceChildren(document.createTextNode(step.caption+' '),statusBadge(step));
    $('step-context').replaceChildren(element('span', scenarioLabels[scenario.kind], 'path-tag'));
    if (step.branch) $('step-context').append(element('span', branchLabels[step.branch], 'path-tag'));
    if (step.execution) $('step-context').append(element('span', executionLabels[step.execution], 'path-tag'));
    $('step-condition').textContent = step.condition ? t('이 조건에서: ','When: ')+step.condition : '';
    $('step-condition').hidden = !step.condition;
    $('returns').textContent = step.returns ? '↳ '+step.returns : '';
    $('previous').disabled = stepIndex === 0;
    $('next').disabled = stepIndex === scenario.steps.length-1;
    showItem(edge || nodeMap.get(step.nodeId));
    preparingStep = false;
    if (view === 'flow') {
      revealStep(!restoringLocation,isPlaying() ? startStepClock : null);
    }
    paint();
  }
  function elapsedStep(now = performance.now()) {
    return isPlaying() && !cameraMotion && !preparingStep ? Math.max(0,Math.min(stepDuration,stepElapsed+(now-stepStartedAt)*playbackRate)) : stepElapsed;
  }
  function startStepClock() {
    if (!isPlaying()) return;
    stepStartedAt = performance.now();
    clearTimeout(timer);
    timer = setTimeout(advancePlayback,(stepDuration-stepElapsed)/playbackRate);
    paint();
  }
  function stop(completed = false) {
    if (isPlaying()) {
      stepElapsed = completed ? stepDuration : elapsedStep();
      playbackState = completed ? 'complete' : 'paused';
    }
    clearTimeout(timer);timer=null;
    cancelCamera();
    $('play').textContent=t('▶ 자동 재생','▶ Play');
    $('play').setAttribute('aria-pressed','false');
    paint();
  }
  function advancePlayback() {
    if (!isPlaying()) return;
    if (stepIndex >= data.scenarios[scenarioIndex].steps.length-1) stop(true);
    else setStep(stepIndex+1);
  }
  function togglePlayback() {
    if(view!=='flow'||!data.scenarios[scenarioIndex])return;
    if (isPlaying()) {stop();return;}
    const steps=data.scenarios[scenarioIndex].steps;
    if (playbackState === 'complete' || stepIndex < 0 || (stepIndex === steps.length-1 && playbackState !== 'paused')) setStep(0);
    $('play').textContent=t('Ⅱ 일시 정지','Ⅱ Pause');
    $('play').setAttribute('aria-pressed','true');
    playbackState = 'playing';
    revealStep(true,startStepClock);
    paint();
  }
  function changeSpeed() {
    const next=Number($('playback-speed').value);
    if(![1,1.5,2].includes(next))return;
    // Keep elapsed explanation time, including while paused or framing a node.
    // Speed scales the reading clock and transfer together, never the camera.
    stepElapsed=elapsedStep();
    playbackRate=next;
    document.documentElement.style.setProperty('--step-interval',(stepDuration/playbackRate)+'ms');
    if(isPlaying()&&!cameraMotion&&!preparingStep)startStepClock();
    else paint();
  }
  function revealStep(smooth, done) {
    const connection = stepConnection();
    if (connection) revealConnection(connection,smooth,done);
    else if (currentStep()?.nodeId) revealNode(currentStep().nodeId,smooth,done);
    else done?.();
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
    finishCamera();
    const canvas = $('canvas'), stage = $('stage');
    const cx = (canvas.scrollLeft+canvas.clientWidth/2-stage.offsetLeft)/zoom;
    const cy = (canvas.scrollTop+canvas.clientHeight/2-stage.offsetTop)/zoom;
    zoom = Math.max(.2,Math.min(2,value));
    applyZoom();
    canvas.scrollLeft = cx*zoom+stage.offsetLeft-canvas.clientWidth/2;
    canvas.scrollTop = cy*zoom+stage.offsetTop-canvas.clientHeight/2;
    if ($('panel').classList.contains('open') && selectedNodeId()) revealNode(selectedNodeId());
    updateMini();
  }
  function fit(initial = false) {
    if (!initial) finishCamera();
    const canvas = $('canvas');
    const ratio = Math.min(1,(canvas.clientWidth-32)/graphWidth,(canvas.clientHeight-32)/graphHeight);
    zoom = Math.max(initial ? (canvas.clientWidth < 600 ? .8 : .55) : .2,ratio);
    applyZoom();
    canvas.scrollLeft=$('stage').offsetLeft+(graphWidth*zoom-canvas.clientWidth)/2;
    canvas.scrollTop=$('stage').offsetTop+(graphHeight*zoom-canvas.clientHeight)/2;
    if ($('panel').classList.contains('open') && selectedNodeId()) revealNode(selectedNodeId());
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
  function visibleFrame(pageTop = scrollY) {
    const frame=$('canvas').getBoundingClientRect();
    const shift=scrollY-pageTop;
    const area={left:Math.max(0,frame.left)+16,right:Math.min(innerWidth,frame.right)-16,
      top:Math.max(0,frame.top+shift)+16,bottom:Math.min(innerHeight,frame.bottom+shift)-16};
    if ($('panel').classList.contains('open')) {
      const panel=$('panel').getBoundingClientRect();
      if (panel.left<area.right && panel.right>area.left) {
        if (matchMedia('(max-width:900px)').matches) area.bottom=Math.min(area.bottom,panel.top-16);
        else area.right=Math.min(area.right,panel.left-16);
      }
    }
    return area;
  }
  function readCamera() {
    return {left:$('canvas').scrollLeft,top:$('canvas').scrollTop,zoom,pageTop:scrollY};
  }
  function applyCamera(position) {
    if (zoom !== position.zoom) {zoom=position.zoom;applyZoom();}
    $('canvas').scrollLeft=position.left;
    $('canvas').scrollTop=position.top;
    if (Math.abs(scrollY-position.pageTop)>.5) scrollTo({top:position.pageTop,behavior:'instant'});
    positionPanel();updateMini();
  }
  function cancelCamera() {
    cancelAnimationFrame(cameraFrame);
    cameraFrame=null;cameraMotion=null;
    $('canvas').classList.remove('camera-moving');
  }
  function finishCamera(snap = false) {
    const motion=cameraMotion;
    if (!motion) return;
    cancelCamera();
    if (snap) applyCamera(motion.to);
    if (motion.done) motion.done();
    else paint();
  }
  function moveCamera(target,smooth = false,done = null) {
    cancelCamera();
    const canvas=$('canvas'),from=readCamera();
    const to={zoom:Math.max(.2,Math.min(2,target.zoom)),
      left:Math.max(0,Math.min(graphWidth*target.zoom+canvas.clientWidth,target.left)),
      top:Math.max(0,Math.min(graphHeight*target.zoom+canvas.clientHeight,target.top)),
      pageTop:Math.max(0,Math.min(document.documentElement.scrollHeight-innerHeight,target.pageTop))};
    const distance=Math.max(Math.abs(to.left-from.left),Math.abs(to.top-from.top),Math.abs(to.pageTop-from.pageTop),
      Math.abs(to.zoom-from.zoom)*Math.max(graphWidth,graphHeight));
    if (!smooth || reducedMotion.matches || document.hidden || distance<2) {
      applyCamera(to);
      if (done) done(); else paint();
      return;
    }
    const motion={from,to,done,startedAt:performance.now()};
    cameraMotion=motion;
    $('canvas').classList.add('camera-moving');
    // Frame the explanation first; the transfer and its reading time start
    // only after this movement completes. New input can cancel this job.
    clearTransfer();
    function frame(now) {
      if (cameraMotion!==motion) return;
      const progress=Math.min(1,Math.max(0,(now-motion.startedAt)/cameraDuration));
      const ease=progress*progress*(3-2*progress);
      const position={};
      for (const key of ['left','top','zoom','pageTop']) position[key]=from[key]+(to[key]-from[key])*ease;
      applyCamera(position);
      if (progress<1) cameraFrame=requestAnimationFrame(frame);
      else finishCamera(true);
    }
    cameraFrame=requestAnimationFrame(frame);
  }
  function mapPageTop() {
    const frame=$('canvas').getBoundingClientRect();
    const bottom=$('panel').classList.contains('open') && matchMedia('(max-width:900px)').matches ?
      $('panel').getBoundingClientRect().top : innerHeight;
    let pageTop=scrollY;
    if (frame.top<0 || frame.height>bottom) pageTop+=frame.top;
    else if (frame.bottom>bottom) pageTop+=frame.bottom-bottom;
    return Math.max(0,Math.min(document.documentElement.scrollHeight-innerHeight,pageTop));
  }
  function frameBounds(box,smooth,done) {
    const canvas=$('canvas'),frame=canvas.getBoundingClientRect(),stage=$('stage');
    const pageTop=mapPageTop(),area=visibleFrame(pageTop),frameTop=frame.top+scrollY-pageTop;
    const left=frame.left+stage.offsetLeft+box.left*zoom-canvas.scrollLeft;
    const top=frameTop+stage.offsetTop+box.top*zoom-canvas.scrollTop;
    const width=(box.right-box.left)*zoom,height=(box.bottom-box.top)*zoom;
    if (left>=area.left && left+width<=area.right && top>=area.top && top+height<=area.bottom) {
      moveCamera({...readCamera(),pageTop},smooth,done);
      return;
    }
    const ratio=Math.min((area.right-area.left)/width,(area.bottom-area.top)/height,1);
    const targetZoom=ratio>0 && ratio<1 ? Math.max(.2,zoom*ratio*.94) : zoom;
    moveCamera({zoom:targetZoom,pageTop,
      left:stage.offsetLeft+(box.left+box.right)*targetZoom/2-((area.left+area.right)/2-frame.left),
      top:stage.offsetTop+(box.top+box.bottom)*targetZoom/2-((area.top+area.bottom)/2-frameTop)},smooth,done);
  }
  function revealConnection(edge,smooth = false,done = null) {
    const nodes = [...document.querySelectorAll('.node')].filter(n => n.dataset.id === edge.from || n.dataset.id === edge.to);
    const group = [...document.querySelectorAll('.edge')].find(n => n.dataset.id === edge.id);
    if (!nodes.length || !group) {done?.();return;}
    const boxes=nodes.map(n=>({x:n.offsetLeft,y:n.offsetTop,width:n.offsetWidth,height:n.offsetHeight}));
    boxes.push(group.querySelector('.edge-path').getBBox(),group.querySelector('.edge-label-bg').getBBox());
    frameBounds({left:Math.min(...boxes.map(b=>b.x)),right:Math.max(...boxes.map(b=>b.x+b.width)),
      top:Math.min(...boxes.map(b=>b.y)),bottom:Math.max(...boxes.map(b=>b.y+b.height))},smooth,done);
  }
  function revealNode(id,smooth = false,done = null) {
    const target=[...document.querySelectorAll('.node')].find(n=>n.dataset.id===id);
    if (!target) {done?.();return;}
    frameBounds({left:target.offsetLeft,top:target.offsetTop,right:target.offsetLeft+target.offsetWidth,
      bottom:target.offsetTop+target.offsetHeight},smooth,done);
  }
  function chooseNode(node, inspection=node) {
    stop();
    if(regionId&&!visibleNodes().some(n=>n.id===node.id)){regionId=null;draw();updateNavigation();}
    if (!detail && node.importance==='detail') {detail=true;$('mode').value='detail';draw(selectedNodeId()||edgeMap.get(selected)?.to);}
    showItem(inspection,true);
  }
  function changeMode() {
    stop();detail=$('mode').value==='detail';
    if (view==='flow' && data.scenarios.length) {
      stepIndex=-1;draw();setStep(0);
      return;
    }
    const visibleIds=new Set(visibleNodes().map(n=>n.id));
    const visible=id=>visibleIds.has(id);
    if (focusId && !visible(focusId)) focusId=null;
    const edge=edgeMap.get(selected);
    if ((selectedNodeId() && !visible(selectedNodeId())) || (edge && (!visible(edge.from)||!visible(edge.to)))) {
      selected=null;closePanel(false);
    }
    draw();updateNavigation();
    if (selectedNodeId()) revealNode(selectedNodeId());
  }
  function updateNavigation() {
    $('structure').setAttribute('aria-pressed',String(view==='structure'));
    $('workflow').setAttribute('aria-pressed',String(view==='flow'));
    $('overview').classList.toggle('active',view==='structure'&&!focusId&&!regionId);
    for(const button of $('flows').children) button.classList.toggle('active',view==='flow'&&Number(button.dataset.index)===scenarioIndex);
    $('crumb').textContent = focusId ? t('연결 강조 중 · ','Connections focused · ')+nodeMap.get(focusId).label : view==='flow' ?
      data.scenarios[scenarioIndex].title : regionId?regionMap.get(regionId).label:
      isAtlas?t('프로젝트 / 전체 구성','Project / overview'):t('설명 범위 / 구성','Explanation scope / structure');
    const focused = !!focusId && focusId === selected;
    $('focus-related').textContent = focused ? t('연결 강조 해제','Clear connection focus') : t('연결된 부분에 집중','Focus on connections');
    $('focus-related').setAttribute('aria-pressed',String(focused));
    $('back').hidden=!history.length;
  }
  function setView(value) {
    if (value !== view) focusId = null;
    stop();view=value;
    if(value==='flow'&&regionId){regionId=null;draw();}
    $('player').hidden=view!=='flow'||!data.scenarios.length;
    if(view==='flow'&&stepIndex<0)setStep(0);
    updateNavigation();paint();
  }
  function locationHash() {
    const params=new URLSearchParams({s2s:'1',subject:data.subject.id,view,detail:detail?'detail':'core',speed:String(playbackRate)});
    if(isAtlas&&view==='overview') {
      if(entryQuery)params.set('q',entryQuery);
      if(entryGroup)params.set('group',entryGroup);
      if(entryAvailability)params.set('available',entryAvailability);
      if(entrySelected)params.set('feature',entrySelected);
      return '#'+params.toString();
    }
    if(view==='flow'&&currentStep()) {
      params.set('scenario',data.scenarios[scenarioIndex].id);
      params.set('step',currentStep().id);
    }
    if(selected&&itemMap.has(selected))params.set(nodeMap.has(selected)?'node':edgeMap.has(selected)?'edge':'item',selected);
    if(selected&&$('panel').classList.contains('open'))params.set('panel','1');
    if(focusId)params.set('focus',focusId);
    if(regionId)params.set('region',regionId);
    return '#'+params.toString();
  }
  function savedAtlasLocation() {
    if(view==='overview')return locationHash();
    const params=new URLSearchParams(locationHash().slice(1));
    const camera=readCamera();
    params.set('camera',JSON.stringify([camera.zoom,...[camera.left,camera.top,camera.pageTop].map(n=>Math.round(n*1000)/1000)]));
    params.set('layout',JSON.stringify(cameraLayout()));
    return '#'+params.toString();
  }
  function cameraLayout() {
    return [innerWidth,innerHeight,$('canvas').clientWidth,$('canvas').clientHeight,graphWidth,graphHeight];
  }
  function syncLocation() {
    if(!navigationReady||restoringLocation||preparingStep||data.analysis.status==='insufficient')return;
    const hash=locationHash();
    if(location.hash===hash)return;
    // replaceState avoids creating a browser Back entry for every autoplay step.
    // Restricted file viewers can still copy a link from the current state.
    try{window.history.replaceState(null,'',hash);}catch{/* Keep navigation usable when URL updates are denied. */}
    $('navigation-notice').hidden=true;
  }
  function readLocation(hash) {
    const params=new URLSearchParams(hash.slice(1));
    const entryKeys=['tab','q','group','available','feature'];
    const allowed=new Set(['s2s','subject','view','detail','speed','scenario','step','node','edge','item','panel','focus','region','camera','layout',...entryKeys]);
    if([...params.keys()].some(key=>!allowed.has(key)||params.getAll(key).length!==1)||
      params.get('s2s')!=='1'||params.get('subject')!==data.subject.id||
      !(isAtlas?['overview','structure','flow']:['structure','flow']).includes(params.get('view'))||
      (params.has('detail')&&!['core','detail'].includes(params.get('detail')))||
      (params.has('speed')&&!['1','1.5','2'].includes(params.get('speed')))||
      (params.has('panel')&&params.get('panel')!=='1'))throw new Error('Invalid location');
    const result={view:params.get('view'),detail:params.get('detail')==='detail',rate:Number(params.get('speed')||1),scenario:0,step:-1,
      item:null,panel:params.has('panel'),focus:params.get('focus'),region:params.get('region'),camera:null,layout:null};
    if(result.view==='overview') {
      if(['scenario','step','node','edge','item','panel','focus','region','camera','layout'].some(k=>params.has(k))||
        (params.has('tab')&&!['roles','files'].includes(params.get('tab')))||
        (params.get('q')||'').length>240||
        (params.has('group')&&!regionMap.has(params.get('group')))||
        (params.has('available')&&!['ready','missing'].includes(params.get('available')))||
        (params.has('feature')&&!subjectMap.has(params.get('feature'))))throw new Error('Invalid overview');
      return {...result,tab:params.get('tab')||'roles',query:params.get('q')||'',group:params.get('group')||'',
        availability:params.get('available')||'',feature:params.get('feature')};
    }
    if(entryKeys.some(k=>params.has(k)))throw new Error('Unexpected overview state');
    if(result.region&&(!isAtlas||!regionMap.has(result.region)||result.view!=='structure'))throw new Error('Missing region');
    if(params.has('camera')) {
      result.camera=JSON.parse(params.get('camera'));
      if(!isAtlas||!Array.isArray(result.camera)||result.camera.length!==4||result.camera.some(n=>typeof n!=='number'||!Number.isFinite(n)||n<0||n>1e7)||result.camera[0]<.2||result.camera[0]>2)throw new Error('Invalid camera');
    }
    if(params.has('layout')) {
      result.layout=JSON.parse(params.get('layout'));
      if(!result.camera||!Array.isArray(result.layout)||result.layout.length!==6||result.layout.some(n=>typeof n!=='number'||!Number.isFinite(n)||n<=0||n>1e7))throw new Error('Invalid camera layout');
    }
    if(result.view==='flow') {
      result.scenario=data.scenarios.findIndex(s=>s.id===params.get('scenario'));
      if(result.scenario<0)throw new Error('Missing scenario');
      result.step=params.has('step')?data.scenarios[result.scenario].steps.findIndex(s=>s.id===params.get('step')):0;
      if(result.step<0)throw new Error('Missing step');
    } else if(params.has('scenario')||params.has('step'))throw new Error('Unexpected scenario');
    const selection=['node','edge','item'].filter(key=>params.has(key));
    if(selection.length>1)throw new Error('Ambiguous selection');
    if(selection.length) {
      const key=selection[0],id=params.get(key);
      if(!(key==='node'?nodeMap:key==='edge'?edgeMap:itemMap).has(id))throw new Error('Missing item');
      result.item=id;
    }
    if(result.panel&&!result.item)throw new Error('Missing inspection');
    if(result.focus&&(!nodeMap.has(result.focus)||result.focus!==result.item))throw new Error('Missing focus');
    return result;
  }
  function restoreLocation(hash) {
    if(hash&&hash!=='#'&&!hash.startsWith('#s2s='))return;
    let restored={view:isAtlas?'overview':'structure',detail:false,rate:1,scenario:0,step:-1,item:null,panel:false,focus:null},invalid=false;
    if(hash&&hash!=='#') {
      try{restored=readLocation(hash);}catch{invalid=true;}
    }
    restoringLocation=true;
    closeEntryContext(false);closeEntryPalette(false);
    stop();history.length=0;closePanel(false);
    selected=null;focusId=null;stepIndex=-1;stepElapsed=0;playbackState='idle';
    view=restored.view;detail=restored.detail;scenarioIndex=restored.scenario;playbackRate=restored.rate;regionId=restored.region||null;
    if(isAtlas) {
      if(view==='overview') {
        entryTab=restored.tab||'roles';entryQuery=restored.query||'';entryGroup=restored.group||'';
        entryAvailability=restored.availability||'';entrySelected=restored.feature||null;
        renderEntryFilters();
      }
      applyAtlasView();
    }
    if(data.analysis.status==='insufficient') {invalid=!!hash;view='structure';}
    else if(view!=='overview') {
      const inspection=itemMap.get(restored.item),edge=edgeMap.get(restored.item);
      const inspectedNodes=nodeMap.has(restored.item)?[restored.item]:subjectMap.has(restored.item)?[subjectMap.get(restored.item).nodeId]:edge?[edge.from,edge.to]:[];
      if(regionId&&inspectedNodes.some(id=>!visibleNodes().some(n=>n.id===id)))regionId=null;
      if(inspectedNodes.some(id=>nodeMap.get(id).importance==='detail'))detail=true;
      $('mode').value=detail?'detail':'core';$('scenario').value=String(scenarioIndex);
      $('playback-speed').value=String(playbackRate);
      document.documentElement.style.setProperty('--step-interval',(stepDuration/playbackRate)+'ms');
      draw();
      if(restored.step>=0)setStep(restored.step);
      if(inspection) {
        if(restored.panel)showItem(inspection,true);
        else selected=inspection.id;
      }
      focusId=restored.focus;
      if(nodeMap.has(selected))revealNode(selected);
      else if(edgeMap.has(selected))revealConnection(edgeMap.get(selected));
      else if(subjectMap.has(selected))revealNode(subjectMap.get(selected).nodeId);
      else if(view==='flow')revealStep(false);
      else fit();
      $('player').hidden=view!=='flow'||!data.scenarios.length;
      updateNavigation();paint();
      // Coordinates belong to the layout they were captured in. After a resize
      // (or for an older link without dimensions), keep the selection framed above.
      if(restored.camera&&restored.layout?.every((n,i)=>n===cameraLayout()[i])) {
        const [zoom,left,top,pageTop]=restored.camera;applyCamera({zoom,left,top,pageTop});updateMini();
      }
    }
    if(isAtlas&&view==='overview'&&entrySelected) {
      const card=entryCard(entrySelected);
      card?.focus({preventScroll:true});
      // Returning to a capability restores its visible location as well as
      // its selection. Apply immediately, including under reduced motion.
      card?.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});
    }
    restoringLocation=false;
    syncLocation();
    $('navigation-notice').textContent=invalid?t('현재 파일에서 링크의 위치를 찾을 수 없어 기본 화면으로 열었습니다.','This location is unavailable in the current file. The default view is shown.'):'';
    $('navigation-notice').hidden=!invalid;
  }
  function visibleNodes() {
    if(!isAtlas||!regionId)return data.nodes.filter(n=>detail||n.importance==='core');
    const members=new Set(regionMap.get(regionId).nodeIds),visible=new Set(members);
    for(const e of data.edges){if(members.has(e.from))visible.add(e.to);if(members.has(e.to))visible.add(e.from);}
    return data.nodes.filter(n=>visible.has(n.id));
  }
  function rememberView() {
    history.push({focusId,selected,zoom,detail,view,scenarioIndex,stepIndex,regionId,left:$('canvas').scrollLeft,top:$('canvas').scrollTop});
  }
  function enterRegion(id) {
    stop();rememberView();closePanel(false);regionId=id;focusId=null;selected=null;view='structure';
    $('player').hidden=true;
    draw();fit(true);updateNavigation();paint();
  }
  function capabilityButton(subject) {
    const button=element('button',subject.label,'capability-button');button.type='button';button.dataset.capabilityId=subject.id;
    button.append(element('small',subject.link.generated?t('동작 설명 준비됨','Explanation available'):t('상세 설명 미생성','Detail not generated')));
    button.addEventListener('click',()=>{
      chooseNode(nodeMap.get(subject.nodeId),subjectMap.get(subject.id));
    });return button;
  }
  function initializeAtlas() {
    if(!isAtlas)return;
    document.body.classList.add('atlas-page');$('atlas-navigation').hidden=false;$('atlas-summary').hidden=false;
    const counts=t('책임 구역 ','Responsibility regions ')+data.regions.length+' · '+t('구성 요소 ','Components ')+data.nodes.length+' · '+t('주요 기능 ','Capabilities ')+data.subjects.length;
    $('atlas-summary').append(element('span',counts));
    // Count recorded, reviewed items, not repository-wide or test coverage.
    // Legacy capabilities inherit the owner's review state, as their cards do.
    const reviewed=[...data.nodes.filter(n=>!n.contextOnly),...data.regions,...subjectMap.values(),...(data.structureEntries||[])];
    const checked=reviewed.filter(item=>item.displayStatus==='confirmed').length;
    const coverage=element('span',undefined,'coverage');
    coverage.style.setProperty('--coverage',(reviewed.length?checked/reviewed.length*100:0)+'%');
    coverage.append(element('span',t('기록된 항목 확인 ','Recorded items checked ')+checked+' / '+reviewed.length,'coverage-label'));
    coverage.title=t('이 지도에 기록된 구성 요소·구역·기능·경로의 확인 비율입니다. 프로젝트 전체나 테스트 커버리지가 아닙니다.','Review status of components, regions, capabilities and paths recorded in this map; not repository-wide or test coverage.');
    $('atlas-summary').append(coverage);
    const scope=element('button',t('분석 범위와 한계 ▸','Analysis scope and limits ▸'));scope.type='button';scope.addEventListener('click',()=>{
      if(view==='overview'&&!$('atlas-entry').hidden){$('entry-gaps').open=true;focusEntry($('entry-gaps-title'));}
      else {const section=$('scope-title').parentElement;section.open=true;section.scrollIntoView({behavior:reducedMotion.matches?'instant':'smooth'});}
    });$('atlas-summary').append(scope);
    $('atlas-regions-title').textContent=t('책임 구역','RESPONSIBILITIES');$('atlas-regions-title').hidden=!data.regions.length;
    $('capabilities-title').textContent=t('주요 기능','CAPABILITIES');$('capabilities-title').hidden=!data.subjects.length;
    for(const region of data.regions){const button=element('button',region.label);button.type='button';button.dataset.regionId=region.id;
      button.append(element('small',region.nodeIds.length+t('개 구성 · 펼쳐 보기',' parts · explore')));button.addEventListener('click',()=>enterRegion(region.id));$('atlas-regions').append(button);}
    for(const subject of data.subjects)$('capabilities').append(capabilityButton(subject));
    $('diagram-title').textContent=t('프로젝트를 한눈에','Explore the project');
    $('diagram-hint').textContent=t('구역을 펼치거나 주요 기능을 선택해 동작 설명으로 이동하세요.','Explore a responsibility region or choose a capability to open its explanation.');
    if(data.subjects.every(s=>s.scope))$('regions').hidden=true;
    initializeEntry();
  }
  function applyAtlasView() {
    const home=view==='overview', usable=data.analysis.status!=='insufficient';
    $('atlas-entry').hidden=!home||!usable;
    $('workspace').hidden=home||!usable;
    document.body.classList.toggle('atlas-overview',home);
    if(!home||!usable){closeEntryContext(false);closeEntryPalette(false);}
    const skip=document.querySelector('.skip');
    skip.href=home?'#entry-title':'#canvas';
    skip.textContent=home?t('프로젝트 소개로 건너뛰기','Skip to project overview'):t('다이어그램으로 건너뛰기','Skip to diagram');
  }
  function openEntryDiagram(action) {
    closeEntryContext(false);closeEntryPalette(false);
    restoreLocation('#'+new URLSearchParams({s2s:'1',subject:data.subject.id,view:'structure',detail:'core',speed:'1'}));
    $('canvas').scrollIntoView({block:'center'});
    $('canvas').focus({preventScroll:true});
    if(action)action();
  }
  function entryButton(label, handler, className) {
    const button=element('button',label,className);button.type='button';
    button.addEventListener('click',handler);return button;
  }
  function entryEvidence(item) {
    const details=element('details',undefined,'entry-evidence');
    details.append(element('summary',t('근거와 확인 메모','Evidence and review note')));
    details.append(element('p',item.verificationNote));
    evidenceSection(details,item.evidenceIds);
    return details;
  }
  function entryGlyph(kind) {
    const paths={
      feature:'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z',
      input:'M14 4h6v16h-6 M3 12h12 M9 6l6 6-6 6',
      output:'M10 4H4v16h6 M9 12h12 M15 6l6 6-6 6',
      project:'M12 3l9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5'
    };
    const icon=svg('svg',{viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.4','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',class:'entry-icon'});
    icon.append(svg('path',{d:paths[kind]||paths.feature}));return icon;
  }
  function entryCard(id) {
    return [...$('entry-features').querySelectorAll('.feature-card')].find(card=>card.dataset.featureId===id);
  }
  function entryPaths(nodeId) {
    return (data.structureEntries||[]).filter(entry=>entry.nodeIds.includes(nodeId));
  }
  function entryLandmark(nodeId) {
    return entryPaths(nodeId).filter(entry=>entry.path!=='.').sort((a,b)=>
      (a.kind==='file')-(b.kind==='file')||a.path.split('/').length-b.path.split('/').length||a.path.localeCompare(b.path))[0];
  }
  function openEntryPath(id) {
    const item=[...$('entry-files').querySelectorAll('.entry-tree-item')].find(el=>el.dataset.structureId===id);
    if(!item)return;
    closeEntryContext(false);closeEntryPalette(false);
    $('entry-files-section').open=true;
    for(let parent=item;parent&&parent!==$('entry-files');parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;
    focusEntry(item.querySelector('summary'));
  }
  function renderEntrySummary() {
    const summary=$('entry-summary');summary.replaceChildren();
    summary.setAttribute('aria-label',t('프로젝트의 입력과 결과 · 실행 순서가 아닙니다','Project inputs and outputs · not execution order'));
    summary.hidden=!data.summary.inputs.length&&!data.summary.outputs.length;
    for(const [key,label,kind] of [['inputs',t('들어오는 것','INPUT'),'input'],['outputs',t('만들어지는 것','OUTPUT'),'output']]) {
      if(key==='outputs') {
        const center=element('div',undefined,'entry-io-center');
        center.append(entryGlyph('project'),element('span',t('이 프로젝트','This project')));summary.append(center);
      }
      const box=element('div',undefined,'entry-io');
      const heading=element('p',label,'entry-io-label');heading.prepend(entryGlyph(kind));box.append(heading);
      const values=element('ul');
      for(const value of data.summary[key])values.append(element('li',value));
      if(!values.childElementCount)values.append(element('li',t('아직 기록되지 않았습니다.','Not recorded yet.')));
      box.append(values);summary.append(box);
    }
    const limits=[...new Set([...data.warnings.filter(w=>w.severity==='high').map(w=>w.message),...data.analysis.unresolved,...data.summary.limitations])];
    const alerts=$('entry-alerts');alerts.replaceChildren();alerts.hidden=!limits.length;
    if(limits.length) {
      alerts.append(element('span',t('확인하고 읽기','READ WITH CONTEXT'),'entry-alert-label'),element('p',limits[0]),
        entryButton(t('분석 범위 보기','Review scope'),()=>{$('entry-gaps').open=true;focusEntry($('entry-gaps-title'));}));
    }
  }
  function renderEntryFilters() {
    $('entry-search').value=entryQuery;$('entry-group').value=entryGroup;$('entry-availability').value=entryAvailability;
    const query=entryQuery.trim().toLocaleLowerCase();
    const matches=data.subjects.filter(subject=>{
      const owner=nodeMap.get(subject.nodeId),paths=entryPaths(subject.nodeId).map(entry=>entry.path);
      return (!entryGroup||regionMap.get(entryGroup).nodeIds.includes(subject.nodeId))&&
        (!entryAvailability||(entryAvailability==='ready')===subject.link.generated)&&
        [subject.label,subject.summary,subject.question,subject.module,owner.label,owner.codeName,...paths,
          ...(subject.targets||[]).flatMap(target=>[target.file,target.symbol,target.label])]
          .some(value=>value?.toLocaleLowerCase().includes(query));
    });
    $('entry-count').textContent=t('기록된 기능 ','Recorded capabilities: ')+matches.length+' / '+data.subjects.length;
    $('entry-features').replaceChildren();
    const containers=new Map();
    for(const subject of matches) {
      const item=subjectMap.get(subject.id),owner=nodeMap.get(subject.nodeId);
      const group=data.regions.find(region=>region.nodeIds.includes(subject.nodeId))||owner;
      if(!containers.has(group.id)) {
        const section=element('section',undefined,'entry-capability-group');section.dataset.groupId=group.id;section.setAttribute('aria-label',group.label);
        const heading=element('div',undefined,'entry-group-heading');
        const title=element('h3',group.label);heading.append(title);
        const belongs=capability=>(data.regions.find(region=>region.nodeIds.includes(capability.nodeId))?.id||capability.nodeId)===group.id;
        const shown=matches.filter(belongs).length,total=data.subjects.filter(belongs).length;
        const count=element('span',t('기능 ','Capabilities: ')+(shown===total?total:shown+' / '+total),'entry-group-count');
        count.title=t('현재 필터에 표시된 기능 / 이 그룹에 기록된 기능','Visible capabilities / capabilities recorded in this group');heading.append(count);
        if(regionMap.has(group.id))heading.append(statusBadge(group));
        heading.append(entryButton(t('그룹 관계도 ↗','Group diagram ↗'),()=>openEntryDiagram(()=>{
          if(regionMap.has(group.id))enterRegion(group.id);else chooseNode(owner);
        })));
        const cards=element('div',undefined,'entry-grid');
        section.append(heading,cards);$('entry-features').append(section);containers.set(group.id,cards);
      }
      const card=element('article',undefined,'entry-card feature-card');card.dataset.featureId=subject.id;card.tabIndex=-1;
      card.classList.toggle('entry-selected',entrySelected===subject.id);
      const title=element('h4'),selectButton=entryButton(undefined,()=>selectEntryFeature(subject.id,{reset:false,inspect:true}),'entry-select');
      selectButton.setAttribute('aria-haspopup','dialog');
      selectButton.setAttribute('aria-controls','entry-context');
      selectButton.title=t('기능 요약 열기: ','Open capability summary: ')+subject.label;
      selectButton.append(entryGlyph('feature'),element('span',subject.label),element('span','→','entry-select-arrow'));title.append(selectButton);
      card.append(title,element('p',subject.summary||owner.summary,'entry-feature-summary'));
      const meta=element('div',undefined,'entry-feature-meta');meta.append(element('span',t('담당 · ','Owner · ')+owner.label));
      const landmark=entryLandmark(owner.id);
      if(landmark) {
        const path=entryButton(landmark.path,()=>openEntryPath(landmark.id),'entry-path-link '+landmark.displayStatus);
        path.title=landmark.label+' · '+labels[landmark.displayStatus];
        if(landmark.displayStatus!=='confirmed')path.append(element('span',' · '+labels[landmark.displayStatus]));
        meta.append(path);
      }
      card.append(meta);
      const state=element('div',undefined,'entry-feature-state');state.append(statusBadge(item),
        element('span',subject.link.generated?t('상세 준비됨','Detail ready'):t('상세 문서 미생성','Detail not generated'),'entry-availability'));
      card.append(state);
      const actions=element('div',undefined,'entry-actions');
      const control=linkControl('behavior',subject.link);
      control.textContent=subject.link.generated?t('상세 흐름 →','Detailed flow →'):t('상세 생성 요청 복사','Copy detail request');
      // Capture the selected capability before return-state serialization.
      const select=()=>{entrySelected=subject.id;updateEntrySelection();syncLocation();};
      for(const event of ['click','auxclick'])control.addEventListener(event,select,{capture:true});
      actions.append(control,entryButton(t('구조에서 위치 보기','Locate in diagram'),()=>{entrySelected=subject.id;openEntryDiagram(()=>chooseNode(owner,item));}));
      card.append(actions);containers.get(group.id).append(card);
    }
    if(!matches.length)$('entry-features').append(element('p',data.subjects.length?
      t('일치하는 기능이 없습니다. 검색이나 필터를 초기화해 보세요.','No matching capabilities. Clear the search or filters.'):
      t('기능 목록이 아직 기록되지 않았습니다. 아래 구성과 분석 범위를 확인해 주세요.','No capabilities have been cataloged. Explore the components and analysis scope below.'),'entry-empty'));
    renderEntryContext();
  }
  function focusEntry(target) {
    if(!target)return;
    target.focus({preventScroll:true});
    target.scrollIntoView({block:'start',behavior:reducedMotion.matches?'instant':'smooth'});
  }
  function updateEntrySelection() {
    for(const card of $('entry-features').querySelectorAll('.feature-card')) {
      const active=entrySelected===card.dataset.featureId;
      card.classList.toggle('entry-selected',active);
    }
    renderEntryContext();
  }
  function selectEntryFeature(id,{reset=true,inspect=true}={}) {
    if(!subjectMap.has(id))return;
    entrySelected=id;
    if(reset&&(entryQuery||entryGroup||entryAvailability)) {
      entryQuery='';entryGroup='';entryAvailability='';renderEntryFilters();
    } else updateEntrySelection();
    syncLocation();
    const card=entryCard(id);
    if(!card)return;
    // Search/tree navigation has a new return destination. Direct card clicks
    // leave the page still, including when it is only partly in the viewport.
    if(reset)card.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});
    if(inspect)openEntryContext(card.querySelector('.entry-select'));
    else focusEntry(card);
  }
  function initializeEntryContext() {
    const overlay=$('entry-context'),box=overlay.querySelector('.entry-context-box'),fallback=$('copy-fallback');
    let previousFocus=null,background=[],previousOverflow='',previousPadding='',position=null,backdropStart=false;
    closeEntryContext=(restoreFocus=true)=>{
      if(overlay.hidden)return;
      overlay.hidden=true;
      fallback.hidden=true;document.body.insertBefore(fallback,$('announcement'));
      for(const [item,inert] of background)item.inert=inert;
      background=[];document.documentElement.style.overflow=previousOverflow;document.body.style.paddingRight=previousPadding;
      if(restoreFocus) {
        const target=previousFocus?.isConnected?previousFocus:entryCard(entrySelected)?.querySelector('.entry-select')||$('entry-title');
        target.focus({preventScroll:true});
        if(position)scrollTo({left:position.x,top:position.y,behavior:'instant'});
      }
      previousFocus=null;position=null;
    };
    openEntryContext=target=>{
      if(view!=='overview'||$('atlas-entry').hidden||!entryCard(entrySelected))return;
      closeEntryPalette(false);
      if(!overlay.hidden){$('entry-context-title').focus({preventScroll:true});return;}
      previousFocus=target;position={x:scrollX,y:scrollY};
      previousOverflow=document.documentElement.style.overflow;previousPadding=document.body.style.paddingRight;
      const gutter=innerWidth-document.documentElement.clientWidth;
      if(gutter)document.body.style.paddingRight=(parseFloat(getComputedStyle(document.body).paddingRight)+gutter)+'px';
      fallback.hidden=true;box.append(fallback);
      background=[...document.body.children].filter(item=>item!==overlay&&item!==$('announcement')).map(item=>[item,item.inert]);
      for(const [item] of background)item.inert=true;
      document.documentElement.style.overflow='hidden';overlay.hidden=false;
      for(const disclosure of overlay.querySelectorAll('details'))disclosure.open=false;
      $('entry-context-body').scrollTop=0;
      $('entry-context-title').focus({preventScroll:true});
    };
    const focusable=()=>[...overlay.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),textarea:not(:disabled),select:not(:disabled),summary,[tabindex="0"]')]
      .filter(item=>item.getClientRects().length&&getComputedStyle(item).visibility==='visible'&&!item.closest('[inert]'));
    $('entry-context-close').addEventListener('click',()=>closeEntryContext());
    overlay.addEventListener('pointerdown',event=>{backdropStart=event.target===overlay;});
    overlay.addEventListener('click',event=>{if(event.target===overlay&&backdropStart)closeEntryContext();backdropStart=false;});
    overlay.addEventListener('keydown',event=>{
      if(event.isComposing)return;
      if(event.key==='Escape') {
        event.preventDefault();event.stopPropagation();
        if(!fallback.hidden)$('close-copy').click();else closeEntryContext();
      } else if(event.key==='Tab') {
        const targets=focusable(),first=targets[0],last=targets.at(-1);
        if(!first){event.preventDefault();$('entry-context-title').focus();}
        else if(event.shiftKey&&(document.activeElement===first||!targets.includes(document.activeElement))){event.preventDefault();last.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
      }
    });
    document.addEventListener('focusin',event=>{
      if(!overlay.hidden&&!overlay.contains(event.target))$('entry-context-title').focus({preventScroll:true});
    });
  }
  function renderEntryContext() {
    const subject=entryCard(entrySelected)?subjectMap.get(entrySelected):null;
    if(!subject){closeEntryContext(false);return;}
    $('entry-context-title').textContent=subject.label;
    $('entry-context-note').textContent=subject.summary||nodeMap.get(subject.nodeId).summary;
    $('entry-context-status').replaceChildren(statusBadge(subject));
    if(subject.displayStatus!=='confirmed'&&subject.verificationNote)$('entry-context-status').append(element('p',subject.verificationNote,'entry-note'));
    const owner=nodeMap.get(subject.nodeId),actions=$('entry-context-actions');actions.replaceChildren();
    const control=linkControl('behavior',subject.link);
    control.textContent=subject.link.generated?t('상세 흐름 열기 ↗','Open detailed flow ↗'):t('상세 생성 요청 복사','Copy detail request');
    actions.append(control,entryButton(t('구조에서 확인','View in diagram'),()=>openEntryDiagram(()=>chooseNode(owner,subject))));
    const ownerBox=$('entry-context-owner');ownerBox.replaceChildren(element('h3',t('담당하는 부분','RESPONSIBLE COMPONENT')),element('p',owner.label),element('p',owner.summary,'entry-note'),statusBadge(owner));
    const paths=$('entry-context-paths');paths.replaceChildren(element('h3',t('관련 코드 위치','CODE LOCATIONS')));
    const locations=entryPaths(owner.id);
    const primary=entryLandmark(owner.id)||locations[0],extra=element('details',undefined,'entry-evidence');
    extra.append(element('summary',t('다른 관련 경로 ','More related paths: ')+Math.max(0,locations.length-1)));
    for(const entry of locations) {
      const button=entryButton(undefined,()=>openEntryPath(entry.id),'entry-location');
      button.append(element('code',entry.path),element('small',entry.label),statusBadge(entry));
      if(entry===primary)paths.append(button);else extra.append(button);
    }
    if(locations.length>1)paths.append(extra);
    if(!locations.length)paths.append(element('p',t('폴더 연결이 기록되지 않았습니다. 아래 근거 위치를 확인하세요.','No folder mapping is recorded. Check the evidence locations below.'),'entry-note'));
    const reviewIds=[...new Set([...(subject.evidenceIds||[]),...(owner.evidenceIds||[])])];
    const references=element('details',undefined,'entry-evidence');
    references.append(element('summary',t('소스 근거 확인','Review source evidence')));evidenceSection(references,reviewIds);paths.append(references);
    const connections=$('entry-context-connections');connections.replaceChildren(element('h3',t('연결된 부분','CONNECTED COMPONENTS')));
    const edges=data.edges.filter(edge=>edge.from===owner.id||edge.to===owner.id);
    for(const edge of edges) {
      const peer=nodeMap.get(edge.from===owner.id?edge.to:edge.from);
      const button=entryButton(undefined,()=>openEntryDiagram(()=>chooseNode(peer)),'entry-connection');
      button.append(element('span',nodeMap.get(edge.from).label+' → '+nodeMap.get(edge.to).label),element('small',edge.label),statusBadge(edge));connections.append(button);
    }
    connections.append(element('p',edges.length?
      t('기록된 직접 연결입니다. 변경 영향의 전체 목록은 아닙니다.','Recorded direct relationships, not an exhaustive change-impact analysis.'):
      t('직접 연결이 기록되지 않았습니다. 의존성이 없다는 뜻은 아닙니다.','No direct relationships are recorded; this does not establish that there are no dependencies.'),'entry-note'));
    renderEntryFlow(owner.id);renderCautions(owner.id);
    const tests=reviewIds.filter(id=>evidenceMap.get(id)?.kind==='test');
    const checks=$('entry-context-checks');checks.replaceChildren(element('summary',tests.length?
      t('연결된 테스트 근거 ','Linked test evidence: ')+tests.length:t('테스트 연결 미기록','Test mapping not recorded')));
    if(tests.length) {
      checks.append(element('p',t('검토된 테스트 위치입니다. 테스트 실행 결과를 뜻하지 않습니다.','Reviewed test locations, not test execution results.'),'entry-note'));evidenceSection(checks,tests);
    } else checks.append(element('p',t('연결된 테스트가 기록되지 않았습니다. 변경 전에 별도로 찾아 확인해야 합니다.','No linked tests are recorded. Locate and check them before making a change.'),'entry-note'));
    const scope=$('entry-context-scope');scope.replaceChildren(element('summary',t('설명 범위와 한계','Scope and limits')));
    if(subject.scope) {
      list(scope,t('이 기능의 설명 범위','CAPABILITY SCOPE'),subject.scope.includes);
      list(scope,t('제외한 범위','OUTSIDE THIS SCOPE'),subject.scope.excludes);
    }
    scope.append(element('p',t('상세 문서 미생성은 기능이 없다는 뜻이 아닙니다. 기록된 범위 밖은 별도 분석이 필요합니다.','A missing detail page does not mean the capability is absent. Anything outside the recorded scope needs further analysis.'),'entry-note'));
  }
  function renderEntryFlow(ownerId) {
    // Owner overlap establishes related context, not an exact capability trace.
    const scenarios=data.scenarios.filter(scenario=>scenario.steps.some(step=>step.nodeId===ownerId||
      [edgeMap.get(step.edgeId)?.from,edgeMap.get(step.edgeId)?.to].includes(ownerId)));
    $('entry-flow').hidden=!scenarios.length;$('entry-flow-steps').replaceChildren();
    for(const scenario of scenarios) {
      const section=element('details',undefined,'entry-flow-case');
      section.append(element('summary',scenario.title));
      const steps=element('ol',undefined,'entry-flow-steps');
      for(const step of scenario.steps) {
        const node=nodeMap.get(step.nodeId||edgeMap.get(step.edgeId)?.to);
        const item=element('li',undefined,'entry-flow-step '+step.displayStatus);item.dataset.stepId=step.id;
        item.classList.toggle('nonsequential',nonSequential(step));
        const body=node?entryButton(undefined,()=>openEntryDiagram(()=>chooseNode(node)),'entry-flow-button'):element('div',undefined,'entry-flow-button');
        body.append(element('span',step.caption,'entry-flow-caption'));
        if(step.condition)body.append(element('small',t('이 조건에서: ','When: ')+step.condition));
        if(nonSequential(step)||step.branch&&step.branch!=='normal')body.append(element('small',
          [nonSequential(step)?executionLabels[step.execution]:null,step.branch&&step.branch!=='normal'?branchLabels[step.branch]:null].filter(Boolean).join(' · ')));
        if(node)body.append(element('small',node.label+' ↗','entry-flow-owner'));
        body.append(statusBadge(step));item.append(body);steps.append(item);
      }
      section.append(steps);$('entry-flow-steps').append(section);
    }
  }
  function renderCautions(ownerId) {
    const rules=data.rules.filter(rule=>rule.nodeIds.includes(ownerId));
    $('entry-cautions').hidden=!rules.length;$('entry-cautions-list').replaceChildren();
    for(const rule of rules) {
      const card=element('article',undefined,'entry-caution');card.dataset.ruleId=rule.id;
      card.append(statusBadge(rule),element('h4',rule.plainText));
      const facts=element('dl',undefined,'entry-rule-facts');
      for(const [label,value] of [[t('언제','When'),rule.condition],[t('그러면','Then'),rule.outcome]])if(value)facts.append(element('dt',label),element('dd',value));
      if(rule.evidenceIds.some(id=>evidenceMap.get(id)?.kind==='documentation'))card.append(element('p',
        t('문서에 명시된 규약입니다. 모든 코드의 준수를 보장하지 않습니다.','A documented convention; this does not guarantee compliance throughout the code.'),'entry-meta'));
      const details=element('details',undefined,'entry-evidence');
      details.append(element('summary',t('조건·이유·예외·근거','Conditions, reasons, exceptions and evidence')),facts);
      if(rule.rationale)details.append(element('p',rule.rationale));
      list(details,t('예외','Exceptions'),rule.exceptions||[]);
      details.append(element('p',rule.verificationNote));evidenceSection(details,rule.evidenceIds);
      card.append(details);$('entry-cautions-list').append(card);
    }
  }
  function renderGaps() {
    const body=$('entry-gaps-body');body.replaceChildren();
    for(const [label,items] of [[t('아직 확인하지 못한 것','Unresolved'),data.analysis.unresolved],
      [t('설명의 한계','Limitations'),data.summary.limitations],
      [t('이번 분석에서 제외한 것','Outside this analysis'),data.subject.scope.excludes],
      [t('다음에 확인할 것','Next checks'),data.analysis.nextAttempts]]) {
      const group=element('div');list(group,label,[...new Set(items)]);
      if(group.childElementCount)body.append(group);
    }
    if(!body.childElementCount)body.append(element('p',t('기록된 미확인 항목이 없습니다.','No unresolved items are recorded.')));
  }
  function renderPalette() {
    const overlay=$('entry-palette'),input=$('entry-palette-input'),results=$('entry-palette-results');
    let previousFocus=null,background=[],previousOverflow='';
    const index=[
      ...data.subjects.map(subject=>({kind:t('기능','Capability'),label:subject.label,
        description:subject.summary||nodeMap.get(subject.nodeId).summary,
        search:[subject.question,subject.module,...(subject.targets||[]).flatMap(target=>[target.file,target.symbol,target.label])],
        open:()=>selectEntryFeature(subject.id)})),
      ...data.nodes.filter(node=>!node.contextOnly).map(node=>({kind:t('구성 요소','Component'),label:node.label,
        description:node.summary,search:[node.codeName,node.roleLabel],open:()=>openEntryDiagram(()=>chooseNode(node))})),
      ...(data.structureEntries||[]).map(entry=>({kind:t('경로','Path'),label:entry.path,description:entry.label+' · '+entry.summary,search:[],open:()=>openEntryPath(entry.id)}))
    ].map(item=>({...item,query:[item.label,item.description,...item.search].filter(Boolean).join(' ').toLocaleLowerCase()}));
    closeEntryPalette=(restoreFocus=true)=>{
      if(overlay.hidden)return;
      overlay.hidden=true;
      for(const [item,inert] of background)item.inert=inert;
      background=[];document.documentElement.style.overflow=previousOverflow;
      if(restoreFocus&&previousFocus?.isConnected)previousFocus.focus({preventScroll:true});
    };
    const render=()=>{
      const query=input.value.trim().toLocaleLowerCase(),matches=index.filter(item=>item.query.includes(query));
      results.replaceChildren();
      for(const match of matches) {
        const item=element('li'),button=entryButton(undefined,()=>{closeEntryPalette();match.open();});
        button.append(element('small',match.kind),element('span',match.label),element('small',match.description));
        item.append(button);results.append(item);
      }
      if(!matches.length)results.append(element('li',t('일치하는 항목이 없습니다. 다른 이름이나 경로로 찾아보세요.','No matches. Try another name or path.'),'entry-palette-empty'));
      $('entry-palette-hint').textContent=t('검색 결과 ','Results: ')+matches.length+t('개 · ↑↓ 이동 · Enter 선택 · Esc 닫기',' · ↑↓ navigate · Enter select · Esc close');
    };
    const open=()=>{
      if(view!=='overview'||$('atlas-entry').hidden)return;
      closeEntryContext();
      if(!overlay.hidden){input.focus();input.select();return;}
      previousFocus=document.activeElement;previousOverflow=document.documentElement.style.overflow;
      background=[...document.body.children].filter(item=>item!==overlay).map(item=>[item,item.inert]);
      for(const [item] of background)item.inert=true;
      document.documentElement.style.overflow='hidden';overlay.hidden=false;
      input.value='';render();input.focus();
    };
    $('entry-palette-open').addEventListener('click',open);
    $('entry-palette-close').addEventListener('click',()=>closeEntryPalette());
    overlay.addEventListener('click',event=>{if(event.target===overlay)closeEntryPalette();});
    input.addEventListener('input',render);
    document.addEventListener('keydown',event=>{
      if(event.defaultPrevented||event.isComposing||event.repeat||event.altKey||event.shiftKey)return;
      if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'&&view==='overview'&&!$('atlas-entry').hidden) {
        if(overlay.hidden&&event.target.closest?.('input,textarea,select,[contenteditable]:not([contenteditable="false"])'))return;
        event.preventDefault();open();
      }
    });
    overlay.addEventListener('keydown',event=>{
      if(event.isComposing)return;
      if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeEntryPalette();return;}
      const buttons=[...results.querySelectorAll('button')];
      if(['ArrowDown','ArrowUp'].includes(event.key)&&!event.ctrlKey&&!event.metaKey&&!event.altKey) {
        event.preventDefault();
        const current=buttons.indexOf(document.activeElement),direction=event.key==='ArrowDown'?1:-1;
        const next=current<0?(direction===1?0:buttons.length-1):(current+direction+buttons.length)%buttons.length;
        buttons[next]?.focus();
      } else if(event.key==='Enter'&&event.target===input) {event.preventDefault();buttons[0]?.click();}
      else if(event.key==='Tab') {
        const focusable=[$('entry-palette-close'),input,...buttons],first=focusable[0],last=focusable.at(-1);
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
      }
    });
  }
  function initializeEntry() {
    const texts={
      'entry-route':t('프로젝트 둘러보기','EXPLORE THE PROJECT'),
      'entry-title':t('무엇을 살펴볼까요?','What would you like to explore?'),
      'entry-note':t('같은 목적의 기능을 그룹으로 묶었습니다. 기능 이름을 누르면 요약 팝업이 열립니다.','Capabilities are grouped by responsibility. Select a name to open its summary dialog.'),
      'entry-diagram':t('연결 다이어그램 ↗','Relationship diagram ↗'),
      'entry-palette-open':t('통합 검색 · Ctrl / ⌘ K','Find anything · Ctrl / ⌘ K'),
      'entry-palette-label':t('기능·구성 요소·경로 찾기','Find capabilities, components or paths'),
      'entry-palette-close':t('닫기','Close'),
      'entry-structure-title':t('함께 살펴볼 구성','Other components'),
      'entry-structure-note':t('별도 기능 카드가 연결되지 않은 구성입니다. 역할과 근거를 확인할 수 있습니다.','Components without separate capability cards. Explore their roles and evidence.'),
      'entry-files-title':t('패키지·폴더 펼쳐 보기','Explore packages and folders'),
      'entry-files-note':t('기록된 실제 경로입니다. 들여쓰기는 포함 관계이며 호출·의존 관계가 아닙니다.','Recorded paths. Indentation means containment, not calls or dependencies.'),
      'entry-search-label':t('기능 필터','Filter capabilities'),
      'entry-group-label':t('담당 구역','Responsibility'),
      'entry-availability-label':t('상세 문서','Detail pages'),
      'entry-reset':t('초기화','Reset'),
      'entry-context-kicker':t('기능 요약','CAPABILITY SUMMARY'),
      'entry-context-close':t('닫기 ×','Close ×'),
      'entry-flow-title':t('담당 구성의 관련 흐름','RELATED COMPONENT FLOWS'),
      'entry-flow-note':t('같은 담당 구성을 포함하는 설명입니다. 이 기능만의 흐름을 보장하지 않습니다. 번호는 설명 순서이며 실제 실행 기록이 아닙니다.','These explanations share the owner component, not necessarily this exact capability scope. Numbers indicate explanation order, not an execution trace.'),
      'entry-cautions-title':t('담당 구성에서 지킬 규칙','COMPONENT CAUTIONS'),
      'entry-cautions-note':t('담당 구성에 연결된 규칙입니다. 조건과 적용 범위를 함께 확인하세요.','Rules linked to the owner component. Check their conditions and scope.'),
      'entry-gaps-title':t('분석 범위와 아직 모르는 것','Analysis scope and open questions'),
      'entry-gaps-note':t('기록된 항목의 확인 비율은 전체 프로젝트의 분석률이 아닙니다. 목록이 비어 있어도 전체 검증을 뜻하지 않습니다.','The recorded-item review ratio is not whole-project coverage. An empty list does not establish exhaustive validation.'),
      'entry-home':t('← 프로젝트 입구','← Project overview')
    };
    for(const [id,value] of Object.entries(texts))$(id).textContent=value;
    $('entry-search').placeholder=t('기능 이름이나 코드 경로','Capability name or code path');
    initializeEntryContext();
    renderEntrySummary();renderGaps();renderPalette();
    $('entry-home').hidden=false;
    $('entry-home').addEventListener('click',()=>{
      stop();closePanel(false);history.length=0;view='overview';selected=null;focusId=null;regionId=null;
      applyAtlasView();renderEntryFilters();syncLocation();$('entry-title').focus();$('entry-title').scrollIntoView({block:'start'});
    });
    $('entry-diagram').addEventListener('click',()=>openEntryDiagram());
    for(const [id,values] of [
      ['entry-group',[['',t('모든 구역','All responsibilities')],...data.regions.map(r=>[r.id,r.label])]],
      ['entry-availability',[['',t('모든 상태','Any availability')],['ready',t('준비됨','Available')],['missing',t('미생성','Not generated')]]]
    ])for(const [value,label] of values){const option=element('option',label);option.value=value;$(id).append(option);}
    const filter=()=>{entryQuery=$('entry-search').value;entryGroup=$('entry-group').value;entryAvailability=$('entry-availability').value;renderEntryFilters();syncLocation();};
    $('entry-search').addEventListener('input',filter);
    $('entry-group').addEventListener('change',filter);$('entry-availability').addEventListener('change',filter);
    $('entry-reset').addEventListener('click',()=>{entryQuery='';entryGroup='';entryAvailability='';entrySelected=null;renderEntryFilters();syncLocation();});
    const owners=new Set(data.subjects.map(subject=>subject.nodeId));
    const groups=data.nodes.filter(node=>!node.contextOnly&&!owners.has(node.id));
    $('entry-support').hidden=!groups.length;
    for(const group of groups) {
      const card=element('article',undefined,'entry-card role-card');
      card.append(statusBadge(group),element('h3',group.label),element('p',group.summary));
      const members=(group.nodeIds||[group.id]).map(id=>nodeMap.get(id));
      const chips=element('div',undefined,'entry-parts');
      for(const member of members)chips.append(element('span',member.label));
      card.append(chips,entryButton(t('관계도 펼쳐 보기 →','Explore relationships →'),()=>openEntryDiagram(()=>{
        if(regionMap.has(group.id))enterRegion(group.id);else chooseNode(group);
      })));$('entry-roles').append(card);
    }
    // The IR accepts language tags that a browser's Intl may reject. Sorting
    // must not stop initialization or change the recorded explanation language.
    let comparePaths=(left,right)=>left<right?-1:left>right?1:0;
    try{comparePaths=new Intl.Collator(data.language).compare;}catch{/* Use deterministic string order. */}
    const entries=[...(data.structureEntries||[])].sort((a,b)=>comparePaths(a.path,b.path));
    if(!entries.length)$('entry-files').append(element('p',t('이 JSON에는 패키지·폴더 구조가 기록되지 않았습니다. 기존 관계도는 계속 사용할 수 있습니다. 구조를 추가하려면 원본 경로와 근거를 검토해 JSON을 갱신해 주세요.','This JSON has no package/folder entries. The existing diagram is still available. Review the source paths and evidence before adding structure entries.'),'entry-empty'));
    const tree=element('div',undefined,'entry-tree');$('entry-files').append(tree);
    const containers=new Map();
    const pathDepth=path=>path==='.'?0:path.split('/').length;
    // Root depth is zero, even beside one-character folders. Attach recorded
    // ancestors first; never invent entries for omitted intermediate folders.
    for(const entry of [...entries].sort((a,b)=>pathDepth(a.path)-pathDepth(b.path))) {
      const ancestors=entries.filter(e=>e!==entry&&e.kind!=='file'&&(e.path==='.'||entry.path.startsWith(e.path+'/')));
      const parent=ancestors.sort((a,b)=>pathDepth(b.path)-pathDepth(a.path))[0];
      const details=element('details',undefined,'entry-tree-item');details.dataset.structureId=entry.id;
      const title=element('summary');
      const kind={package:t('패키지','Package'),directory:t('폴더','Folder'),file:t('파일','File')}[entry.kind];
      title.append(element('span',kind,'entry-kind'),element('code',entry.path),element('span',entry.label),statusBadge(entry));
      details.append(title);
      const body=element('div',undefined,'entry-tree-body');body.append(element('p',entry.summary));
      const actions=element('div',undefined,'entry-actions');
      for(const id of entry.nodeIds)actions.append(entryButton(nodeMap.get(id).label+' ↗',()=>openEntryDiagram(()=>chooseNode(nodeMap.get(id)))));
      const capabilities=data.subjects.filter(s=>entry.nodeIds.includes(s.nodeId));
      for(const subject of capabilities)actions.append(entryButton(t('기능: ','Capability: ')+subject.label,()=>selectEntryFeature(subject.id)));
      body.append(actions,entryEvidence(entry));details.append(body);
      (containers.get(parent?.id)||tree).append(details);containers.set(entry.id,body);
    }
    renderEntryFilters();
  }
  function keyboardNavigation(event) {
    if(isAtlas&&view==='overview')return;
    if(event.defaultPrevented||event.isComposing||event.ctrlKey||event.metaKey||event.altKey||data.analysis.status==='insufficient')return;
    const target=event.target;
    if(!target.closest?.('#workspace')||target.closest('input,textarea,select,[contenteditable]:not([contenteditable="false"]),#panel'))return;
    if(view==='flow'&&data.scenarios.length&&['[',']','p','P'].includes(event.key)) {
      event.preventDefault();
      if(event.key.toLowerCase()==='p'){if(!event.repeat)togglePlayback();}
      else{stop();setStep(stepIndex+(event.key==='['?-1:1));}
      return;
    }
    if(target===$('canvas')) {
      if(event.key===' '&&view==='flow') {event.preventDefault();if(!event.repeat)togglePlayback();return;}
      if(event.key==='Enter') {
        const nodes=[...document.querySelectorAll('.node')];
        const node=nodes.find(n=>n.dataset.id===selected)||nodes[0];
        if(node){event.preventDefault();stop();node.focus({preventScroll:true});revealNode(node.dataset.id,true);}
      }
      return;
    }
    const current=target.closest('.node');
    if(!current||!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key))return;
    event.preventDefault();stop();
    const nodes=[...document.querySelectorAll('.node')];
    let next;
    if(event.key==='Home')next=nodes[0];
    else if(event.key==='End')next=nodes.at(-1);
    else {
      const horizontal=['ArrowLeft','ArrowRight'].includes(event.key),sign=['ArrowLeft','ArrowUp'].includes(event.key)?-1:1;
      const x=current.offsetLeft+current.offsetWidth/2,y=current.offsetTop+current.offsetHeight/2;
      next=nodes.filter(n=>n!==current).map(n=>{
        const dx=n.offsetLeft+n.offsetWidth/2-x,dy=n.offsetTop+n.offsetHeight/2-y;
        return {node:n,forward:sign*(horizontal?dx:dy),side:Math.abs(horizontal?dy:dx)};
      }).filter(n=>n.forward>1).sort((a,b)=>(a.forward+a.side*2)-(b.forward+b.side*2))[0]?.node;
    }
    if(next){next.focus({preventScroll:true});revealNode(next.dataset.id,true);}
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
    $('summary-details-title').parentElement.hidden=!data.summary.inputs.length&&!data.summary.outputs.length;
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
    $('playback-progress').setAttribute('aria-label',t('설명 재생 진행','Walkthrough progress'));
    $('scenario').setAttribute('aria-label',t('설명 흐름','Walkthrough'));
    $('step-picker-label').textContent=t('단계 선택','Jump to step');
    $('speed-label').textContent=t('설명 속도','Playback speed');
    $('copy-position').textContent=t('현재 위치 링크 복사','Copy link to this view');
    const copyPosition=()=>{stop();const url=new URL(location.href);url.hash=locationHash();copy(url.href);};
    $('copy-position').addEventListener('click',copyPosition);
    $('copy-inspection').textContent=t('링크','Link');
    $('copy-inspection').setAttribute('aria-label',t('이 설명 링크 복사','Copy link to this explanation'));
    $('copy-inspection').addEventListener('click',copyPosition);
    $('keyboard-help-title').textContent=t('키보드 안내','Keyboard help');
    $('keyboard-help-text').textContent=t('그림에서 Enter로 구성 요소 탐색을 시작합니다. 노드의 방향키로 옆 부분을 찾고 Enter로 설명을 엽니다. 빈 그림 영역에서는 방향키로 지도를 이동하고 + / −로 확대·축소합니다. 흐름 보기에서 [ / ]는 이전·다음 단계, P는 재생·정지입니다. 검색창과 선택 목록에서는 원래 키 동작을 유지합니다.',
      'Enter on the map starts component navigation. Arrow keys on a node focus nearby parts; Enter opens the explanation. Arrow keys on the empty map pan; + / − zoom. In walkthrough view, [ / ] move between steps and P plays or pauses. Search and selection controls keep their native keys.');
    $('copy-label').textContent=t('텍스트를 선택해 복사해 주세요.','Select this text to copy it.');
    $('close-copy').textContent=t('닫기','Close');
    $('close-copy').addEventListener('click',()=>{$('copy-fallback').hidden=true;(copyReturnFocus?.isConnected?copyReturnFocus:$('copy-position')).focus({preventScroll:true});});
    $('step-picker').addEventListener('change',()=>{stop();setStep(Number($('step-picker').value));});
    $('playback-speed').addEventListener('change',changeSpeed);
    $('panel-size').addEventListener('click',()=>{
      stop();document.body.classList.toggle('panel-expanded');positionPanel();
      if(selectedNodeId())revealNode(selectedNodeId(),true);
      else if(edgeMap.has(selected))revealConnection(edgeMap.get(selected),true);
    });
    $('back').textContent=t('← 돌아가기','← Back');
    $('zoom-out').setAttribute('aria-label',t('축소','Zoom out'));
    $('zoom-in').setAttribute('aria-label',t('확대','Zoom in'));
    $('fit').textContent=t('전체','Fit');
    $('fit').setAttribute('aria-label',t('지도를 화면에 맞추기','Fit map to view'));
    $('canvas').setAttribute('aria-label',t('관계도. Enter로 구성 요소 탐색, 방향키로 이동, +와 -로 확대 축소, 0으로 전체 보기',
      'Relationship map. Enter to explore components, arrow keys to move, + and - to zoom, 0 to fit.'));
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
      if(isAtlas) {
        for(const subject of data.subjects.filter(s=>[s.label,s.summary,s.question,...(s.targets||[]).map(t=>t.symbol)].some(v=>v?.toLocaleLowerCase().includes(query))))$('results').append(capabilityButton(subject));
        for(const region of data.regions.filter(r=>[r.label,r.summary].some(v=>v.toLocaleLowerCase().includes(query)))){const button=element('button',region.label+' · '+t('구역','region'));button.type='button';button.addEventListener('click',()=>enterRegion(region.id));$('results').append(button);}
      }
      if(!$('results').childElementCount)$('results').append(element('p',t('일치하는 구성 요소가 없습니다.','No matching components.')));
    });
    data.scenarios.forEach((scenario,index)=>{
      const button=element('button',scenario.title);button.type='button';button.dataset.index=index;
      button.append(element('small',scenario.steps.length+t('개 설명 단계',' explanation steps')));
      button.addEventListener('click',()=>{scenarioIndex=index;$('scenario').value=String(index);setView('flow');setStep(0);});
      $('flows').append(button);
    });
    $('structure').addEventListener('click',()=>setView('structure'));
    $('workflow').addEventListener('click',()=>setView('flow'));
    $('overview').addEventListener('click',()=>{history.length=0;focusId=null;selected=null;closePanel();regionId=null;draw();setView('structure');fit();});
    $('focus-related').addEventListener('click',()=>{
      if(!nodeMap.has(selected))return;
      if(focusId===selected){focusId=null;updateNavigation();paint();return;}
      stop();
      rememberView();
      focusId=selected;closePanel();revealNode(focusId);updateNavigation();paint();
    });
    $('back').addEventListener('click',()=>{
      const saved=history.pop();if(!saved)return;stop();closePanel();
      ({focusId,selected,zoom,detail,view,scenarioIndex,stepIndex,regionId}=saved);
      $('mode').value=detail?'detail':'core';$('scenario').value=String(scenarioIndex);draw();
      if(stepIndex>=0){const selection=selected;setStep(stepIndex,true);selected=selection;}
      setView(view);$('canvas').scrollLeft=saved.left;$('canvas').scrollTop=saved.top;
      if(itemMap.has(selected))showItem(itemMap.get(selected));
      updateMini();paint();
    });
    $('zoom-in').addEventListener('click',()=>setZoom(zoom*1.2));
    $('zoom-out').addEventListener('click',()=>setZoom(zoom/1.2));
    $('fit').addEventListener('click',()=>fit());
    $('canvas').addEventListener('scroll',updateMini,{passive:true});
    let drag=null;
    $('canvas').addEventListener('pointerdown',event=>{
      if(event.button!==0||event.target.closest('button,.edge'))return;
      stop();
      if(event.pointerType==='touch')return;
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
      if(event.target!==$('canvas')||event.defaultPrevented||event.isComposing||event.ctrlKey||event.metaKey||event.altKey)return;
      if(['+','=','-','0','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))event.preventDefault();
      if(event.key.startsWith('Arrow'))stop();
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
    if(isAtlas)document.body.classList.add('atlas-page');
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
    if(!isAtlas)for(const subject of data.subjects) $('regions').append(linkControl('behavior',subject.link,subject.label));
    $('rules-section').hidden=!data.rules.length;$('rules-title').textContent=t('어떤 규칙을 따르나요?','What rules apply?');
    for(const rule of data.rules) {
      const box=element('article',undefined,'rule-card');
      box.append(statusBadge(rule),element('p',rule.plainText),element('small',rule.condition+' → '+rule.outcome));
      const button=element('button',t('근거 확인','View evidence'));button.type='button';button.addEventListener('click',()=>showItem(rule,true));box.append(button);$('rules-list').append(box);
    }
    $('scope-title').textContent=t('설명 범위와 한계','Scope and limitations');
    const scope=element('div',undefined,'scope-body-grid');
    const included=element('div');list(included,t('포함한 범위','Included'),data.subject.scope.includes);list(included,t('제외한 범위','Excluded'),data.subject.scope.excludes);
    const limitations=element('div'),scopeSeen=new Set();list(limitations,t('확인하지 못한 내용','Unresolved'),data.analysis.unresolved,scopeSeen);list(limitations,t('탐색한 위치','Searched'),data.analysis.searched,scopeSeen);list(limitations,t('한계','Limitations'),data.summary.limitations,scopeSeen);list(limitations,t('다음 시도','Next attempts'),data.analysis.nextAttempts,scopeSeen);
    scope.append(included,limitations);$('scope-body').append(scope);
    if(isAtlas) {
      // Header metadata is hidden on narrow screens; keep an accessible copy
      // in the scope disclosure without calling a captured snapshot "current".
      list($('scope-body'),t('분석 기준 · 현재 소스와 다를 수 있음','Analysis snapshot · may differ from current source'),
        [$('snapshot').textContent]);
    }
    $('offline-note').textContent=t('오프라인 설명서 · 하위 페이지를 만든 뒤 상위 페이지를 새로 생성하면 링크가 갱신됩니다.','Offline explanation · regenerate the parent page after creating a child to update its links.');
    if(data.analysis.status==='insufficient') {
      $('workspace').hidden=true;$('insufficient').hidden=false;
      $('insufficient').append(element('h2',t('아직 설명할 근거가 충분하지 않습니다.','There is not enough evidence yet.')));
      list($('insufficient'),t('확인하지 못한 이유','Why'),data.analysis.unresolved);
      list($('insufficient'),t('살펴본 범위','Searched'),data.analysis.searched);
      list($('insufficient'),t('다음에 시도할 것','Next attempts'),data.analysis.nextAttempts);
    } else if(!isAtlas) {
      // Atlas layout is deferred until the reader opens a diagram (or restores
      // a diagram deep link). The entry does not need a hidden graph layout.
      draw();
      if(data.scenarios.length) setStep(0);
      selected=null;
      closePanel();
      paint();
    }
    let resizeTimer;
    addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{
      if(data.analysis.status!=='insufficient'&&view!=='overview') {
        finishCamera();
        draw();
        positionPanel();
        if(isPlaying())revealStep(false);
        else if($('panel').classList.contains('open') && selectedNodeId())revealNode(selectedNodeId());
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
    addEventListener('wheel',()=>{if(cameraMotion || isPlaying())stop();},{passive:true});
    reducedMotion.addEventListener('change',()=>{if(reducedMotion.matches)finishCamera(true);paint();});
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'&&!$('copy-fallback').hidden){$('close-copy').click();return;}
      if(event.key==='Escape'&&$('panel').classList.contains('open'))closePanel();
      else keyboardNavigation(event);
    });
    initializeCanvas();
    initializeAtlas();
    // Do not serialize intermediate initialization states over a supplied link.
    navigationReady=true;
    if(location.hash.startsWith('#s2s='))restoreLocation(location.hash);
    else if(isAtlas) {
      if(location.hash&&location.hash!=='#'){view='overview';applyAtlasView();}
      else restoreLocation('');
    }
    addEventListener('hashchange',()=>restoreLocation(location.hash));
    const notice=$('navigation-notice');$('workspace').before(notice);
    document.documentElement.dataset.ready='true';
  }
  initialize();
})();
