const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {spawnSync}=require('node:child_process');
const root=path.resolve(__dirname,'..');
const run=path.resolve(root,process.env.S2S_RULES_EVAL_DIR||process.env.S2S_EVAL_DIR||'build/eval/m3');
const cases=JSON.parse(fs.readFileSync(path.join(root,'eval/rules-cases.json'),'utf8')).cases;
const url=id=>pathToFileURL(path.join(run,id+'.html')).href;

test.beforeEach(async({context})=>{await context.setOffline(true);});

for(const item of cases)test('M3 '+item.id+' preserves the rules, scope and both page links',async({page},info)=>{
  const errors=[],external=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))external.push(r.url());});
  const graph=JSON.parse(fs.readFileSync(path.join(root,'eval',item.candidate),'utf8'));
  const layout=JSON.parse(fs.readFileSync(path.join(root,'eval',item.layout),'utf8'));
  await page.goto(url(item.id));
  await page.evaluate(()=>document.fonts.ready);
  await expect(page.locator('html')).toHaveAttribute('data-viewer','primer');
  await expect(page.locator('h1')).toHaveText(graph.summary.title);
  await expect(page.locator('.rule-figure')).toHaveCount(layout.sections.length);
  await expect(page.locator('.withheld')).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  const metadata=await page.locator('#s2s-data').textContent();
  expect(JSON.parse(metadata).subject).toEqual(graph.subject);
  expect(metadata).not.toContain('anchorText');
  const html=await page.content();
  for(const evidence of graph.evidence)if(evidence.anchorText.trim().length>=12)expect(html).not.toContain(evidence.anchorText);
  for(const figure of layout.sections){
    const section=page.locator('#figure-'+figure.id);
    await expect(section).toHaveAttribute('data-kind',figure.kind);
    if(figure.kind==='comparison'){
      const controls=section.locator('.case-controls button');
      for(let i=0;i<figure.ruleIds.length;i++){
        await controls.nth(i).click();
        await expect(controls.nth(i)).toHaveAttribute('aria-pressed','true');
        const selected=section.locator('.rule-case:not([hidden])');
        await expect(selected).toHaveCount(1);
        const rule=graph.rules.find(r=>r.id===figure.ruleIds[i]);
        await expect(selected.locator('.rule-condition p')).toHaveText(rule.condition);
        await expect(selected.locator('.rule-outcome p')).toHaveText(rule.outcome);
        await expect(selected.locator('.rule-reason p')).toHaveText(rule.rationale);
      }
    }
    for(const stateId of figure.transitionIds||[]){
      const state=graph.stateTransitions.find(s=>s.id===stateId);
      const picture=section.locator('[data-transition-id='+stateId+']');
      await expect(picture.locator('.state-trigger')).toContainText(state.trigger);
      await expect(picture.locator('.rule-condition p')).toHaveText(state.from);
      await expect(picture.locator('.rule-outcome p')).toHaveText(state.to);
    }
    expect(await section.evaluate(n=>{
      const r=n.getBoundingClientRect();
      return [...n.querySelectorAll('.rule-condition,.rule-outcome,.case-controls button')].filter(c=>c.getClientRects().length).every(c=>{const b=c.getBoundingClientRect();return b.left>=r.left&&b.right<=r.right+1;});
    })).toBe(true);
  }
  const evidence=page.locator('.rule-case:not([hidden]) .rule-evidence').first();
  await evidence.locator('summary').click();
  await expect(evidence.locator('.rule-locations li').first()).toBeVisible();
  await page.screenshot({path:path.join(root,'build/qa/m3',info.project.name+'-'+item.id+'.png'),fullPage:true});
  await page.getByRole('link',{name:'동작과 협력으로 돌아가기 ↗'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-viewer','canvas');
  await page.locator('#links').getByRole('link',{name:'규칙과 이유 ↗'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-viewer','primer');
  expect(errors).toEqual([]);expect(external).toEqual([]);
});

test('comparison uses keyboard controls, shares dark mode and honors reduced motion',async({page})=>{
  await page.goto(url('agent-parallel-tools-rules'));
  const buttons=page.locator('.comparison').first().locator('.case-controls button');
  await buttons.nth(1).focus();
  await page.keyboard.press('Enter');
  await expect(buttons.nth(1)).toHaveAttribute('aria-pressed','true');
  await expect(page.locator('.comparison').first().locator('.rule-case:not([hidden])')).toHaveAttribute('data-rule-id','configured-budget');
  await page.locator('#theme-toggle').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.getByRole('link',{name:'동작과 협력으로 돌아가기 ↗'}).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.locator('#links').getByRole('link',{name:'규칙과 이유 ↗'}).click();
  await expect(page.locator('#theme-toggle')).toHaveAttribute('aria-checked','true');
  await page.emulateMedia({reducedMotion:'reduce'});
  expect(await page.locator('.case-controls button').first().evaluate(n=>getComputedStyle(n).transitionDuration)).toBe('0s');
  await page.locator('#theme-toggle').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','light');
});

test('denied local storage still permits theme and comparison controls',async({page})=>{
  await page.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage denied');}}));
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url('agent-parallel-tools-rules'));
  await page.locator('#theme-toggle').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
  await page.locator('.case-controls button').nth(1).click();
  await expect(page.locator('.case-controls button').nth(1)).toHaveAttribute('aria-pressed','true');
  expect(errors).toEqual([]);
});

test('all rule explanations remain readable without JavaScript',async({browser},info)=>{
  const context=await browser.newContext({javaScriptEnabled:false,viewport:info.project.use.viewport});
  try{
    await context.setOffline(true);
    const page=await context.newPage();
    await page.goto(url('agent-parallel-tools-rules'));
    await expect(page.locator('.rule-case:visible')).toHaveCount(5);
    await expect(page.locator('.case-controls:visible')).toHaveCount(0);
    await expect(page.locator('.rule-reason')).toHaveCount(5);
    expect(await page.locator('.rule-reason').allTextContents()).toHaveLength(5);
    await expect(page.getByRole('link',{name:'동작과 협력으로 돌아가기 ↗'})).toBeVisible();
  } finally {await context.close();}
});

test('authored text remains inert and missing-page commands survive denied clipboard access',async({page},info)=>{
  const item=cases.find(c=>c.profile==='ai-agent');
  const graph=JSON.parse(fs.readFileSync(path.join(root,'eval',item.candidate),'utf8'));
  const sentinel='__S2S_MAIN__ <img src=x onerror=window.injected=true>';
  graph.rules.find(r=>r.id==='effective-budget').rationale=sentinel;
  const command='$codebase-atlas 이 프로젝트의 지도를 설명해 줘';
  graph.links.atlas={url:'missing-atlas.html',generated:false,command};
  const input=info.outputPath('rules.json'),output=info.outputPath('rules.html');
  fs.mkdirSync(path.dirname(input),{recursive:true});fs.writeFileSync(input,JSON.stringify(graph));
  const rendered=spawnSync('python3',[path.join(root,'skills/visual-primer/scripts/rules.py'),'build-pair',
    '--behavior-input',path.join(root,'eval/m2/graphs',item.behaviorId+'.json'),'--input',input,
    '--layout',path.join(root,'eval',item.layout),'--source-root',path.join(root,'.cache/m1-sources',item.source),
    '--behavior-output',info.outputPath('behavior.html'),'--output',output],{encoding:'utf8'});
  expect(rendered.status,rendered.stderr).toBe(0);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(()=>{
    Object.defineProperty(navigator,'clipboard',{get(){throw new Error('Clipboard denied');}});
    document.execCommand=()=>{throw new Error('Copy denied');};
  });
  await page.goto(pathToFileURL(output).href);
  await expect(page.locator('.comparison').first().locator('.rule-reason p').first()).toHaveText(sentinel);
  await expect(page.locator('img')).toHaveCount(0);
  expect(await page.evaluate(()=>window.injected)).toBeUndefined();
  await page.locator('.copy-command').click();
  await expect(page.locator('textarea')).toHaveValue(command);
  await expect(page.locator('#announcement')).toHaveText('표시된 명령을 선택해 복사해 주세요.');
  expect(errors).toEqual([]);
});
