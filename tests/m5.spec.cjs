const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const run=path.resolve(root,process.env.S2S_EVAL_DIR||'build/eval/m5');
const url=id=>pathToFileURL(path.join(run,id+'.html')).href;
const maps=['utility','framework','agent','library','event','web'];
async function open(page,name='agent'){
  await page.goto(url(name+'-project'));
  await expect(page.locator('html')).toHaveAttribute('data-ready','true');
  await page.evaluate(()=>document.fonts.ready);
}
const graph=page=>page.locator('#s2s-data').evaluate(n=>JSON.parse(n.textContent));
test.beforeEach(async({page,context})=>{await context.setOffline(true);await page.emulateMedia({reducedMotion:'reduce'});});

for(const name of maps)test(name+' map shows its real groups, capabilities and navigable geometry offline',async({page},info)=>{
  const errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url());});
  await open(page,name);const data=await graph(page);
  await expect(page.locator('#layer-label')).toContainText('프로젝트 지도');
  await expect(page.locator('#player')).toBeHidden();
  await expect(page.locator('#workflow')).toBeHidden();
  await expect(page.locator('#capabilities > button')).toHaveCount(data.subjects.length);
  await page.locator('#mode').selectOption('detail');
  await expect(page.locator('.node')).toHaveCount(data.nodes.length);
  await expect(page.locator('.edge')).toHaveCount(data.edges.length);
  await expect(page.locator('.map-region')).toHaveCount(data.regions.length);
  const geometry=await page.evaluate(()=>{
    const box=n=>({id:n.dataset.id,x:n.offsetLeft,y:n.offsetTop,w:n.offsetWidth,h:n.offsetHeight});
    const nodes=[...document.querySelectorAll('.node')].map(box);
    const overlap=(a,b)=>Math.min(a.x+a.w,b.x+b.w)>Math.max(a.x,b.x)+1&&Math.min(a.y+a.h,b.y+b.h)>Math.max(a.y,b.y)+1;
    const collisions=nodes.flatMap((n,i)=>nodes.slice(i+1).filter(other=>overlap(n,other)).map(other=>[n.id,other.id]));
    const data=JSON.parse(document.querySelector('#s2s-data').textContent),groups=[...document.querySelectorAll('.map-region')].map(box);
    const badMembers=[];
    for(const region of data.regions){const group=groups.find(g=>g.id===region.id);for(const id of region.nodeIds){const node=nodes.find(n=>n.id===id);if(node.x<group.x||node.y<group.y||node.x+node.w>group.x+group.w||node.y+node.h>group.y+group.h)badMembers.push(id);}}
    const badLabels=[];
    for(const element of document.querySelectorAll('.map-region')){const g=box(element),label=box(element.querySelector('button'));label.x+=g.x;label.y+=g.y;if(nodes.some(n=>overlap(n,label)))badLabels.push(g.id);}
    return {collisions,badMembers,badLabels,overflow:document.documentElement.scrollWidth>innerWidth};
  });
  expect(geometry).toEqual({collisions:[],badMembers:[],badLabels:[],overflow:false});
  expect(errors).toEqual([]);expect(requests).toEqual([]);
  await page.screenshot({path:path.join(root,'build/qa/m5',info.project.name+'-'+name+'-map.png')});
});

test('a region reveals its detail members and actual neighbors, and Back restores the overview',async({page})=>{
  await open(page);const data=await graph(page),region=data.regions.find(r=>r.nodeIds.includes('executor'));
  const initial=await page.locator('.node').count();
  await page.locator('#atlas-regions button').filter({hasText:region.label}).click();
  const expected=new Set(region.nodeIds);
  for(const e of data.edges){if(region.nodeIds.includes(e.from))expected.add(e.to);if(region.nodeIds.includes(e.to))expected.add(e.from);}
  expect((await page.locator('.node').evaluateAll(nodes=>nodes.map(n=>n.dataset.id))).sort()).toEqual([...expected].sort());
  await expect(page.locator('#crumb')).toHaveText(region.label);
  expect(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('region')).toBe(region.id);
  await page.reload();await expect(page.locator('#crumb')).toHaveText(region.label);
  await page.locator('#overview').click();await expect(page.locator('.node')).toHaveCount(initial);
  await page.locator('#atlas-regions button').filter({hasText:region.label}).click();
  await page.locator('#back').click();await expect(page.locator('.node')).toHaveCount(initial);
  await expect(page.locator('#crumb')).toHaveText('프로젝트 / 전체 구성');
});

test('capability search reveals its responsible detail node and exact scope',async({page})=>{
  await open(page);const data=await graph(page),subject=data.subjects.find(s=>s.nodeId==='cli');
  await page.locator('#atlas-regions button').first().click();
  await page.locator('#search').fill('명령으로');
  await page.locator('#results [data-capability-id]').click();
  await expect(page.locator('#panel-title')).toHaveText(subject.label);
  await expect(page.locator('.node.selected')).toHaveAttribute('data-id','cli');
  await expect(page.locator('#mode')).toHaveValue('detail');
  await expect(page.locator('#panel-body')).toContainText(subject.scope.includes[0]);
  await expect(page.locator('#panel .capability-action button')).toContainText('생성 명령 복사');
  await page.keyboard.press('Escape');await expect(page.locator('#results [data-capability-id]')).toBeFocused();
});

