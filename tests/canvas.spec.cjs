const {test,expect}=require('@playwright/test');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const url=name=>pathToFileURL(path.join(root,'build/examples',name+'.html')).href;
const evidenceUrl=pathToFileURL(path.join(root,'build/m1/web-dispatch.html')).href;
test.beforeEach(async({context})=>context.setOffline(true));

async function expectContainedInspector(page) {
  await expect(page.locator('#canvas')).not.toHaveClass(/camera-moving/);
  await expect.poll(()=>page.evaluate(()=>{
    const panel=document.getElementById('panel'),p=panel.getBoundingClientRect();
    const c=document.getElementById('canvas').getBoundingClientRect();
    const mobile=matchMedia('(max-width:900px)').matches;
    const controls=['close-panel','focus-related'].every(id=>{
      const button=document.getElementById(id),r=button.getBoundingClientRect();
      return r.top>=p.top&&r.bottom<=p.bottom&&r.left>=p.left&&r.right<=p.right&&
        document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)?.closest('button')===button;
    });
    return {insideWindow:p.top>=0&&p.bottom<=innerHeight+.5&&p.left>=0&&p.right<=innerWidth,
      insideMap:mobile||(p.top>=c.top&&p.bottom<=c.bottom&&p.left>=c.left&&p.right<=c.right),controls};
  })).toEqual({insideWindow:true,insideMap:true,controls:true});
}

test('long evidence scrolls inside the panel while close and focus remain reachable',async({page},info)=>{
  await page.setViewportSize(info.project.name==='desktop'?{width:1280,height:650}:{width:390,height:844});
  await page.goto(evidenceUrl);
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('.node[data-id=tree]').click();
  await expectContainedInspector(page);
  const body=page.locator('#panel-body');
  expect(await body.evaluate(n=>n.scrollHeight>n.clientHeight)).toBe(true);
  const pageTop=await page.evaluate(()=>scrollY);
  await body.hover();
  await page.mouse.wheel(0,1800);
  await expect.poll(()=>body.evaluate(n=>n.scrollTop+n.clientHeight>=n.scrollHeight-2)).toBe(true);
  expect(await page.evaluate(()=>scrollY)).toBe(pageTop);
  await expect(page.locator('#panel .evidence-item button').last()).toBeInViewport({ratio:1});
  await expectContainedInspector(page);
  await page.locator('#focus-related').click();
  await expect(page.locator('#focus-related')).toHaveAttribute('aria-pressed','true');
  await page.locator('#search').fill('등록된 처리 함수');
  await page.locator('#results button').click();
  expect(await body.evaluate(n=>n.scrollTop)).toBe(0);
  await expect(page.locator('#panel-title')).toHaveText('등록된 처리 함수');
  await expectContainedInspector(page);
  await page.locator('#close-panel').click();
  await expect(page.locator('#panel')).toBeHidden();
});

test('open inspector adapts to page scroll and short or rotated viewports',async({page},info)=>{
  await page.goto(evidenceUrl);
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('.node[data-id=tree]').click();
  const sizes=info.project.name==='desktop'?
    [{width:1000,height:500},{width:1327,height:921},{width:390,height:844},{width:1280,height:650}]:
    [{width:390,height:600},{width:844,height:390},{width:1000,height:500},{width:390,height:844}];
  for(const size of sizes){
    await page.setViewportSize(size);
    await expectContainedInspector(page);
    await page.evaluate(()=>window.scrollBy(0,60));
    await expectContainedInspector(page);
  }
  await page.screenshot({path:path.join(root,'build/qa',info.project.name+'-bounded-panel.png')});
});

test('generated canvas starts with a map and opens real evidence on demand',async({page})=>{
  await page.goto(url('agent-run'));
  await expect(page.locator('html')).toHaveAttribute('data-viewer','canvas');
  await expect(page.locator('#panel')).toBeHidden();
  await expect(page.locator('#player')).toBeHidden();
  await expect(page.locator('#structure')).toHaveAttribute('aria-pressed','true');
  const data=JSON.parse(await page.locator('#s2s-data').textContent());
  const detail=data.nodes.find(n=>n.importance==='detail');
  await page.locator('#search').fill(detail.label);
  await page.locator('#results').getByRole('button',{name:detail.label,exact:true}).click();
  await expect(page.locator('#mode')).toHaveValue('detail');
  await expect(page.locator('#panel-title')).toHaveText(detail.label);
  await expect(page.locator('#panel .location').first()).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#panel')).toBeHidden();
  await page.locator('#search').fill('no-such-component-xyz');
  await expect(page.locator('#results')).toContainText('일치하는 구성 요소가 없습니다.');
  await page.locator('#search').clear();
  await expect(page.locator('#results')).toBeHidden();
});

