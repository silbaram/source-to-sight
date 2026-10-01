'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.argv[3]||'playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.S2S_CHROMIUM_EXECUTABLE?{executablePath:process.env.S2S_CHROMIUM_EXECUTABLE}:{})});let checks=0;
 try{for(const language of ['ko','en'])for(const width of [1440,390])for(const dark of [false,true]){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'}),page=await context.newPage(),errors=[],network=[];
  page.on('pageerror',error=>errors.push(error.message));page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url())});
  const ready=()=>page.waitForSelector('html[data-ready=true]');
  await page.goto(pathToFileURL(path.resolve(process.argv[2],language,'features/project.html')).href);await ready();
  if(dark)await page.locator('#theme-toggle').click();
  const data=await page.locator('#s2s-data').evaluate(node=>JSON.parse(node.textContent));
  assert.equal(await page.locator('.project-composition').count(),1);
  assert.equal(await page.locator('.feature-overview').count(),3,'Each actual capability has its own group');
  assert.equal(await page.locator('.atlas-area-open:visible').count(),0,'No area selection is required to read a feature flow');
  const feature=page.locator('.feature-overview').first(),child=data.featureDetails[0];
  assert(!(await feature.innerText()).includes('SECOND ONLY'),'Shared ownership does not blend two capability traces');
  assert((await page.locator('#feature-cap-second').innerText()).includes('SECOND ONLY'));
  for(const value of [...child.summary.inputs,...child.summary.outputs])assert((await feature.locator('.feature-request').innerText()).includes(value));
  assert((await feature.locator('.feature-request').boundingBox()).y<(await feature.locator('.feature-step').first().boundingBox()).y);
  assert.equal(await feature.locator('.feature-step').count(),2);
  assert(child.nodes.length>await feature.locator('.feature-step').count(),'Overview combines internal steps into responsibilities');
  assert(!(await feature.innerText()).includes('DETAILED RECEIVE'),'Internal processing stays in the detail page');
  assert.equal(await page.locator('.feature-overview select').count(),0,'Scenario controls belong to detail');
  const ids=await feature.locator('[data-edge-id]').evaluateAll(nodes=>nodes.map(node=>node.dataset.edgeId));
  assert(ids.every(id=>child.edges.some(edge=>edge.id===id)),'Arrows use only the exact child graph');
  assert((await page.locator('#feature-cap-second .feature-relations').innerText()).includes(language==='ko'?'병렬':'Parallel'));
  assert.equal(await page.locator('#feature-cap-second .feature-connector').count(),0,'Parallel transfers are not serialized by card order');
  assert.equal(await feature.locator('a.feature-open').count(),0,'Grouped features have no duplicate whole-path action');
  assert.equal(await feature.locator('.feature-overview-footer').count(),0,'No empty footer remains');
  await feature.locator('.feature-step[data-group-id="group-request"]').click();
  await page.waitForURL(url=>url.pathname.endsWith('/features/behavior.html'));await ready();
  assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('view'),'structure');
  assert.equal(await page.locator('.map-region.selected').getAttribute('data-id'),'group-request');
  assert.equal(await page.locator('.map-region.selected button').getAttribute('aria-pressed'),'true');
  assert(await page.evaluate(()=>{
    const header=document.querySelector('.diagram-header'),wrap=document.querySelector('.canvas-wrap');
    const controls=document.getElementById('process-context'),canvas=document.getElementById('canvas');
    const hs=getComputedStyle(header),ws=getComputedStyle(wrap);
    return header.contains(controls)&&hs.backgroundColor!==ws.backgroundColor&&
      parseFloat(hs.borderBottomWidth)>=1&&hs.borderBottomStyle==='solid'&&
      wrap.getBoundingClientRect().top-header.getBoundingClientRect().bottom>=12&&
      canvas.getBoundingClientRect().top>=controls.getBoundingClientRect().bottom;
  }),'Controls have their own surface, divider and space before the graph viewport');
  assert.notEqual(await page.locator('.map-region.selected').evaluate(n=>getComputedStyle(n).boxShadow),'none');
  assert(await page.evaluate(()=>{
    const group=document.querySelector('.map-region.selected .map-region-label').getBoundingClientRect();
    const first=document.querySelector('.node.group-member').getBoundingClientRect();
    const canvas=document.getElementById('canvas').getBoundingClientRect();
    const panel=document.getElementById('panel').getBoundingClientRect();
    const scale=new DOMMatrix(getComputedStyle(document.getElementById('stage')).transform).a;
    return scale>=.85&&[group,first].every(box=>box.left>=canvas.left&&box.right<=canvas.right&&
      box.top>=Math.max(0,canvas.top)&&box.bottom<=Math.min(innerHeight,canvas.bottom)&&
      (innerWidth>900?box.right<=panel.left:box.bottom<=panel.top));
  }),'Selected responsibilities start with readable headings and cards clear of the inspector');
  await page.locator('#show-connections').click();
  assert(await page.evaluate(()=>{
    const group=document.querySelector('.map-region.selected').getBoundingClientRect();
    const canvas=document.getElementById('canvas').getBoundingClientRect();
    const panel=document.getElementById('panel').getBoundingClientRect();
    return group.left>=canvas.left&&group.right<=canvas.right&&group.top>=Math.max(0,canvas.top)&&
      group.bottom<=Math.min(innerHeight,canvas.bottom)&&
      (innerWidth>900?group.right<=panel.left:group.bottom<=panel.top);
  }),'Optional connections can still frame the whole selected responsibility');
  await page.locator('#show-connections').click();
  assert(await page.locator('.node.group-member').evaluateAll(nodes=>nodes.every(node=>{
    const box=node.getBoundingClientRect(),hit=document.elementFromPoint(box.x+box.width/2,box.y+box.height/2);
    return hit?.closest('.node')===node;
  })),'Raised group backgrounds must not cover their processing nodes');
  await page.reload();await ready();
  assert.equal(await page.locator('.map-region.selected').getAttribute('data-id'),'group-request','Group emphasis survives reload');
  if(language==='ko'){
    await page.screenshot({path:path.resolve(process.argv[2],'selected-group-'+width+'-'+(dark?'dark':'light')+'.png')});
  }
  await page.locator('#process-groups button[data-process-group="group-decision"]').click();
  assert.equal(await page.locator('.map-region.selected').getAttribute('data-id'),'group-decision','Selecting another group transfers emphasis');
  assert.equal(await page.locator('.map-region.selected').count(),1);
  await page.locator('#close-panel').click();
  const typical=child.scenarios.find(s=>s.kind==='typical')||child.scenarios[0];
  await page.locator('#workflow').click();
  assert.equal(await page.locator('#panel.open').count(),0,'Following a path does not automatically cover the diagram');
  assert.equal(await page.locator('.map-region.selected').count(),0,'Path following clears group inspection emphasis');
  assert.equal(await page.locator('#process-groups button').count(),2);
  assert.equal(await page.locator('#region-layer .map-region').count(),2,'Summary groups enclose detailed nodes');
  const boxes=await page.evaluate(()=>[...document.querySelectorAll('#region-layer .map-region')].map(group=>{
    const data=JSON.parse(document.getElementById('s2s-data').textContent);
    const region=data.regions.find(r=>r.id===group.dataset.id),rect=group.getBoundingClientRect();
    return {label:group.querySelector('button').textContent,contained:region.nodeIds.every(id=>{
      const node=[...document.querySelectorAll('.node')].find(n=>n.dataset.id===id);
      const box=node.getBoundingClientRect();
      return box.left>=rect.left&&box.right<=rect.right&&box.top>=group.querySelector('.map-region-label').getBoundingClientRect().bottom&&box.bottom<=rect.bottom;
    })};
  }));
  assert(boxes.every(box=>box.contained),'Group boxes must contain their members with room for headings');
  assert(await page.locator('#process-current').isVisible());
  assert(await page.evaluate(()=>{
    const canvas=document.getElementById('canvas').getBoundingClientRect();
    return [...document.querySelectorAll('.map-region.path-active .map-region-label')].every(label=>{
      const box=label.getBoundingClientRect();
      return box.left>=canvas.left&&box.right<=canvas.right&&box.top>=canvas.top&&box.bottom<=canvas.bottom;
    });
  }),'Active responsibility headings stay inside the diagram viewport');
  assert((await page.locator('#process-current').innerText()).includes(typical.steps[0].caption));
  if(language==='ko'&&!dark){
    await page.locator('#process-context').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.resolve(process.argv[2],'process-context-'+width+'.png')});
  }
  const positions=await page.locator('.node').evaluateAll(nodes=>nodes.map(n=>[n.dataset.id,n.style.left,n.style.top]));
  await page.locator('#structure').click();
  assert.equal(await page.locator('#process-current').isVisible(),false);
  assert.equal(await page.locator('#canvas.process-board').count(),1,'Structure uses readable operation cards');
  assert.equal(await page.locator('#connections').isVisible(),false,'Structure hides connections until requested');
  await page.locator('#workflow').click();
  assert.deepEqual(await page.locator('.node').evaluateAll(nodes=>nodes.map(n=>[n.dataset.id,n.style.left,n.style.top])),positions,'Returning to the path restores its connection layout');
  await page.locator('#mode').selectOption('detail');
  assert.equal(await page.locator('#mode').inputValue(),'detail','Detail entry includes every recorded node');
  assert.equal(await page.locator('#mode option:checked').innerText(),language==='ko'?'전체 처리':'All processing');
  assert.equal(await page.locator('.node').count(),child.nodes.length);
  await page.locator('#structure').click();
  await page.locator('#mode').selectOption('core');
  assert.equal(await page.locator('.node').count(),child.nodes.filter(node=>node.importance==='core').length);
  await page.locator('#mode').selectOption('detail');
  assert.equal(await page.locator('.node').count(),child.nodes.length);
  await page.locator('#links a[href*="project.html"]').click();await page.waitForURL(url=>url.pathname.endsWith('/features/project.html'));await ready();
  await page.locator('.feature-jumps a').first().click();
  assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('feature'),child.subject.id);
  await page.waitForFunction(()=>document.activeElement?.matches('.feature-heading.is-selected'));
  const box=feature.locator('.feature-step[data-group-id="group-request"]');await box.focus();
  await Promise.all([page.waitForURL(url=>url.pathname.endsWith('/features/behavior.html')),page.keyboard.press('Enter')]);await ready();
  assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('item'),'group-request');
  assert.equal(await page.locator('.region-process').count(),2);
  assert((await page.locator('.region-processes').innerText()).includes('DETAILED RECEIVE'));
  assert.equal(await page.locator('.node.group-member').count(),2);
  await page.locator('.region-process[data-node-id="node-caller"]').click();
  assert.equal(await page.locator('.node.selected').getAttribute('data-id'),'node-caller');
  assert.equal(await page.locator('.map-region.selected').getAttribute('data-id'),'group-request','Inspecting a member retains its group emphasis');
  const surfaces=await page.evaluate(()=>{
    const style=selector=>getComputedStyle(document.querySelector(selector));
    const group=style('.map-region.selected'),card=style('.node.group-member:not(.selected)');
    const selected=style('.node.selected');
    const luminance=color=>{
      const channels=color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{
        v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;
      });
      return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;
    };
    const contrast=(a,b)=>{
      const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
    };
    return {
      group:group.backgroundColor,card:card.backgroundColor,selected:selected.backgroundColor,
      borderContrast:Math.min(contrast(card.borderTopColor,group.backgroundColor),contrast(card.borderTopColor,card.backgroundColor)),
      selectionContrast:Math.min(contrast(selected.borderTopColor,group.backgroundColor),contrast(selected.borderTopColor,selected.backgroundColor)),
      textContrast:Math.min(contrast(card.color,card.backgroundColor),contrast(selected.color,selected.backgroundColor)),
      ring:selected.boxShadow
    };
  });
  assert.notEqual(surfaces.group,surfaces.card,'Containment and processing cards use separate neutral surfaces');
  assert.notEqual(surfaces.card,surfaces.selected,'Only the inspected card receives a selected surface');
  assert(surfaces.borderContrast>=3,'Card boundaries contrast with both adjacent surfaces');
  assert(surfaces.selectionContrast>=3,'Selection boundary has at least 3:1 contrast');
  assert(surfaces.textContrast>=4.5,'Card text has at least 4.5:1 contrast');
  assert.notEqual(surfaces.ring,'none');
  assert.equal(await page.locator('.node.selected').getAttribute('aria-pressed'),'true');
  if(language==='ko')await page.screenshot({path:path.resolve(process.argv[2],'selected-node-'+width+'-'+(dark?'dark':'light')+'.png')});
  await page.locator('#close-panel').click();
  await page.locator('.node[data-id="node-main"]').click();
  assert.equal(await page.locator('.node.selected').getAttribute('data-id'),'node-main');
  assert(await page.locator('#panel').evaluate(node=>node.classList.contains('open')));
  await page.locator('.node-rules a').click();await ready();
  assert.equal(new URL(page.url()).searchParams.get('s2s-node'),'node-main');
  await page.locator('.primer-intro > .links a[data-layer="atlas"]').click();await ready();
  assert.equal(await page.locator('.feature-heading.is-selected').getAttribute('data-feature-id'),child.subject.id);
  assert(await page.locator('.feature-heading.is-selected').evaluate(node=>node===document.activeElement));
  assert.equal(await page.locator('#feature-cap-missing .feature-step').count(),0);
  await page.locator('#feature-cap-missing button.feature-open').click();assert(await page.locator('#entry-context').isVisible());await page.keyboard.press('Escape');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.goto(pathToFileURL(path.resolve(process.argv[2],language,'features/no-summary.html')).href);await ready();
  assert.equal(await page.locator('.feature-step').count(),0,'Missing reviewed summaries do not become detailed-node copies');
  assert.equal(await page.locator('.feature-request').count(),2,'Known inputs/results remain available');
  assert.equal(await page.locator('.feature-overview a.feature-open').count(),2,'Checked detail pages remain accessible');
  await page.goto(pathToFileURL(path.resolve(process.argv[2],language,'features/path-cases.html')).href);await ready();
  const cases=await page.locator('#s2s-data').evaluate(node=>JSON.parse(node.textContent));
  const errorIndex=cases.scenarios.findIndex(s=>s.kind==='error');
  await page.locator('#process-path').selectOption(String(errorIndex));
  assert.equal(await page.locator('#workflow').getAttribute('aria-pressed'),'true');
  assert((await page.locator('#process-current').innerText()).includes('SYNTHETIC INVALID INPUT'));
  assert((await page.locator('#process-current').innerText()).includes(cases.nodes.find(n=>n.id===cases.edges[0].from).label));
  assert((await page.locator('#process-path option:checked').innerText()).startsWith(language==='ko'?'오류 경로':'Error path'));
  assert((await page.locator('#flows').textContent()).includes('SYNTHETIC INVALID INPUT'));
  await page.reload();await ready();
  assert.equal(await page.locator('#process-path').inputValue(),String(errorIndex),'Selected error path survives reload');
  await page.locator('#process-groups button').first().click();
  assert.equal(await page.locator('#structure').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('.region-process').count(),2);
  await page.locator('#close-panel').click();
  await page.locator('#workflow').click();
  assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('edge'),cases.scenarios[errorIndex].steps[0].edgeId,'Returning to the path restores its active connection');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.goto(pathToFileURL(path.resolve(process.argv[2],language,'features/no-path.html')).href);await ready();
  assert.equal(await page.locator('#process-path-control').isVisible(),false);
  assert.equal(await page.locator('#workflow').isVisible(),false);
  await page.locator('#mode').selectOption('detail');
  assert.equal(await page.locator('.map-region').count(),2);
  const resize=page.locator('#canvas-resize');
  const height=()=>page.locator('#canvas').evaluate(n=>n.clientHeight);
  const camera=()=>page.evaluate(()=>{
    const canvas=document.getElementById('canvas'),stage=document.getElementById('stage');
    const scale=new DOMMatrix(getComputedStyle(stage).transform).a;
    return {x:(canvas.scrollLeft+canvas.clientWidth/2-stage.offsetLeft)/scale,
      y:(canvas.scrollTop+canvas.clientHeight/2-stage.offsetTop)/scale,scale};
  });
  const defaultHeight=await height();
  await resize.scrollIntoViewIfNeeded();
  const originalCamera=await camera();
  const originalPositions=await page.locator('.node').evaluateAll(nodes=>nodes.map(n=>[n.dataset.id,n.style.left,n.style.top]));
  const grip=await resize.boundingBox();
  await page.mouse.move(grip.x+grip.width/2,grip.y+grip.height/2);
  await page.mouse.down();await page.mouse.move(grip.x+grip.width/2,grip.y+grip.height/2+90,{steps:6});await page.mouse.up();
  assert(Math.abs(await height()-defaultHeight-90)<=2,'Dragging the grip changes only viewport height');
  const resizedCamera=await camera();
  assert.equal(resizedCamera.scale,originalCamera.scale,'Resize keeps the zoom level');
  assert(Math.abs(resizedCamera.x-originalCamera.x)<3&&Math.abs(resizedCamera.y-originalCamera.y)<3,'Resize keeps the graph point at the viewport center: '+JSON.stringify({originalCamera,resizedCamera}));
  assert.deepEqual(await page.locator('.node').evaluateAll(nodes=>nodes.map(n=>[n.dataset.id,n.style.left,n.style.top])),originalPositions,'Height changes do not rearrange nodes');
  const draggedHeight=await height();
  await resize.press('ArrowUp');assert.equal(await height(),draggedHeight-40);
  assert.equal(Number(await resize.getAttribute('aria-valuenow')),await height());
  const savedHeight=await height();await page.reload();await ready();
  assert.equal(await height(),savedHeight,'Reader height preference survives reload');
  await resize.press('Home');assert.equal(await height(),320);
  await resize.press('ArrowUp');assert.equal(await height(),320,'Minimum height is enforced');
  await resize.press('End');assert.equal(await height(),1600);
  await resize.press('ArrowDown');assert.equal(await height(),1600,'Maximum height is enforced');
  await resize.press('Home');await resize.press('Shift+ArrowDown');
  assert.equal(await height(),420,'Shift uses a larger keyboard step');
  await page.locator('#fit').click();
  await page.locator('.node').first().click();
  assert.equal(await page.locator('.node.selected').count(),1,'Node inspection works after resizing');
  assert.equal(await page.locator('#legend .legend-group').count(),2);
  assert.equal(await page.locator('[data-legend-group="operations"]').count(),1,'Board explains its operation symbols');
  assert.equal(await page.locator('[data-legend-group="nodes"] h3').innerText(),language==='ko'?'노드':'Nodes');
  assert.equal(await page.locator('[data-legend-group="arrows"]').count(),0,'Hidden arrows do not dominate the default legend');
  await page.locator('#show-connections').click();
  assert.equal(await page.locator('[data-legend-group="arrows"] h3').innerText(),language==='ko'?'화살표':'Arrows');
  assert.equal(await page.locator('[data-legend-group="nodes"] .legend-arrow').count(),0);
  assert.equal(await page.locator('[data-legend-group="arrows"] .legend-node').count(),0);
  assert.equal(await page.locator('.legend-arrow.data').count(),1,'Data-transfer arrows have their own legend');
  assert.equal(await page.locator('.legend-arrow.uncertain .legend-arrow-shaft').evaluate(n=>getComputedStyle(n).strokeDasharray),'1px, 6px');
  await page.locator('#show-connections').click();
  assert(await page.locator('#legend').evaluate(n=>n.scrollWidth<=n.clientWidth+1),'Legend wraps within the viewport');
  await page.locator('#legend').scrollIntoViewIfNeeded();
  await page.locator('#zoom-level').click();
  assert.equal((await camera()).scale,1,'100% stays available while inspecting a node on every viewport');
  await page.locator('#zoom-in').click();
  assert(Math.abs((await camera()).scale-1.2)<.001,'Manual zoom is not undone by automatic node framing');
  await page.locator('#zoom-out').click();
  assert(Math.abs((await camera()).scale-1)<.001,'Manual zoom out retains the requested scale with the inspector open');
  assert.equal(await page.locator('#panel.open').count(),1);
  assert.equal(await page.locator('.node.selected').count(),1);
  await page.locator('#close-panel').click();
  if(language==='ko')await page.locator('.canvas-footer').screenshot({path:path.resolve(process.argv[2],'legend-'+width+'-'+(dark?'dark':'light')+'.png')});
  const beforeZoom=(await camera()).scale;
  await page.locator('#zoom-in').click();
  assert((await camera()).scale>beforeZoom,'Zoom still works after resizing');
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);await context.close();checks++;
 }}finally{await browser.close()}
 console.log(checks+' summary/detail journeys passed: reviewed responsibilities, hidden internal steps, scoped process lists, parallel relations, node rules, return focus and offline use.');
})().catch(error=>{console.error(error);process.exitCode=1});
