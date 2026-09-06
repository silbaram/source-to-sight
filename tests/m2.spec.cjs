const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {settleCamera,reachStep}=require('./playback-clock.cjs');
const root=path.resolve(__dirname,'..');
const run=path.resolve(root,process.env.S2S_EVAL_DIR||'build/eval/m2');
const cases=JSON.parse(fs.readFileSync(path.join(root,'eval/cases.json'),'utf8')).cases.filter(c=>c.variant==='complex');
const url=id=>pathToFileURL(path.join(run,id+'.html')).href;

test.beforeEach(async({context,page})=>{
  await context.setOffline(true);
  await page.emulateMedia({reducedMotion:'no-preference'});
  await page.clock.install({time:new Date('2026-01-01T00:00:00Z')});
  await page.clock.pauseAt(new Date('2026-01-01T00:00:01Z'));
});

const branchLabels={normal:'진행',alternate:'다른 경로',error:'오류',retry:'재시도',stop:'종료'};
for(const item of cases)test('M2 '+item.id+' preserves every path, guard and execution label',async({page})=>{
  const graph=JSON.parse(fs.readFileSync(path.join(root,'eval',item.candidate),'utf8'));
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(url(item.id));
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('#workflow').click();
  for(let i=0;i<graph.scenarios.length;i++){
    await page.locator('#scenario').selectOption(String(i));
    const scenario=graph.scenarios[i];
    for(let j=0;j<scenario.steps.length;j++){
      const step=scenario.steps[j];
      await expect(page.locator('#caption')).toContainText(step.caption);
      await expect(page.locator('#step-context')).toContainText(branchLabels[step.branch]);
      if(step.condition){
        await expect(page.locator('#step-condition')).toBeVisible();
        await expect(page.locator('#step-condition')).toContainText(step.condition);
      } else await expect(page.locator('#step-condition')).toBeHidden();
      if(step.execution==='parallel')await expect(page.locator('#step-context')).toContainText('병렬 구간 · 내부 순서 미정');
      if(step.execution==='unordered')await expect(page.locator('#step-context')).toContainText('대상 순서 미정');
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
      if(j<scenario.steps.length-1)await page.locator('#next').click();
    }
    await expect(page.locator('#next')).toBeDisabled();
  }
  expect(errors).toEqual([]);
});

test('explicit parallel entry, worker calls and result recording keep their checked direction',async({page})=>{
  await page.goto(url('agent-parallel-tools'));
  await page.locator('#workflow').click();
  for(let i=0;i<3;i++)await page.locator('#next').click();
  const transfers=['process-batch','worker-call','call-tool','save-observations'];
  for(let i=3;i<=6;i++){
    await page.locator('#play').click();
    await settleCamera(page);
    await page.clock.runFor(350);
    await expect(page.locator('.flow-token')).toHaveCount(1);
    await expect(page.locator('.edge[data-id='+transfers[i-3]+'] .flow-token')).toHaveCount(1);
    if(i===3){
      await expect(page.locator('#flow-transfer')).toContainText('모델 요청과 도구 처리');
      await expect(page.locator('#flow-transfer')).toContainText('도구 묶음 제출과 수집');
      await expect(page.locator('#step-context')).toContainText('병렬 구간 · 내부 순서 미정');
    }
    if(i===4){
      await expect(page.locator('#flow-transfer')).toContainText('각 작업에서 도구 호출');
      await expect(page.locator('#mode')).toHaveValue('detail');
      await expect(page.locator('.node[data-id=execute]')).toBeVisible();
    }
    if(i<6)await page.locator('#next').click();
  }
  await page.locator('#play').click();
  await page.locator('#scenario').selectOption('0');
  await page.locator('#play').click();
  await reachStep(page,2,8);
  await page.clock.runFor(200);
  await expect(page.locator('.flow-token')).toHaveCount(1);
});

test('unspecified recipient order stays unconnected while an explicit await follows its checked dispatch',async({page})=>{
  await page.goto(url('event-async-lifecycle'));
  await page.locator('#workflow').click();
  for(let i=0;i<2;i++)await page.locator('#next').click();
  await page.locator('#play').click();
  await settleCamera(page);
  await page.clock.runFor(350);
  expect(await page.locator('.flow-token').count()).toBe(0); // Recipient selection does not invent a delivery order.
  await expect(page.locator('#step-count')).toHaveText('03 / 06');
  await page.locator('#next').click();
  await expect(page.locator('#caption')).toContainText('하나씩 await');
  await expect(page.locator('#step-context')).toContainText('대상 순서 미정');
  await page.locator('#play').click();
  await settleCamera(page);
  await page.clock.runFor(350);
  await expect(page.locator('.edge[data-id=await-receiver] .flow-token')).toHaveCount(1);
  await page.emulateMedia({reducedMotion:'reduce'});
  await expect(page.locator('.flow-token')).toHaveCount(0);
  await expect(page.locator('#step-count')).toHaveText('04 / 06');
  await expect(page.locator('#step-condition')).toContainText('비동기 함수');
});