test('theme works in generated files and survives reload without resetting exploration',async({page},info)=>{
  await page.goto(url('agent-run'));
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
  await page.locator('#workflow').click();await page.locator('#next').click();
  const caption=await page.locator('#caption').textContent();
  await page.locator('#theme-toggle').click();
  await expect(page.locator('#theme-toggle')).toHaveAttribute('aria-checked','true');
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await expect(page.locator('#caption')).toHaveText(caption);
  // The SVG markers and paths use the same semantic palette in both themes.
  expect(await page.locator('#arrow-normal path').evaluate(n=>getComputedStyle(n).fill)).toBe('rgb(149, 184, 209)');
  await page.screenshot({path:path.join(root,'build/qa',info.project.name+'-canvas-dark.png'),fullPage:true});
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.locator('#theme-toggle').click();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
});

test('denied storage still allows theme changes and graph exploration',async({page})=>{
  await page.addInitScript(()=>{
    Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Denied','SecurityError');}});
  });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url('utility-minimum'));
  await page.locator('#theme-toggle').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.locator('.node').click();await expect(page.locator('#panel-title')).toHaveText('서식 표시 제거');
  expect(errors).toEqual([]);
});

test('focus and back restore view, walkthrough, detail level and camera',async({page})=>{
  await page.goto(url('agent-run'));
  await page.locator('#flows button').first().click();
  await page.locator('#next').click();
  await page.locator('#search').fill('요청 기록');
  await page.locator('#results button').click();
  const capture=()=>page.evaluate(()=>({
    zoom:document.getElementById('zoom-level').textContent,
    left:document.getElementById('canvas').scrollLeft,top:document.getElementById('canvas').scrollTop,
    mode:document.getElementById('mode').value,step:document.getElementById('step-count').textContent,
    flow:document.getElementById('workflow').getAttribute('aria-pressed'),
    selected:document.querySelector('.node.selected')?.dataset.id
  }));
  const before=await capture();
  await page.locator('#focus-related').click();
  await expect(page.locator('.node.dim').first()).toBeAttached();
  await expect(page.locator('#back')).toBeVisible();
  await page.locator('#zoom-in').click();await page.locator('#structure').click();
  await page.locator('#mode').selectOption('detail');
  await page.locator('#back').click();
  expect(await capture()).toEqual(before);
  await expect(page.locator('.node.dim')).toHaveCount(0);
  await expect(page.locator('#back')).toBeHidden();
});

for (const route of ['canvas','search','list','keyboard']) test('selecting another node via '+route+' clears the old connection focus',async({page},info)=>{
  await page.goto(url('agent-run'));
  // A is adjacent only to the loop. B is outside A's focused neighborhood.
  await page.locator('.node[data-id=request]').click();
  await page.locator('#focus-related').click();
  await expect(page.locator('.node[data-id=step]')).toHaveClass(/\bdim\b/);
  await expect(page.locator('#crumb')).toHaveText('연결 강조 중 · 요청 기록');
  if(route==='canvas')await page.locator('.node[data-id=step]').click();
  if(route==='search'){
    await page.locator('#search').fill('다음 행동 요청');
    await page.locator('#results button').click();
  }
  if(route==='list'){
    await page.locator('#list-title').click();
    await page.locator('#component-list button[data-node-id=step]').click();
  }
  if(route==='keyboard'){
    await page.locator('.node[data-id=step]').focus();
    await page.keyboard.press('Enter');
  }
  await expect(page.locator('#panel-title')).toHaveText('다음 행동 요청');
  await expect(page.locator('.node.selected')).toHaveCount(1);
  await expect(page.locator('.node[data-id=step]')).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.node[data-id=request]')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('.node.dim,.edge.dim')).toHaveCount(0);
  await expect(page.locator('.node[data-id=step]')).toHaveCSS('opacity','1');
  await expect(page.locator('#crumb')).toHaveText('설명 범위 / 구성');
  await expect(page.locator('#focus-related')).toHaveText('연결된 부분에 집중');
  await expect(page.locator('#focus-related')).toHaveAttribute('aria-pressed','false');
  if(route==='canvas'){
    await page.screenshot({path:path.join(root,'build/qa',info.project.name+'-new-node-selection.png'),fullPage:true});
    // A second focus uses B, never the previously selected A.
    await page.locator('#focus-related').click();
    await expect(page.locator('#crumb')).toHaveText('연결 강조 중 · 다음 행동 요청');
    await expect(page.locator('.node[data-id=model]')).not.toHaveClass(/\bdim\b/);
    await expect(page.locator('.node[data-id=request]')).toHaveClass(/\bdim\b/);
  }
});

