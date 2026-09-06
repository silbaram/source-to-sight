const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {spawnSync}=require('node:child_process');
const {settleCamera}=require('./playback-clock.cjs');
const root=path.resolve(__dirname,'..');
const run=path.resolve(root,process.env.S2S_EVAL_DIR||'build/eval/m4');
const url=id=>pathToFileURL(path.join(run,id+'.html')).href;

test.beforeEach(async({page,context})=>{
  await context.setOffline(true);
  await page.clock.install({time:new Date('2026-01-01T00:00:00Z')});
  await page.clock.pauseAt(new Date('2026-01-01T00:00:01Z'));
});
async function open(page,id='agent-parallel-tools'){
  await page.goto(url(id));
  await expect(page.locator('html')).toHaveAttribute('data-ready','true');
  await page.evaluate(()=>document.fonts.ready);
}
async function jump(page,index=3){
  await page.locator('#workflow').click();
  await page.locator('#step-picker').selectOption(String(index));
  await settleCamera(page);
}
async function start(page,index=3){
  await open(page);await jump(page,index);
  await page.locator('#play').click();await settleCamera(page);
}
const count=(page,text)=>expect(page.locator('#step-count')).toHaveText(text);
const params=page=>new URL(page.url()).hash.slice(1);
async function choose(page,id){
  await page.locator('#list-title').click();
  const buttons=page.locator('#component-list button');
  const index=await buttons.evaluateAll((nodes,id)=>nodes.findIndex(n=>n.dataset.nodeId===id),id);
  await buttons.nth(index).click();
  await settleCamera(page);
}

for(const rate of ['1','1.5','2'])test(rate+'x keeps transfer and step progress on the same clock',async({page})=>{
  await page.emulateMedia({reducedMotion:'no-preference'});
  await open(page);await jump(page);
  await page.locator('#playback-speed').selectOption(rate);
  await page.locator('#play').click();await settleCamera(page);
  await expect(page.locator('.flow-token')).toHaveCount(1);
  const first=await page.locator('.flow-token').getAttribute('transform');
  await page.clock.runFor(300/Number(rate));
  expect(await page.locator('.flow-token').getAttribute('transform')).not.toBe(first);
  await page.clock.runFor(1000/Number(rate));
  await count(page,'04 / 08');
  await page.clock.runFor(300/Number(rate));
  await count(page,'05 / 08');
});

test('changing speed and pausing retain elapsed explanation time',async({page})=>{
  await page.emulateMedia({reducedMotion:'no-preference'});
  await start(page);await page.clock.runFor(400);
  await page.locator('#playback-speed').selectOption('2');
  await page.clock.runFor(400);await count(page,'04 / 08');
  await page.locator('#play').click();
  await page.clock.runFor(3000);
  await page.locator('#playback-speed').selectOption('1.5');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await count(page,'04 / 08');
  await page.locator('#play').click();await settleCamera(page);
  await page.clock.runFor(90);await count(page,'04 / 08');
  await page.clock.runFor(160);await count(page,'05 / 08');
});

test('a speed change during framing waits for the camera before counting time',async({page})=>{
  await page.emulateMedia({reducedMotion:'no-preference'});
  await open(page);await jump(page);
  await page.locator('#canvas').evaluate(n=>{n.scrollLeft=0;n.scrollTop=0;});
  await page.locator('#play').click();
  await expect(page.locator('#canvas')).toHaveClass(/camera-moving/);
  await page.clock.runFor(100);
  await page.locator('#playback-speed').selectOption('2');
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await settleCamera(page);
  await page.clock.runFor(600);await count(page,'04 / 08');
  await page.clock.runFor(200);await count(page,'05 / 08');
});

test('direct step selection cancels autoplay and reveals detail targets',async({page})=>{
  await start(page);
  await page.clock.runFor(100);
  await page.locator('#step-picker').selectOption('4');await settleCamera(page);
  await count(page,'05 / 08');
  await expect(page.locator('#mode')).toHaveValue('detail');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await page.clock.runFor(10000);await count(page,'05 / 08');
  await page.locator('#step-picker').selectOption('7');await settleCamera(page);
  await count(page,'08 / 08');await expect(page.locator('#next')).toBeDisabled();
  await page.locator('#scenario').selectOption('2');await settleCamera(page);
  await count(page,'01 / 02');
  await expect(page.locator('#step-picker option')).toHaveCount(2);
});