test('ungenerated detail copies a precise request without leaving the map or creating an execution',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{window.copied=text;}}}));
  await open(page,'utility');const data=await graph(page),pending=data.subjects.find(s=>!s.link.generated);
  expect(pending).toBeTruthy();
  await page.locator('#capabilities [data-capability-id]').nth(data.subjects.indexOf(pending)).click();
  const before=page.url();await page.locator('#panel .capability-action button').click();
  expect(page.url()).toBe(before);
  const copied=await page.evaluate(()=>window.copied);
  for(const text of [pending.id,pending.scope.includes[0],'index.js','language=ko','atlas='])expect(copied).toContain(text);
  expect(fs.existsSync(path.resolve(run,pending.link.url))).toBe(false);
  await expect(page.locator('#player')).toBeHidden();
});

test('Core keeps capabilities visible inside a region and clears a hidden detail selection in the overview',async({page})=>{
  await open(page);const data=await graph(page),subject=data.subjects.find(s=>s.nodeId==='executor');
  const region=data.regions.find(r=>r.nodeIds.includes(subject.nodeId));
  await page.locator('#atlas-regions button').filter({hasText:region.label}).click();
  await page.locator('#capabilities [data-capability-id]').nth(data.subjects.indexOf(subject)).click();
  await page.locator('#mode').selectOption('core');
  await expect(page.locator('#panel-title')).toHaveText(subject.label);
  await expect(page.locator('.node.selected')).toHaveAttribute('data-id',subject.nodeId);
  await page.locator('#close-panel').click();await page.locator('#overview').click();
  await page.locator('#capabilities [data-capability-id]').nth(data.subjects.indexOf(subject)).click();
  await page.locator('#mode').selectOption('core');
  await expect(page.locator('#panel')).toBeHidden();await expect(page.locator('.node.selected')).toHaveCount(0);
});

test('capability owner stays visible after zoom and a mobile sheet resize',async({page})=>{
  await open(page);await page.locator('#capabilities button').first().click();
  await page.locator('#zoom-in').click();
  await page.setViewportSize({width:500,height:900});
  await expect(page.locator('#panel-size')).toBeVisible();
  await page.locator('#panel-size').click();
  await expect.poll(()=>page.locator('.node.selected').evaluate(node=>{
    const box=node.getBoundingClientRect(),panel=document.querySelector('#panel').getBoundingClientRect();
    return box.left>=0&&box.right<=innerWidth&&box.top>=0&&box.bottom<=panel.top;
  })).toBe(true);
});