const progressFraction=page=>page.locator('#playback-fill').evaluate(n=>new DOMMatrix(getComputedStyle(n).transform).a);

test('continuous playback remains visible and advances through every parallel walkthrough step',async({page})=>{
  await page.goto(url('agent-parallel-tools'));
  await page.evaluate(()=>document.fonts.ready);
  await page.locator('#workflow').click();
  await page.locator('#play').click();
  const transfers=[null,'start','decide','process-batch','worker-call','call-tool','save-observations','next-decision'];
  for(let i=0;i<8;i++){
    await reachStep(page,i+1,8);
    await page.clock.runFor(250);
    await expect(page.locator('#step-count')).toHaveText(String(i+1).padStart(2,'0')+' / 08');
    await expect(page.locator('#play')).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.node[aria-current=step]')).toHaveCount(1);
    const earlier=await progressFraction(page);
    const position=transfers[i] ? await page.locator('.flow-token').getAttribute('transform') : null;
    await page.clock.runFor(300);
    expect(await progressFraction(page)).toBeGreaterThan(earlier+.015);
    if(transfers[i]){
      await expect(page.locator('.flow-token')).toHaveCount(1);
      await expect(page.locator('.edge[data-id='+transfers[i]+'] .flow-token')).toHaveCount(1);
      expect(await page.locator('.flow-token').getAttribute('transform')).not.toBe(position);
      await expect(page.locator('.node.explaining')).toHaveCount(0);
    } else {
      await expect(page.locator('.flow-token')).toHaveCount(0);
      expect(await page.locator('.node.explaining').count()).toBeGreaterThan(0);
      expect(await page.locator('.node.explaining').first().evaluate(n=>getComputedStyle(n,'::after').animationName)).toBe('step-attention');
    }
    if(i>=3&&i<=5)await expect(page.locator('#playback-status')).toHaveText('병렬 구간 설명 중');
    const visible=await page.evaluate(()=>{
      const canvas=document.querySelector('#canvas').getBoundingClientRect();
      return canvas.top>=-1&&canvas.bottom<=innerHeight+1&&[...document.querySelectorAll('.node.active,.flow-token')].every(n=>{
        const r=n.getBoundingClientRect();
        return r.top>=Math.max(0,canvas.top)&&r.bottom<=Math.min(innerHeight,canvas.bottom)&&r.left>=canvas.left&&r.right<=canvas.right;
      });
    });
    expect(visible).toBe(true);
    await page.clock.runFor(950);
  }
  await expect(page.locator('#playback-status')).toHaveText('설명 재생 완료');
  await expect(page.locator('#play')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('.flow-token,.node.explaining')).toHaveCount(0);
  expect(await progressFraction(page)).toBeCloseTo(1);
});

test('parallel playback feedback stops on manual navigation and resets for a new scenario',async({page})=>{
  await page.goto(url('agent-parallel-tools'));
  await page.locator('#workflow').click();
  await page.locator('#scenario').selectOption('1'); // Node-only group failure: no specific handoff is claimed.
  await page.locator('#play').click();
  await settleCamera(page);
  await page.clock.runFor(400);
  await expect(page.locator('.node.explaining')).toHaveCount(1);
  await page.locator('.node[data-id=batch]').click();
  await expect(page.locator('#playback-status')).toHaveText('일시 정지');
  await expect(page.locator('.node.explaining')).toHaveCount(0);
  const paused=await progressFraction(page);
  await page.clock.runFor(2000);
  expect(await progressFraction(page)).toBeCloseTo(paused);
  await page.locator('#close-panel').click();
  await page.locator('#scenario').selectOption('2');
  await expect(page.locator('#playback-status')).toHaveText('자동 재생 준비');
  await expect(page.locator('#playback-progress')).toHaveAttribute('aria-valuemax','2');
  expect(await progressFraction(page)).toBe(0);
});

test('reduced motion retains discrete progress without parallel pulses',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto(url('agent-parallel-tools'));
  await page.locator('#workflow').click();
  for(let i=0;i<3;i++)await page.locator('#next').click();
  await page.locator('#play').click();
  const first=await progressFraction(page);
  await page.clock.runFor(500);
  expect(await progressFraction(page)).toBe(first);
  await expect(page.locator('.flow-token,.node.explaining')).toHaveCount(0);
  await expect(page.locator('#playback-status')).toHaveText('병렬 구간 설명 중');
  await page.clock.runFor(1100);
  expect(await progressFraction(page)).toBeGreaterThan(first);
  await expect(page.locator('#playback-progress')).toHaveAttribute('aria-valuenow','5');
});
