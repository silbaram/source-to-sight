const {test,expect}=require('@playwright/test');
const path=require('node:path');
const fs=require('node:fs');
const {pathToFileURL}=require('node:url');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const examples=path.join(root,'build/examples');
const cases=fs.readdirSync(examples).filter(p=>p.endsWith('.html'));
const url=name=>pathToFileURL(path.join(examples,name+'.html')).href;

test.beforeEach(async({context})=>{await context.setOffline(true);});

function renderVariant(info,change,fixtureName='cli-transform') {
  const data=JSON.parse(fs.readFileSync(path.join(root,'fixtures',fixtureName+'.json'),'utf8'));
  change(data);
  const repositories=JSON.parse(fs.readFileSync(path.join(root,'fixtures/source-repositories.json'),'utf8'));
  const repository=repositories.find(r=>r.repository===data.snapshot.repository);
  const sourceRoot=repository?path.join(root,'.cache/sources',repository.id):root;
  const input=info.outputPath('input.json'),output=info.outputPath('page.html');
  fs.mkdirSync(path.dirname(input),{recursive:true});
  fs.writeFileSync(input,JSON.stringify(data));
  const result=spawnSync('python3',[path.join(root,'skills/code-flow/scripts/s2s.py'),
    'render',input,'--source-root',sourceRoot,'--output',output],{encoding:'utf8'});
  expect(result.status,result.stderr).toBe(0);
  return pathToFileURL(output).href;
}

for(const file of cases) test(file+' renders offline with sound geometry',async({page},info)=>{
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await page.goto(pathToFileURL(path.join(examples,file)).href);
  await expect(page.locator('html')).toHaveAttribute('data-ready','true');
  await page.evaluate(()=>document.fonts.ready);
  expect(errors).toEqual([]);expect(requests).toEqual([]);
  const geometry=await page.evaluate(()=>{
    const rects=[...document.querySelectorAll('.node')].map(n=>({id:n.dataset.id,r:n.getBoundingClientRect()}));
    const overlapping=[];
    for(let a=0;a<rects.length;a++)for(let b=a+1;b<rects.length;b++){
      const x=rects[a].r,y=rects[b].r;
      if(Math.min(x.right,y.right)-Math.max(x.left,y.left)>2&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>2)
        overlapping.push([rects[a].id,rects[b].id]);
    }
    const data=JSON.parse(document.getElementById('s2s-data').textContent);
    const crossings=[],disconnected=[];
    const origin=document.getElementById('connections').getBoundingClientRect();
    for(const group of document.querySelectorAll('.edge')){
      const edge=data.edges.find(e=>e.id===group.dataset.id);
      const route=group.querySelector('.edge-path'),length=route.getTotalLength();
      for(const [id,distance] of [[edge.from,0],[edge.to,length]]){
        const r=rects.find(n=>n.id===id).r,p=route.getPointAtLength(distance);
        const x=p.x+origin.left,y=p.y+origin.top;
        const inside=x>=r.left-3&&x<=r.right+3&&y>=r.top-3&&y<=r.bottom+3;
        const boundary=Math.min(Math.abs(x-r.left),Math.abs(x-r.right),Math.abs(y-r.top),Math.abs(y-r.bottom))<=3;
        if(!inside||!boundary)disconnected.push([edge.id,id]);
      }
      for(const node of rects){
        if([edge.from,edge.to].includes(node.id))continue;
        for(let distance=0;distance<length;distance+=3){
          const p=route.getPointAtLength(distance),x=p.x+origin.left,y=p.y+origin.top,r=node.r;
          if(x>r.left+2&&x<r.right-2&&y>r.top+2&&y<r.bottom-2){crossings.push([edge.id,node.id]);break;}
        }
      }
    }
    return {width:document.documentElement.scrollWidth,viewport:innerWidth,overlapping,crossings,disconnected};
  });
  expect(geometry.width).toBeLessThanOrEqual(geometry.viewport);
  expect(geometry.overlapping).toEqual([]);
  expect(geometry.crossings).toEqual([]);
  expect(geometry.disconnected).toEqual([]);
  if(['agent-run.html','adversarial.html','framework-plugin.html','utility-minimum.html','insufficient.html'].includes(file)){
    await page.screenshot({path:path.join(root,'build/qa',info.project.name+'-'+file+'.png'),fullPage:true});
  }
});