for(const name of maps)test(name+' connects map, behavior and rules and returns to the selected map state',async({page})=>{
  await page.addInitScript(()=>{Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage denied');}});Object.defineProperty(window,'sessionStorage',{get(){throw new Error('Storage denied');}});});
  await open(page,name);const data=await graph(page),subject=data.subjects.find(s=>s.link.generated);
  const region=data.regions.find(r=>r.nodeIds.includes(subject.nodeId));
  if(region)await page.locator('#atlas-regions button').filter({hasText:region.label}).click();
  await page.locator('#capabilities [data-capability-id]').nth(data.subjects.indexOf(subject)).click();
  const camera=await page.evaluate(()=>({left:document.querySelector('#canvas').scrollLeft,top:document.querySelector('#canvas').scrollTop,zoom:document.querySelector('#zoom-level').textContent}));
  const expectedHash=new URLSearchParams(new URL(page.url()).hash.slice(1));
  await page.locator('#panel .capability-action a').click();
  await expect(page.locator('#layer-label')).toContainText('동작과 협력');
  const behavior=await graph(page);expect(behavior.subject.id).toBe(subject.id);
  expect(JSON.parse(fs.readFileSync(path.join(run,subject.link.url.replace(/\.html$/,'.render.json')),'utf8'))).toEqual(behavior);
  await page.getByRole('link',{name:'규칙과 이유 ↗'}).click();
  await expect(page.locator('.primer-intro .eyebrow')).toContainText('규칙과 이유');
  expect(JSON.parse(fs.readFileSync(path.join(run,behavior.links.logic.url.replace(/\.html$/,'.render.json')),'utf8'))).toEqual(await graph(page));
  await page.getByRole('link',{name:'프로젝트 지도 ↗'}).click();
  await expect(page.locator('#panel-title')).toHaveText(subject.label);
  await expect(page.locator('.node.selected')).toHaveAttribute('data-id',subject.nodeId);
  const restored=new URLSearchParams(new URL(page.url()).hash.slice(1));
  expect(restored.get('region')).toBe(expectedHash.get('region'));
  expect(restored.get('item')).toBe(subject.id);
  const after=await page.evaluate(()=>({left:document.querySelector('#canvas').scrollLeft,top:document.querySelector('#canvas').scrollTop,zoom:document.querySelector('#zoom-level').textContent}));
  expect(after.zoom).toBe(camera.zoom);expect(Math.abs(after.left-camera.left)).toBeLessThan(2);expect(Math.abs(after.top-camera.top)).toBeLessThan(2);
});

for(const name of maps)test(name+' returns from every available capability, including existing detail pages',async({page})=>{
  await open(page,name);const data=await graph(page);
  expect(data.subjects.filter(s=>s.link.generated)).toHaveLength({utility:1,framework:3,agent:2,library:2,event:2,web:2}[name]);
  for(const subject of data.subjects.filter(s=>s.link.generated)) {
    await page.locator('#capabilities [data-capability-id]').nth(data.subjects.indexOf(subject)).click();
    await page.locator('#panel .capability-action a').click();
    const child=await graph(page);
    expect(child.subject.id).toBe(subject.id);
    expect(child.links.atlas.generated).toBe(true);
    expect(JSON.parse(fs.readFileSync(path.join(run,subject.link.url.replace(/\.html$/,'.render.json')),'utf8'))).toEqual(child);
    await page.getByRole('link',{name:'프로젝트 지도 ↗'}).click();
    await expect(page.locator('#panel-title')).toHaveText(subject.label);
    await expect(page.locator('.node.selected')).toHaveAttribute('data-id',subject.nodeId);
  }
});

for(const mode of ['resize','legacy'])test('map return reframes its selected node after '+mode,async({page},info)=>{
  await open(page);const data=await graph(page),subject=data.subjects.find(s=>s.link.generated);
  const region=data.regions.find(r=>r.nodeIds.includes(subject.nodeId));
  await page.locator('#atlas-regions button').filter({hasText:region.label}).click();
  await page.locator('#capabilities [data-capability-id]').nth(data.subjects.indexOf(subject)).click();
  await page.locator('#panel .capability-action a').click();
  if(mode==='resize')await page.setViewportSize(info.project.name==='desktop'?{width:390,height:844}:{width:844,height:390});
  else await page.getByRole('link',{name:'프로젝트 지도 ↗'}).evaluate(link=>{
    const url=new URL(link.href),params=new URLSearchParams(url.hash.slice(1));
    params.delete('layout');params.set('camera','[2,50000,50000,50000]');
    url.hash='#'+params;link.href=url.href;
  });
  await page.getByRole('link',{name:'프로젝트 지도 ↗'}).click();
  await expect(page.locator('#panel-title')).toHaveText(subject.label);
  await expect(page.locator('#crumb')).toHaveText(region.label);
  await expect(page.locator('.node.selected')).toHaveAttribute('data-id',subject.nodeId);
  await expect(page.locator('#navigation-notice')).toBeHidden();
  await expect.poll(()=>page.locator('.node.selected').evaluate(node=>{
    const box=node.getBoundingClientRect(),canvas=document.querySelector('#canvas').getBoundingClientRect(),panel=document.querySelector('#panel').getBoundingClientRect();
    const right=Math.min(innerWidth,canvas.right,innerWidth>900?panel.left:Infinity);
    const bottom=Math.min(innerHeight,canvas.bottom,innerWidth<=900?panel.top:Infinity);
    return box.left>=Math.max(0,canvas.left)&&box.right<=right&&box.top>=Math.max(0,canvas.top)&&box.bottom<=bottom;
  })).toBe(true);
  if(mode==='resize')await page.screenshot({path:path.join(root,'build/qa/m5',info.project.name+'-return-after-resize.png')});
});

test('region evidence remains separate from node certainty and region labels are clickable',async({page})=>{
  await open(page);
  const region=page.locator('.map-region').first();
  const label=await region.locator('button').textContent();
  await region.locator('button').click();
  await expect(page.locator('#panel')).toBeVisible();
  expect(label).toContain(await page.locator('#panel-title').textContent());
  await expect(page.locator('#panel .evidence-item').first()).toBeVisible();
  await page.locator('.enter-region').click();await expect(page.locator('#panel')).toBeHidden();
});

test('an invalid region or camera falls back with a visible explanation',async({page})=>{
  await open(page);await page.locator('#atlas-regions button').first().click();
  const valid=new URLSearchParams(new URL(page.url()).hash.slice(1));
  for(const [key,value] of [['region','gone'],['camera','[0,1,2,3]'],['camera','{"x":1}'],['camera','[1,1e99,2,3]'],['layout','[1,2]']]){
    const broken=new URLSearchParams(valid);broken.set(key,value);
    await page.evaluate(hash=>{location.hash=hash;},'#'+broken);
    await expect(page.locator('#navigation-notice')).toBeVisible();await expect(page.locator('#crumb')).toHaveText('프로젝트 / 전체 구성');
  }
});

test('dark mode, region navigation and narrow evidence controls remain usable',async({page})=>{
  await open(page);await page.locator('#theme-toggle').click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.locator('#capabilities button').first().click();
  await expect(page.locator('#panel')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  for(const selector of ['#close-panel','#copy-inspection','#panel .capability-action a']){
    await expect(page.locator(selector)).toBeVisible();
    await page.locator(selector).scrollIntoViewIfNeeded();
    expect(await page.locator(selector).evaluate(n=>{const r=n.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth;})).toBe(true);
  }
});
