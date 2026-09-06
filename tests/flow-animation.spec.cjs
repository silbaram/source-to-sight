const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const url=(folder,name)=>pathToFileURL(path.join(root,'build',folder,name+'.html')).href;

test.beforeEach(async({context,page})=>{
  await context.setOffline(true);
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.clock.install();
});

function variant(info,change){
  const data=JSON.parse(fs.readFileSync(path.join(root,'fixtures/agent-run.json'),'utf8'));
  change(data);
  const sources=JSON.parse(fs.readFileSync(path.join(root,'fixtures/source-repositories.json'),'utf8'));
  const source=sources.find(s=>s.repository===data.snapshot.repository);
  const input=info.outputPath('input.json'),output=info.outputPath('page.html');
  fs.mkdirSync(path.dirname(input),{recursive:true});
  fs.writeFileSync(input,JSON.stringify(data));
  const result=spawnSync('python3',[path.join(root,'skills/code-flow/scripts/s2s.py'),'render',input,
    '--source-root',path.join(root,'.cache/sources',source.id),'--output',output],{encoding:'utf8'});
  expect(result.status,result.stderr).toBe(0);
  return pathToFileURL(output).href;
}

async function start(page,target=url('examples','agent-run')){
  await page.goto(target);
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('#workflow').click();
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await page.locator('#play').click();
}

async function tokenProgress(page){
  return page.locator('.flow-token').evaluate(token=>{
    const route=token.parentElement.querySelector('.edge-path');
    const point=token.getCTM();
    const tokenPoint=new DOMPoint(0,0).matrixTransform(point).matrixTransform(route.getCTM().inverse());
    const length=route.getTotalLength();
    let best=Infinity,at=0;
    for(let i=0;i<=200;i++){
      const p=route.getPointAtLength(length*i/200),distance=Math.hypot(tokenPoint.x-p.x,tokenPoint.y-p.y);
      if(distance<best){best=distance;at=i/200;}
    }
    return {at,distance:best,edge:token.parentElement.dataset.id,length};
  });
}

test('playback moves one marker along the actual source-to-target route and pauses cleanly',async({page})=>{
  await start(page);
  await expect(page.locator('#flow-transfer')).toContainText('요청 기록');
  await expect(page.locator('#flow-transfer')).toContainText('계속할지 확인');
  await page.clock.runFor(180);
  const first=await tokenProgress(page);
  await page.clock.runFor(560);
  const later=await tokenProgress(page);
  expect(first.edge).toBe('start-loop');expect(later.edge).toBe(first.edge);
  expect(later.at-first.at).toBeGreaterThan(.4);
  expect(first.distance).toBeLessThan(first.length/200+1);
  expect(later.distance).toBeLessThan(later.length/200+1);
  await expect(page.locator('.flow-token')).toHaveCount(1);
  const visible = await page.evaluate(()=>{
    const c=document.getElementById('canvas').getBoundingClientRect();
    return [...document.querySelectorAll('.node.flow-origin,.node.flow-destination,.flow-token')].every(n=>{
      const r=n.getBoundingClientRect();
      return r.left>=Math.max(0,c.left)&&r.right<=Math.min(innerWidth,c.right)&&
        r.top>=Math.max(0,c.top)&&r.bottom<=Math.min(innerHeight,c.bottom);
    });
  });
  expect(visible).toBe(true);
  await page.clock.runFor(430);
  await expect(page.locator('.node[data-id=loop]')).toHaveClass(/flow-arrived/);
  await page.locator('#play').click();
  await expect(page.locator('.flow-token,.node.flow-arrived')).toHaveCount(0);
  const step=await page.locator('#step-count').textContent();
  await page.clock.runFor(2000);
  await expect(page.locator('#step-count')).toHaveText(step);
});

test('node captions animate only an existing unique forward connection',async({page})=>{
  await start(page,url('m1','web-dispatch'));
  await expect(page.locator('.flow-token')).toHaveCount(0); // registration entry
  await page.clock.runFor(1500);
  await expect(page.locator('.flow-token')).toHaveCount(0); // no register → serve call
  await page.clock.runFor(1700);
  const token=await tokenProgress(page);
  expect(token.edge).toBe('find-route');
  await expect(page.locator('#flow-transfer')).toContainText('메서드별 경로 트리');
  await page.clock.runFor(1400);
  await expect(page.locator('.flow-token')).toHaveCount(0); // no invented tree → serve return
  await expect(page.locator('#flow-transfer')).toBeHidden();
});

