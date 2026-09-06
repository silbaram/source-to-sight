const {test,expect}=require('@playwright/test');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {settleCamera}=require('./playback-clock.cjs');
const root=path.resolve(__dirname,'..');
const run=path.resolve(root,process.env.S2S_EVAL_DIR||'build/eval/m2');

test.beforeEach(async({page,context})=>{
  await context.setOffline(true);
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.clock.install({time:new Date('2026-01-01T00:00:00Z')});
  await page.clock.pauseAt(new Date('2026-01-01T00:00:01Z'));
});

async function openEntry(page){
  await page.goto(pathToFileURL(path.join(run,'agent-parallel-tools.html')).href);
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('#workflow').click();
  for(let i=0;i<3;i++){await page.locator('#next').click();await settleCamera(page);}
}

const position=page=>page.evaluate(()=>{
  const canvas=document.getElementById('canvas');
  return {left:canvas.scrollLeft,top:canvas.scrollTop,pageTop:scrollY};
});
const distance=(a,b)=>Math.hypot(a.left-b.left,a.top-b.top,a.pageTop-b.pageTop);
const activeVisible=page=>page.evaluate(()=>{
  const canvas=document.getElementById('canvas').getBoundingClientRect();
  return [...document.querySelectorAll('.node.active,.flow-token')].every(n=>{
    const r=n.getBoundingClientRect();
    return r.left>=canvas.left&&r.right<=canvas.right&&r.top>=Math.max(0,canvas.top)&&r.bottom<=Math.min(innerHeight,canvas.bottom);
  });
});

async function startTravel(page){
  await openEntry(page);
  await page.locator('#play').scrollIntoViewIfNeeded();
  await page.locator('#canvas').evaluate(n=>{n.scrollLeft=0;n.scrollTop=0;});
  const start=await position(page);
  await page.locator('#play').click();
  return start;
}

test('camera passes through intermediate positions before the connection starts',async({page})=>{
  const start=await startTravel(page);
  expect(distance(start,await position(page))).toBeLessThan(2);
  await expect(page.locator('#canvas')).toHaveClass(/camera-moving/);
  await expect(page.locator('#playback-status')).toHaveText('다음 위치로 이동 중');
  expect(await page.locator('.flow-token').count()).toBe(0);
  await page.clock.runFor(100);
  const first=await position(page);
  await page.clock.runFor(100);
  const second=await position(page);
  expect(distance(first,start)).toBeGreaterThan(5);
  expect(distance(second,first)).toBeGreaterThan(5);
  expect(await page.locator('.flow-token').count()).toBe(0);
  await expect(page.locator('#step-count')).toHaveText('04 / 08');
  await settleCamera(page);
  const end=await position(page);
  expect(distance(second,start)).toBeLessThan(distance(end,start));
  expect(await activeVisible(page)).toBe(true);
  await expect(page.locator('.edge[data-id=process-batch] .flow-token')).toHaveCount(1);
  const token=await page.locator('.flow-token').getAttribute('transform');
  await page.clock.runFor(200);
  expect(await page.locator('.flow-token').getAttribute('transform')).not.toBe(token);
  expect(await position(page)).toEqual(end);
});

test('a connection already in view keeps the camera still',async({page})=>{
  await openEntry(page);
  const before=await position(page);
  await page.locator('#play').click();
  expect(await page.locator('#canvas').evaluate(n=>n.classList.contains('camera-moving'))).toBe(false);
  await page.clock.runFor(500);
  expect(await position(page)).toEqual(before);
  await expect(page.locator('.flow-token')).toHaveCount(1);
});

test('pausing during travel freezes the camera and resuming finishes the trip first',async({page})=>{
  await startTravel(page);
  await page.clock.runFor(120);
  await page.locator('#play').click();
  const paused=await position(page);
  await page.clock.runFor(2000);
  expect(await position(page)).toEqual(paused);
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#playback-status')).toHaveText('일시 정지');
  expect(await page.locator('.flow-token').count()).toBe(0);
  await page.locator('#play').click();
  await page.clock.runFor(100);
  expect(await page.locator('.flow-token').count()).toBe(0);
  await settleCamera(page);
  await page.clock.runFor(250);
  await expect(page.locator('#step-count')).toHaveText('04 / 08');
  await expect(page.locator('.flow-token')).toHaveCount(1);
});

test('rapid previous and next commands cancel old camera and playback jobs',async({page})=>{
  await startTravel(page);
  await page.clock.runFor(100);
  await page.locator('#next').click();
  await page.clock.runFor(80);
  await page.locator('#previous').click();
  await settleCamera(page);
  const stopped=await position(page);
  await page.clock.runFor(2500);
  expect(await position(page)).toEqual(stopped);
  await expect(page.locator('#step-count')).toHaveText('04 / 08');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  expect(await page.locator('.flow-token').count()).toBe(0);
  expect(await activeVisible(page)).toBe(true);
});

test('manual keyboard panning takes control during automatic travel',async({page})=>{
  await startTravel(page);
  await page.clock.runFor(100);
  await page.locator('#canvas').evaluate(n=>n.focus({preventScroll:true}));
  await page.keyboard.press('ArrowRight');
  const manual=await position(page);
  await page.clock.runFor(1500);
  expect(await position(page)).toEqual(manual);
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#canvas')).not.toHaveClass(/camera-moving/);
});

test('enabling reduced motion ends travel and keeps timed steps without motion',async({page})=>{
  await startTravel(page);
  await page.clock.runFor(100);
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(page.locator('#canvas')).not.toHaveClass(/camera-moving/);
  expect(await activeVisible(page)).toBe(true);
  expect(await page.locator('.flow-token,.node.explaining').count()).toBe(0);
  await page.clock.runFor(1600);
  await expect(page.locator('#step-count')).toHaveText('05 / 08');
  await expect(page.locator('#canvas')).not.toHaveClass(/camera-moving/);
});

test('resizing during travel replaces the old destination before playing the connection',async({page},info)=>{
  await startTravel(page);
  await page.clock.runFor(100);
  await page.evaluate(()=>{
    window.cameraResizeObserved=false;
    addEventListener('resize',()=>{window.cameraResizeObserved=true;},{once:true});
  });
  await page.setViewportSize(info.project.name==='desktop'?{width:1100,height:700}:{width:844,height:500});
  // Native resize dispatch is independent of the paused test clock. Wait for
  // that event before advancing the viewer's debounce timer.
  await expect.poll(()=>page.evaluate(()=>window.cameraResizeObserved)).toBe(true);
  await page.clock.runFor(160);
  await expect(page.locator('#canvas')).not.toHaveClass(/camera-moving/);
  const resized=await position(page);
  await page.clock.runFor(400);
  expect(await position(page)).toEqual(resized);
  expect(await activeVisible(page)).toBe(true);
  await expect(page.locator('#step-count')).toHaveText('04 / 08');
  await expect(page.locator('.edge[data-id=process-batch] .flow-token')).toHaveCount(1);
});

test('revealing worker details retains the dispatch node before camera travel',async({page})=>{
  await openEntry(page);
  const center=()=>page.locator('.node[data-id=batch]').evaluate(n=>{const r=n.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};});
  const before=await center();
  await page.locator('#next').evaluate(n=>n.click());
  const after=await center();
  expect(Math.hypot(after.x-before.x,after.y-before.y)).toBeLessThan(2);
  await settleCamera(page);
  await expect(page.locator('#mode')).toHaveValue('detail');
  expect(await activeVisible(page)).toBe(true);
  await expect(page.locator('#step-count')).toHaveText('05 / 08');
});
