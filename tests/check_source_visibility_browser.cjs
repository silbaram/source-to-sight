/* Optional browser regression for explanation-only public surfaces. */
'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.argv[3]||'playwright');

async function checkPublicText(page) {
  assert.equal(await page.locator('.node-code, .code-name').count(),0,'Implementation names have no dedicated display surface');
  const surface=await page.evaluate(()=>[
    document.body.innerText,
    ...[...document.querySelectorAll('[title], [aria-label]')].map(node=>[node.title,node.getAttribute('aria-label')].join(' '))
  ].join('\n'));
  for(const privateText of ['CancellationService.check','def check(shipped):','return "manual_review"','return "cancelled"']) {
    assert(!surface.includes(privateText),'Source text must not appear in visible text, tooltips or accessible labels: '+privateText);
  }
  const data=await page.locator('#s2s-data').textContent();
  assert(!data.includes('anchorText'));
  assert(!data.includes('def check(shipped):'),'Private anchors cannot remain in the embedded payload');
}

async function checkInspector(page) {
  await page.locator('.node[data-id="node-main"]').click();
  await page.locator('#panel .node-reference:has(> .evidence-item) > summary').click();
  const evidence=page.locator('#panel .evidence-item').first();
  assert((await evidence.innerText()).includes('example.py'));
  assert((await evidence.innerText()).includes('1–4'),'Evidence retains the reviewed line range');
  await evidence.locator('button').click();
  assert.equal(await page.evaluate(()=>window.copiedLocation),'example.py:1-4','Copy action only copies the source location');
  await checkPublicText(page);
}

(async()=>{
  const root=path.resolve(process.argv[2]);
  const browser=await chromium.launch({headless:true,...(process.env.S2S_CHROMIUM_EXECUTABLE?{executablePath:process.env.S2S_CHROMIUM_EXECUTABLE}:{})});
  let checks=0;
  try {
    for(const language of ['ko','en'])for(const width of [1440,390])for(const theme of ['light','dark']) {
      const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
      await context.addInitScript(()=>Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>{window.copiedLocation=text;}}}));
      const page=await context.newPage(),errors=[],network=[];
      page.on('pageerror',error=>errors.push(error.message));
      page.on('request',request=>{if(/^https?:/.test(request.url()))network.push(request.url());});
      const open=async name=>{
        await page.goto(pathToFileURL(path.join(root,language,name+'.html')).href);
        await page.waitForSelector('html[data-ready=true]');
        if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('#theme-toggle').click();
        await checkPublicText(page);
      };
      await open('project');
      await page.locator('#entry-palette-open').click();
      await page.locator('#entry-palette-input').fill('CancellationService.check');
      assert.equal(await page.locator('#entry-palette-results button').count(),1,'An implementation identifier remains useful for locating its plain-language component');
      await checkPublicText(page);
      await page.locator('#entry-palette-results button').click();
      await page.waitForFunction(()=>!document.querySelector('.camera-moving'));
      await checkInspector(page);
      await open('behavior');
      await checkInspector(page);
      await open('logic');
      await page.locator('.authored-evidence > summary').click();
      await page.locator('.rule-evidence > summary').first().click();
      assert((await page.locator('.rule-locations').first().innerText()).includes('example.py'));
      await checkPublicText(page);
      assert.deepEqual(errors,[]);
      assert.deepEqual(network,[]);
      await context.close();
      checks++;
    }
    for(const language of ['ko','en']) {
      const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
      const page=await context.newPage();
      await page.goto(pathToFileURL(path.join(root,language,'logic.html')).href);
      await page.locator('.authored-evidence > summary').click();
      await page.locator('.rule-evidence > summary').first().click();
      assert((await page.locator('.rule-locations').first().innerText()).includes('example.py'));
      await checkPublicText(page);
      await context.close();
      checks++;
    }
    console.log(`${checks} source-visibility browser scenarios passed: search, atlas/behavior inspectors, rule evidence, location copying, tooltips and static lessons.`);
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