test('the same focused node offers a clear action without moving the camera',async({page})=>{
  await page.goto(url('agent-run'));
  const node=page.locator('.node[data-id=request]');
  await node.click();await page.locator('#focus-related').click();
  await node.click();
  await expect(page.locator('.node.dim').first()).toBeAttached();
  await expect(page.locator('#focus-related')).toHaveText('연결 강조 해제');
  await expect(page.locator('#focus-related')).toHaveAttribute('aria-pressed','true');
  const camera=()=>page.locator('#canvas').evaluate(n=>[n.scrollLeft,n.scrollTop,document.getElementById('zoom-level').textContent]);
  const before=await camera();
  await page.locator('#focus-related').click();
  expect(await camera()).toEqual(before);
  await expect(page.locator('.node.dim,.edge.dim')).toHaveCount(0);
  await expect(node).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('#panel')).toBeVisible();
  await expect(page.locator('#focus-related')).toHaveAttribute('aria-pressed','false');
});

test('selecting an edge and advancing a walkthrough also clear stale focus',async({page})=>{
  await page.goto(url('agent-run'));
  const focusRequest=async()=>{
    await page.locator('#search').fill('요청 기록');
    await page.locator('#results button').click();
    await page.locator('#focus-related').click();
  };
  await focusRequest();
  const edge=page.locator('.edge[data-id=step-model]');
  await expect(edge).toHaveClass(/\bdim\b/);
  await edge.focus();await page.keyboard.press('Enter');
  await expect(page.locator('.node.dim,.edge.dim')).toHaveCount(0);
  await expect(edge).toHaveClass(/\bactive\b/);
  await expect(page.locator('#focus-related')).toBeHidden();
  await page.keyboard.press('Escape');
  await focusRequest();await page.locator('#workflow').click();
  await expect(page.locator('.node.dim,.edge.dim')).toHaveCount(0);
  await focusRequest();await page.locator('#next').click();
  await expect(page.locator('.node.dim,.edge.dim')).toHaveCount(0);
  await expect(page.locator('#step-count')).toHaveText('02 / 06');
});

for (const route of ['canvas','search']) test('selected node stays visible beside the panel via '+route,async({page},info)=>{
  await page.goto(url('agent-run'));
  await page.evaluate(()=>document.fonts.ready);
  if(route==='search'){
    await page.locator('#search').fill('등록된 도구·에이전트');
    await page.locator('#results button').click();
  }else await page.locator('.node[data-id=tool]').click();
  await expect(page.locator('#panel-title')).toHaveText('등록된 도구·에이전트');
  const visible=()=>page.evaluate(()=>{
    const node=document.querySelector('.node.selected'),n=node.getBoundingClientRect();
    const c=document.getElementById('canvas').getBoundingClientRect(),p=document.getElementById('panel').getBoundingClientRect();
    const covered=Math.min(n.right,p.right)>Math.max(n.left,p.left)&&Math.min(n.bottom,p.bottom)>Math.max(n.top,p.top);
    return {insideCanvas:n.left>=c.left-1&&n.right<=c.right+1&&n.top>=c.top-1&&n.bottom<=c.bottom+1,
      insideWindow:n.left>=0&&n.right<=innerWidth&&n.top>=0&&n.bottom<=innerHeight,
      covered,hit:document.elementFromPoint(n.x+n.width/2,n.y+n.height/2)?.closest('.node')?.dataset.id};
  });
  const expected={insideCanvas:true,insideWindow:true,covered:false,hit:'tool'};
  await expect.poll(visible).toEqual(expected);
  // Zooming must not put the selected node back underneath the open panel.
  await page.locator('#zoom-in').click();
  await expect.poll(visible).toEqual(expected);
  await page.screenshot({path:path.join(root,'build/qa',info.project.name+'-visible-selection-'+route+'.png')});
});