test('a long explanation can jump directly to its final step and restore it',async({page},info)=>{
  const graph=JSON.parse(fs.readFileSync(path.join(root,'eval/m2/graphs/agent-parallel-tools.json'),'utf8'));
  graph.provenance={...graph.provenance,kind:'synthetic',description:'Synthetic long-step navigation fixture.',humanReviewed:false};
  const scenario=graph.scenarios[0],original=scenario.steps[0];
  scenario.steps=Array.from({length:60},(_,i)=>({...original,id:'long-step-'+i,caption:'검증용 설명 단계 '+(i+1)}));
  graph.scenarios=[scenario];graph.links={};
  const input=info.outputPath('long.json'),output=info.outputPath('long.html');
  fs.mkdirSync(path.dirname(input),{recursive:true});fs.writeFileSync(input,JSON.stringify(graph));
  const built=spawnSync('python3',[path.join(root,'skills/code-flow/scripts/author.py'),'build',input,
    '--source-root',path.join(root,'.cache/m1-sources/smolagents'),'--output',output],{encoding:'utf8'});
  expect(built.status,built.stderr).toBe(0);
  await page.goto(pathToFileURL(output).href);await jump(page,59);
  await count(page,'60 / 60');await expect(page.locator('#next')).toBeDisabled();
  expect(new URLSearchParams(params(page)).get('step')).toBe('long-step-59');
  await page.reload();await count(page,'60 / 60');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
});

test('keyboard focus moves between actual nodes and Enter opens their evidence',async({page},info)=>{
  await open(page);
  await page.locator('#canvas').focus();await page.keyboard.press('Enter');await settleCamera(page);
  const first=await page.evaluate(()=>document.activeElement.dataset.id);
  expect(first).toBeTruthy();
  await page.keyboard.press(info.project.name==='desktop'?'ArrowRight':'ArrowDown');await settleCamera(page);
  const next=await page.evaluate(()=>document.activeElement.dataset.id);
  expect(next).toBeTruthy();expect(next).not.toBe(first);
  await page.keyboard.press('Enter');await settleCamera(page);
  await expect(page.locator('#panel')).toBeVisible();
  expect(new URLSearchParams(params(page)).get('node')).toBe(next);
  await page.keyboard.press('Escape');
  expect(await page.evaluate(()=>document.activeElement.dataset.id)).toBe(next);
});

test('walkthrough shortcuts preserve native keys in inputs and selection controls',async({page})=>{
  await open(page);await jump(page,0);
  await page.locator('#canvas').focus();
  await page.keyboard.press(']');await settleCamera(page);await count(page,'02 / 08');
  await page.keyboard.press('[');await settleCamera(page);await count(page,'01 / 08');
  await page.keyboard.press('p');await settleCamera(page);
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','true');
  await page.keyboard.press('p');await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await page.locator('#search').fill('');await page.locator('#search').focus();
  await page.keyboard.type('p[]');await expect(page.locator('#search')).toHaveValue('p[]');
  await count(page,'01 / 08');
  await page.locator('#playback-speed').focus();await page.keyboard.press('p');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await page.locator('#canvas').dispatchEvent('keydown',{key:']',isComposing:true});
  await count(page,'01 / 08');
  await page.locator('#canvas').focus();await page.keyboard.press('Space');await settleCamera(page);
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','true');
});

test('a copied walkthrough link restores scenario, stable step, detail and speed without autoplay',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{window.copied=text;}}}));
  await open(page);await jump(page,4);
  await page.locator('#playback-speed').selectOption('1.5');
  const caption=await page.locator('#caption').textContent();
  const historyLength=await page.evaluate(()=>history.length);
  await page.locator('#play').click();await settleCamera(page);
  await page.locator('#copy-position').click();
  const link=await page.evaluate(()=>window.copied);
  expect(link).toBe(page.url());
  expect(await page.evaluate(()=>history.length)).toBe(historyLength);
  await page.reload();
  await count(page,'05 / 08');
  await expect(page.locator('#caption')).toHaveText(caption);
  await expect(page.locator('#mode')).toHaveValue('detail');
  await expect(page.locator('#playback-speed')).toHaveValue('1.5');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#navigation-notice')).toBeHidden();
});

test('node inspection links reveal hidden detail nodes with their evidence',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{window.copied=text;}}}));
  await open(page);
  const graph=JSON.parse(await page.locator('#s2s-data').textContent());
  const node=graph.nodes.find(n=>n.importance==='detail');
  await choose(page,node.id);
  await page.locator('#copy-inspection').click();
  expect(new URLSearchParams(new URL(await page.evaluate(()=>window.copied)).hash.slice(1)).get('node')).toBe(node.id);
  await page.reload();
  await expect(page.locator('#mode')).toHaveValue('detail');
  await expect(page.locator('#panel-title')).toHaveText(node.label);
  await expect(page.locator('#panel')).toBeVisible();
  expect(await page.locator('.node.selected').getAttribute('data-id')).toBe(node.id);
  await expect(page.locator('#panel .evidence-item').first()).toBeVisible();
});

test('hash navigation and unavailable or malformed targets restore a safe view',async({page})=>{
  await open(page);await jump(page,3);
  const valid=params(page);
  for(const [key,value] of [['step','deleted-step'],['scenario','deleted-flow'],['node','missing-node'],['edge','missing-edge'],['subject','another-project'],['speed','8'],['view','other']]) {
    const broken=new URLSearchParams(valid);broken.set(key,value);
    await page.evaluate(hash=>{location.hash=hash;},'#'+broken);
    await expect(page.locator('#navigation-notice')).toBeVisible();
    await expect(page.locator('#structure')).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('#player')).toBeHidden();
    await expect(page.locator('#panel')).toBeHidden();
    await page.evaluate(hash=>{location.hash=hash;},'#'+valid);
    await expect(page.locator('#navigation-notice')).toBeHidden();
    await count(page,'04 / 08');
  }
  await page.evaluate(hash=>{location.hash=hash;},'#'+valid+'&step=duplicate');
  await expect(page.locator('#navigation-notice')).toBeVisible();
  await page.evaluate(()=>{location.hash='#canvas';});
  await expect(page.locator('#structure')).toHaveAttribute('aria-pressed','true');
});