test('registration and uncertain relationships retain static evidence styling',async({page})=>{
  await start(page,url('examples','framework-plugin'));
  await page.clock.runFor(400);
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('.edge[data-id=register-hook]')).toHaveClass(/active/);
  await expect(page.locator('#flow-transfer')).toBeVisible();
  await page.clock.runFor(5900);
  await expect(page.locator('#step-count')).toHaveText('05 / 05');
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#flow-transfer .pill')).toHaveClass(/uncertain/);
  await expect(page.locator('.edge[data-id=multi-plugin] .edge-path')).toHaveAttribute('marker-end','url(#arrow-uncertain)');
});

test('ambiguous edges and unchecked step captions do not acquire motion',async({page},info)=>{
  const target=variant(info,data=>{
    const steps=data.scenarios[0].steps;
    steps[0].nodeId='request';delete steps[0].edgeId;
    steps[1].nodeId='loop';delete steps[1].edgeId;
    data.edges.push({...data.edges.find(e=>e.id==='start-loop'),id:'another-start'});
    steps[2].supportStatus='uncertain';steps[2].confidence='inferred';
  });
  await start(page,target);
  await page.clock.runFor(1700);
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#flow-transfer')).toBeHidden();
  await page.clock.runFor(1500);
  await expect(page.locator('.edge[data-id=step-model]')).toHaveClass(/active/);
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#caption .pill')).toHaveClass(/uncertain/);
});

test('single-step playback finishes its transfer before stopping',async({page},info)=>{
  const target=variant(info,data=>{data.scenarios=[{...data.scenarios[0],steps:[data.scenarios[0].steps[0]]}];});
  await start(page,target);
  await page.clock.runFor(400);
  await expect(page.locator('.flow-token')).toHaveCount(1);
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','true');
  await page.clock.runFor(1200);
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#step-count')).toHaveText('01 / 01');
});

test('failed source locations never produce a moving confirmed connection',async({page},info)=>{
  const target=variant(info,data=>{data.evidence.find(e=>e.id==='ev-run').contentHash='0'.repeat(64);});
  await start(page,target);
  await page.clock.runFor(400);
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#flow-transfer .pill')).toHaveClass(/unverified/);
  await expect(page.locator('.edge[data-id=start-loop] .edge-path')).toHaveAttribute('marker-end','url(#arrow-uncertain)');
  await page.clock.runFor(1300);
  await expect(page.locator('.edge[data-id=loop-step] .flow-token')).toHaveCount(1);
});

test('reduced motion keeps direction and step information without moving markers',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await start(page);
  await page.clock.runFor(500);
  await expect(page.locator('.flow-token,.node.flow-arrived')).toHaveCount(0);
  await expect(page.locator('#flow-transfer')).toContainText('→');
  await expect(page.locator('.edge[data-id=start-loop]')).toHaveClass(/active/);
  await page.clock.runFor(1100);
  await expect(page.locator('#step-count')).toHaveText('02 / 06');
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.clock.runFor(200);
  await expect(page.locator('.flow-token')).toHaveCount(1);
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(page.locator('.flow-token,.node.flow-arrived')).toHaveCount(0);
});

test('zoom, resize and self-loops keep markers on the routed SVG path',async({page})=>{
  await page.goto(url('examples','agent-run'));
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('#workflow').click();
  await page.locator('#scenario').selectOption('1');
  await page.locator('#play').click();
  await page.clock.runFor(1720);
  let p=await tokenProgress(page);
  expect(p.edge).toBe('repeat');
  await page.locator('#zoom-in').click();
  await page.setViewportSize({width:1000,height:700});
  await page.clock.runFor(250);
  p=await tokenProgress(page);
  expect(p.edge).toBe('repeat');expect(p.at).toBeGreaterThan(.3);
  expect(p.distance).toBeLessThan(p.length/200+1);
  await expect(page.locator('.flow-token')).toHaveCount(1);
  await page.locator('#structure').click();
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#flow-transfer')).toBeHidden();
});

test('selection cancels transfer and no-scenario graphs retain no playback',async({page})=>{
  await start(page);
  await page.clock.runFor(200);
  await page.locator('.node[data-id=loop]').click();
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await page.goto(url('examples','utility-minimum'));
  await expect(page.locator('#player')).toBeHidden();
  await expect(page.locator('.flow-token')).toHaveCount(0);
});
