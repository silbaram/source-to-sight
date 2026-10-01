'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.argv[3]||'playwright');

(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.S2S_CHROMIUM_EXECUTABLE?{executablePath:process.env.S2S_CHROMIUM_EXECUTABLE}:{})});
 let checks=0;
 try{for(const language of ['ko','en'])for(const width of [1440,390])for(const dark of [false,true]){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
  const page=await context.newPage(),errors=[],network=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('request',request=>{if(/^https?:/.test(request.url()))network.push(request.url())});
  const open=async name=>{
    await page.goto(pathToFileURL(path.resolve(process.argv[2],language,name+'.html')).href);
    await page.waitForSelector('html[data-ready=true]');
  };
  await open('operations');
  if(dark)await page.locator('#theme-toggle').click();
  const data=await page.locator('#s2s-data').evaluate(node=>JSON.parse(node.textContent));
  assert.equal(await page.locator('#canvas.process-board').count(),1,'Default structure is an operation board');
  assert.equal(await page.locator('#connections').isVisible(),false,'Default reading does not depend on arrows');
  assert(await page.locator('#stage').evaluate(stage=>new DOMMatrix(getComputedStyle(stage).transform).a>=.8),'Tall operation boards retain readable card text');
  assert(await page.evaluate(()=>{
    const canvas=document.getElementById('canvas').getBoundingClientRect();
    const first=document.querySelector('.node').getBoundingClientRect();
    return first.top>=canvas.top&&first.bottom<=canvas.bottom&&first.left>=canvas.left&&first.right<=canvas.right;
  }),'The first operation is visible when a tall board opens');
  assert.equal(await page.locator('#show-connections').getAttribute('aria-pressed'),'false');
  assert.equal(await page.locator('.node').count(),data.nodes.length);
  for(const node of data.nodes){
    const card=page.locator('.node[data-id="'+node.id+'"]');
    assert.equal(await card.getAttribute('data-operation-kind'),node.operation.kind);
    if(node.operation.targetKind)assert.equal(await card.getAttribute('data-target-kind'),node.operation.targetKind);
    assert((await card.locator('.node-operation-label').innerText()).trim(),'The operation is named in text');
    assert.equal(await card.locator('.node-operation-icon').count(),1);
    assert((await card.locator('.node-description').innerText()).includes(node.summary));
    if(node.operation.target)assert((await card.locator('.node-operation-target').innerText()).includes(node.operation.target));
    assert(!(await card.innerText()).includes(node.codeName),'Implementation identifiers are not public card prose');
  }
  const label=id=>page.locator('.node[data-id="node-'+id+'"] .node-operation-label').innerText();
  assert.notEqual(await label('read'),await label('save'),'Database read and write are distinct operations');
  assert.notEqual(await label('save'),await label('receipt'),'Database and file writes have distinct labels');
  assert.notEqual(await label('payment'),await label('publish'),'API requests and queue publishing have distinct labels');
  const iconShapes=await page.locator('.node[data-id="node-read"],.node[data-id="node-payment"],.node[data-id="node-publish"],.node[data-id="node-receipt"],.node[data-id="node-decide"]').evaluateAll(cards=>cards.map(card=>[...card.querySelectorAll('.node-operation-icon path')].map(part=>part.getAttribute('d')).join('|')));
  assert.equal(new Set(iconShapes).size,5,'Database, API, queue, file and decision symbols are distinct');
  if(width===1440){
    for(const resizedWidth of [390,1440]){
      await page.setViewportSize({width:resizedWidth,height:1000});
      await page.waitForFunction(expectedColumns=>{
        const canvas=document.getElementById('canvas').getBoundingClientRect();
        const cards=[...document.querySelectorAll('.node')];
        const first=cards[0].getBoundingClientRect();
        return new Set(cards.map(card=>card.style.left)).size===expectedColumns&&
          first.top>=canvas.top&&first.bottom<=canvas.bottom&&first.left>=canvas.left&&first.right<=canvas.right;
      },resizedWidth<760?1:2,{timeout:5000});
    }
  }
  const boardPositions=await page.locator('.node').evaluateAll(nodes=>nodes.map(node=>[node.dataset.id,node.style.left,node.style.top]));
  assert(await page.evaluate(()=>{
    const boxes=[...document.querySelectorAll('.node')].map(node=>node.getBoundingClientRect());
    return boxes.every((box,index)=>boxes.every((other,otherIndex)=>index===otherIndex||
      box.right<=other.left||other.right<=box.left||box.bottom<=other.top||other.bottom<=box.top));
  }),'Operation cards never overlap');
  const columns=new Set(boardPositions.map(position=>position[1]));
  assert.equal(columns.size,width<760?1:2,'Board uses the available reading width');
  await page.locator('#show-connections').click();
  assert.equal(await page.locator('#show-connections').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('#canvas.process-board').count(),0);
  assert.equal(await page.locator('#connections').isVisible(),true);
  const visibleEdges=await page.locator('#connections .edge').evaluateAll(edges=>edges.map(edge=>edge.dataset.id));
  assert.deepEqual(visibleEdges.sort(),data.edges.map(edge=>edge.id).sort(),'Optional connections preserve every reviewed edge');
  await page.locator('#show-connections').click();
  assert.deepEqual(await page.locator('.node').evaluateAll(nodes=>nodes.map(node=>[node.dataset.id,node.style.left,node.style.top])),boardPositions,'Returning to the board restores its layout');
  await page.locator('#workflow').click();
  assert.equal(await page.locator('#connections').isVisible(),true,'Path mode keeps its evidence-backed connections');
  const alternate=data.scenarios.findIndex(scenario=>scenario.kind==='alternate');
  await page.locator('#process-path').selectOption(String(alternate));
  assert((await page.locator('#process-current').innerText()).includes(data.scenarios[alternate].steps[0].condition),'Branch conditions remain visible');
  await page.locator('#structure').click();
  assert.equal(await page.locator('#connections').isVisible(),false);
  await page.locator('.node[data-id="node-read"]').click();
  assert.equal(await page.locator('#panel.open').count(),1);
  await page.locator('#panel .node-reference:has(> .evidence-item) > summary').click();
  const panel=await page.locator('#panel').innerText();
  assert(panel.includes('operations.py'),'Source locations remain available');
  assert(!panel.includes('read_order'),'Inspector does not expose implementation identifiers');
  const contrasts=await page.locator('.node-description,.node-operation-target').evaluateAll(elements=>{
    const rgba=value=>{const parts=value.match(/[\d.]+/g).map(Number);return [...parts.slice(0,3),parts[3]??1]};
    const over=(foreground,background)=>foreground.slice(0,3).map((channel,index)=>channel*foreground[3]+background[index]*(1-foreground[3]));
    const luminance=color=>color.map(channel=>{const value=channel/255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4}).reduce((value,channel,index)=>value+channel*[.2126,.7152,.0722][index],0);
    return elements.map(element=>{
      const layers=[];
      for(let node=element;node;node=node.parentElement)layers.push(rgba(getComputedStyle(node).backgroundColor));
      const background=layers.reverse().reduce((color,layer)=>over(layer,color),[255,255,255]);
      const foreground=over(rgba(getComputedStyle(element).color),background);
      const a=luminance(foreground),b=luminance(background);
      return {node:element.closest('.node').dataset.id,kind:element.className,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
    });
  });
  assert(contrasts.every(item=>item.ratio>=4.5),'Operation descriptions and targets meet 4.5:1 contrast: '+JSON.stringify(contrasts.filter(item=>item.ratio<4.5)));
  const publicText=await page.locator('body').innerText();
  assert(!/database\.save_order|payment_service\.charge|return request\[/.test(publicText));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'The page fits the viewport');
  await page.locator('#close-panel').click();
  if(language==='ko')await page.screenshot({path:path.resolve(process.argv[2],'operations-'+width+'-'+(dark?'dark':'light')+'.png')});
  await open('legacy');
  assert.equal(await page.locator('.node[data-operation-kind="process"]').count(),data.nodes.length,'Legacy titles never invent reviewed operation types');
  assert.equal(await page.locator('.node[data-target-kind]').count(),0);
  assert.equal(await page.locator('.node-operation-target').count(),0);
  assert(await page.locator('.node-operation-label').evaluateAll(nodes=>nodes.every(node=>['처리','Process'].includes(node.textContent))));
  await open('uncertain');
  const uncertain=page.locator('.node[data-id="node-payment"]');
  assert.equal(await uncertain.getAttribute('data-operation-kind'),'request');
  assert.equal(await uncertain.locator('.node-status.uncertain').count(),1,'The icon does not hide uncertainty');
  assert((await uncertain.getAttribute('aria-label')).includes(language==='ko'?'추정':'Uncertain'));
  assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
  await context.close();checks++;
 }}finally{await browser.close()}
 console.log(checks+' operation journeys passed: semantic actions and targets, arrow-free board, optional exact connections, legacy fallback, evidence and offline rendering.');
})().catch(error=>{console.error(error);process.exitCode=1});