test('single-node and unordered-only pages never acquire playback controls from shortcuts or links',async({page})=>{
  for(const id of ['utility-strip','plugin-blocked-registration']) {
    await open(page,id);
    await expect(page.locator('#player')).toBeHidden();
    await page.locator('#canvas').focus();await page.keyboard.press('p');await page.keyboard.press(']');
    await expect(page.locator('#player')).toBeHidden();
    const graph=JSON.parse(await page.locator('#s2s-data').textContent());
    const broken=new URLSearchParams({s2s:'1',subject:graph.subject.id,view:'flow',scenario:'missing'});
    await page.evaluate(hash=>{location.hash=hash;},'#'+broken);
    await expect(page.locator('#navigation-notice')).toBeVisible();
    await expect(page.locator('#player')).toBeHidden();
  }
});

test('reduced motion keeps captions, conditions, direction and warning status at every speed',async({page})=>{
  await page.emulateMedia({reducedMotion:'no-preference'});
  await open(page);await jump(page,3);
  const text=await page.locator('#caption,#step-condition,#flow-transfer').allTextContents();
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.locator('#playback-speed').selectOption('2');
  await page.locator('#play').click();
  expect(await page.locator('#caption,#step-condition,#flow-transfer').allTextContents()).toEqual(text);
  await expect(page.locator('.flow-token,.node.explaining')).toHaveCount(0);
  await expect(page.locator('#canvas')).not.toHaveClass(/camera-moving/);
  await page.clock.runFor(800);await count(page,'05 / 08');
  await expect(page.locator('.flow-token,.node.explaining')).toHaveCount(0);
});

test('the same step and speed controls work across all complex project profiles',async({page})=>{
  for(const id of ['utility-retry-budget','plugin-wrapper-unwind','library-resize-callbacks','agent-parallel-tools','event-async-lifecycle','web-routing-fallbacks']){
    await open(page,id);
    const graph=JSON.parse(await page.locator('#s2s-data').textContent());
    for(let i=0;i<graph.scenarios.length;i++){
      await page.locator('#workflow').click();
      await page.locator('#scenario').selectOption(String(i));
      const steps=graph.scenarios[i].steps,last=steps.length-1;
      await page.locator('#step-picker').selectOption(String(last));await settleCamera(page);
      await expect(page.locator('#caption')).toContainText(steps[last].caption);
      await expect(page.locator('#next')).toBeDisabled();
      await page.locator('#playback-speed').selectOption('2');
      const saved=new URLSearchParams(params(page));
      expect(saved.get('scenario')).toBe(graph.scenarios[i].id);expect(saved.get('step')).toBe(steps[last].id);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    }
  }
});

test('mobile sheets resize while their close, link and focus controls remain reachable',async({page},info)=>{
  await page.setViewportSize({width:390,height:844});
  await open(page);
  const node=JSON.parse(await page.locator('#s2s-data').textContent()).nodes[0];
  await choose(page,node.id);
  const size=()=>page.locator('#panel').evaluate(n=>n.getBoundingClientRect().height);
  const compact=await size();
  await page.locator('#panel-size').click();await settleCamera(page);
  expect(await size()).toBeGreaterThan(compact+10);
  await expect(page.locator('#panel-size')).toHaveAttribute('aria-expanded','true');
  await page.locator('#panel-size').click();await settleCamera(page);
  expect(await size()).toBeCloseTo(compact,0);
  for(const id of ['close-panel','copy-inspection','panel-size','focus-related']){
    expect(await page.locator('#'+id).evaluate(n=>{const r=n.getBoundingClientRect();return r.height>=44&&r.top>=0&&r.bottom<=innerHeight&&document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===n;})).toBe(true);
  }
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:path.join(root,'build/qa/m4',info.project.name+'-sheet.png')});
});

test('denied clipboard and URL updates keep a manually copyable current-view link',async({page})=>{
  await page.addInitScript(()=>{
    Object.defineProperty(navigator,'clipboard',{get(){throw new Error('Clipboard denied');}});
    document.execCommand=()=>{throw new Error('Copy denied');};
    history.replaceState=()=>{throw new Error('History denied');};
  });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await open(page);await jump(page,4);
  await page.locator('#copy-position').click();
  await expect(page.locator('#copy-fallback')).toBeVisible();
  const link=await page.locator('#copy-text').inputValue();
  expect(new URLSearchParams(new URL(link).hash.slice(1)).get('view')).toBe('flow');
  await page.keyboard.press('Escape');
  await expect(page.locator('#copy-position')).toBeFocused();
  await page.goto(link);await count(page,'05 / 08');
  expect(errors).toEqual([]);
});