for(const [fixture,id,title] of [['agent-run','loop','계속할지 확인'],['utility-minimum','strip','서식 표시 제거']])
test('structure detail switch preserves selection and panel in '+fixture,async({page})=>{
  await page.goto(url(fixture));
  await page.locator('.node[data-id='+id+']').click();
  const panel=await page.locator('#panel-body').textContent();
  for(const mode of ['detail','core']){
    await page.locator('#mode').selectOption(mode);
    await expect(page.locator('#structure')).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.node.selected')).toHaveAttribute('data-id',id);
    await expect(page.locator('#panel-title')).toHaveText(title);
    await expect(page.locator('#panel-body')).toHaveText(panel);
    await expect(page.locator('#panel')).toBeVisible();
  }
});

test('hiding a selected detail node clears its panel and connection focus',async({page})=>{
  await page.goto(url('agent-run'));
  await page.locator('#search').fill('실행 기록');
  await page.locator('#results button').click();
  await page.locator('#focus-related').click();
  await expect(page.locator('#crumb')).toHaveText('연결 강조 중 · 실행 기록');
  await page.locator('#mode').selectOption('core');
  await expect(page.locator('.node[data-id=memory]')).toHaveCount(0);
  await expect(page.locator('.node.selected,.node.dim,.edge.dim')).toHaveCount(0);
  await expect(page.locator('#panel')).toBeHidden();
  await expect(page.locator('#crumb')).toHaveText('설명 범위 / 구성');
});

test('structure detail switch also preserves an edge selection',async({page})=>{
  await page.goto(url('agent-run'));
  const edge=page.locator('.edge[data-id=step-model]');
  await edge.focus();await page.keyboard.press('Enter');
  const panel=await page.locator('#panel-body').textContent();
  await page.locator('#mode').selectOption('detail');
  await expect(page.locator('#panel-body')).toHaveText(panel);
  await expect(page.locator('.edge.active')).toHaveCount(1);
  await expect(edge).toHaveClass(/\bactive\b/);
});

test('zoom, pan and fit retain attached arrows and keyboard access',async({page})=>{
  await page.goto(url('agent-run'));
  for(let i=0;i<5;i++)await page.locator('#zoom-in').click();
  await page.locator('#canvas').focus();await page.keyboard.press('ArrowRight');await page.keyboard.press('ArrowDown');
  expect(await page.locator('#canvas').evaluate(n=>n.scrollLeft+n.scrollTop)).toBeGreaterThan(0);
  const detached=await page.evaluate(()=>{
    const data=JSON.parse(document.getElementById('s2s-data').textContent),bad=[];
    for(const group of document.querySelectorAll('.edge')){
      const edge=data.edges.find(e=>e.id===group.dataset.id),route=group.querySelector('.edge-path');
      for(const [id,d] of [[edge.from,0],[edge.to,route.getTotalLength()]]){
        const p=route.getPointAtLength(d).matrixTransform(route.getScreenCTM());
        const r=[...document.querySelectorAll('.node')].find(n=>n.dataset.id===id).getBoundingClientRect();
        if(p.x<r.left-3||p.x>r.right+3||p.y<r.top-3||p.y>r.bottom+3||Math.min(Math.abs(p.x-r.left),Math.abs(p.x-r.right),Math.abs(p.y-r.top),Math.abs(p.y-r.bottom))>3)bad.push([edge.id,id]);
      }
    }return bad;
  });
  expect(detached).toEqual([]);
  await page.keyboard.press('0');
  // The scroll surface includes panning room; Fit must contain the actual graph.
  expect(await page.locator('#canvas').evaluate(n=>{
    const frame=n.getBoundingClientRect(),graph=document.getElementById('stage').getBoundingClientRect();
    return graph.left>=frame.left-1&&graph.right<=frame.right+1&&graph.top>=frame.top-1&&graph.bottom<=frame.bottom+1;
  })).toBe(true);
  await expect(page.locator('#mini .viewport')).toHaveCount(1);
  await page.locator('#list-title').click();
  await page.locator('#component-list button').last().focus();await page.keyboard.press('Enter');
  await expect(page.locator('#panel')).toBeVisible();
});