test('a one-node utility is successful and has no playback controls',async({page})=>{
  await page.goto(url('utility-minimum'));
  await expect(page.locator('.node')).toHaveCount(1);
  await expect(page.locator('#player')).toBeHidden();
  await expect(page.locator('#insufficient')).toBeHidden();
  await expect(page.locator('#status-badge')).toHaveText('지정 범위 확인');
  await page.locator('.node').click();
  await expect(page.locator('#panel')).toBeVisible();
  await expect(page.locator('#panel-title')).toHaveText('서식 표시 제거');
  await expect(page.locator('#panel .location').first()).toHaveText('index.js');
});

test('playback reveals a detail node and scenario switching resets the step',async({page})=>{
  await page.goto(url('agent-run'));
  await expect(page.locator('.node[data-id=memory]')).toHaveCount(0);
  for(let i=0;i<5;i++)await page.locator('#next').click();
  await expect(page.locator('#step-count')).toHaveText('06 / 06');
  await expect(page.locator('#mode')).toHaveValue('detail');
  await expect(page.locator('.node[data-id=memory]')).toHaveClass(/active/);
  await page.locator('#scenario').selectOption('1');
  await expect(page.locator('#step-count')).toHaveText('01 / 03');
  await page.locator('#mode').selectOption('core');
  await expect(page.locator('.node[data-id=memory]')).toHaveCount(0);
  await expect(page.locator('#step-count')).toHaveText('01 / 03');
});

test('automatic playback advances and pauses at the final step',async({page})=>{
  await page.clock.install();
  await page.goto(url('cli-transform'));
  await page.locator('#play').click();
  await page.clock.fastForward(1700);
  await expect(page.locator('#step-count')).toHaveText('02 / 02');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
});

test('unverified evidence is visibly different and candidates remain readable',async({page})=>{
  await page.goto(url('adversarial'));
  await expect(page.locator('.node[data-id=n0]')).toHaveClass(/unverified/);
  await expect(page.locator('#warnings')).toHaveAttribute('open','');
  await expect(page.locator('#warning-list')).toContainText('example/fast.js:10');
  await page.locator('.node[data-id=n0]').click();
  await expect(page.locator('#panel')).toContainText('위치를 다시 확인하지 못함');
});

test('insufficient evidence shows reasons and next attempts',async({page})=>{
  await page.goto(url('insufficient'));
  await expect(page.locator('#workspace')).toBeHidden();
  await expect(page.locator('#insufficient')).toContainText('실제 등록 위치를 찾지 못했습니다.');
  await expect(page.locator('#insufficient')).toContainText('플러그인 이름이나 등록 파일');
});

test('paired pages navigate through relative local links',async({page})=>{
  await page.goto(url('utility-minimum'));
  await page.getByRole('link',{name:'규칙과 이유 ↗'}).click();
  await expect(page).toHaveURL(/utility-logic.html$/);
  await page.getByRole('link',{name:'동작 설명 ↗'}).click();
  await expect(page).toHaveURL(/utility-minimum.html$/);
});

test('keyboard focus opens and closes a node explanation',async({page},info)=>{
  await page.goto(url('utility-minimum'));
  const node=page.locator('.node').first();
  await node.focus();await page.keyboard.press('Enter');
  await expect(page.locator('#panel-title')).toHaveText('서식 표시 제거');
  if(info.project.name==='narrow'){
    await expect(page.locator('#close-panel')).toBeFocused();
    await page.keyboard.press('Escape');
    await expect(node).toBeFocused();
    await expect(page.locator('#panel')).toBeHidden();
  }
});

test('HTML-shaped text and quotes stay inert in a real browser',async({page},info)=>{
  const payload='</script><script>globalThis.injected=true</script><img src="https://example.invalid/x" onerror="globalThis.injected=true"> "quotes" __S2S_LAYOUT__';
  const title='Literal <img onerror="globalThis.injected=true"> & "quotes"';
  const target=renderVariant(info,data=>{data.summary.purpose=payload;data.summary.title=title;});
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await page.goto(target);
  await expect(page.locator('html')).toHaveAttribute('data-ready','true');
  await expect(page.locator('#purpose')).toHaveText(payload);
  await expect(page.locator('#title')).toHaveText(title);
  await expect(page).toHaveTitle(title+' · Source to Sight');
  await expect(page.locator('img')).toHaveCount(0);
  expect(await page.evaluate(()=>globalThis.injected)).toBeUndefined();
  expect(errors).toEqual([]);expect(requests).toEqual([]);
});

test('English pages use English controls and evidence labels',async({page},info)=>{
  const target=renderVariant(info,data=>{data.language='en';data.regeneration.language='en';});
  await page.goto(target);
  await expect(page.locator('html')).toHaveAttribute('lang','en');
  await expect(page.locator('#diagram-title')).toHaveText('Follow the picture');
  await expect(page.getByRole('button',{name:'Next step'})).toBeVisible();
  await page.locator('.node').first().click();
  await expect(page.locator('#panel')).toContainText('Location matches');
  await expect(page.getByRole('button',{name:'Copy location'}).first()).toBeVisible();
});

test('actions and state conditions remain visible with their own evidence',async({page},info)=>{
  await page.goto(url('cli-transform'));
  await page.locator('.node[data-id=convert]').click();
  await expect(page.locator('#panel')).toContainText('읽은 내용을 목표 형식으로 정리합니다.');
  await expect(page.locator('#panel li .evidence-item')).toHaveCount(1);
  if(info.project.name==='narrow')await page.keyboard.press('Escape');
  await page.locator('.node[data-id=output]').click();
  const transition=page.locator('#panel .transition');
  await expect(transition).toContainText('저장 대기 → 저장 완료');
  await expect(transition).toContainText('변경 조건');
  await expect(transition).toContainText('결과 파일 저장에 성공했을 때만');
  await expect(transition.locator('.evidence-item')).toHaveCount(1);
  // The condition has to be in the visible panel, not just the embedded IR.
  await expect(transition.getByText('결과 파일 저장에 성공했을 때만',{exact:true})).toBeVisible();
  await page.screenshot({path:path.join(root,'build/qa',info.project.name+'-state-condition.png'),fullPage:true});
});

for(const status of ['confirmed','uncertain','unverified'])test('region '+status+' keeps its own status and evidence',async({page},info)=>{
  const note='구역 구분에 대한 검토 사유입니다.';
  const target=renderVariant(info,data=>{
    const region=data.regions[0];region.verificationNote=note;
    if(status==='uncertain'){region.confidence='inferred';region.supportStatus='uncertain';}
    if(status==='unverified'){
      const evidence={...data.evidence[0],id:'ev-region-failed',endLine:999999};
      data.evidence.push(evidence);region.evidenceIds=[evidence.id];
    }
  },'utility-atlas');
  await page.goto(target);
  const region=page.locator('.region[data-id=public-api]');
  await expect(region.locator('.pill')).toHaveClass(new RegExp('\\b'+status+'\\b'));
  await expect(page.locator('.node[data-id=strip] .node-status')).toHaveText('위치·내용 확인');
  const inspect=region.getByRole('button',{name:'공개 기능 · 구역 근거 확인'});
  await inspect.focus();await page.keyboard.press('Enter');
  await expect(page.locator('#panel-title')).toHaveText('공개 기능');
  await expect(page.locator('#panel .pill').first()).toHaveClass(new RegExp('\\b'+status+'\\b'));
  await expect(page.locator('#panel')).toContainText(note);
  await expect(page.locator('#panel .location').first()).toHaveText('index.js');
  if(status==='unverified')await expect(page.locator('#panel')).toContainText('위치를 다시 확인하지 못함');
  if(status==='uncertain')await page.screenshot({path:path.join(root,'build/qa',info.project.name+'-region-uncertain.png'),fullPage:true});
  if(info.project.name==='narrow'){
    await page.keyboard.press('Escape');
    await expect(inspect).toBeFocused();
  }
  await region.getByRole('button',{name:'서식 표시 제거',exact:true}).click();
  await expect(page.locator('#panel-title')).toHaveText('서식 표시 제거');
  await expect(page.locator('#panel .pill').first()).toHaveClass(/confirmed/);
});
