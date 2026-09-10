/* Diagram → data flow → node rule picture → selected position, offline. */
'use strict';
const assert=require('node:assert/strict');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.argv[3]||'playwright');

(async()=>{
  const browser=await chromium.launch({headless:true});
  let checks=0;
  try {
    for(const language of ['ko','en'])for(const width of [1440,390])for(const dark of [false,true]) {
      const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
      const page=await context.newPage(),errors=[],external=[];
      page.on('pageerror',error=>errors.push(error.message));
      page.on('request',request=>{if(/^https?:/.test(request.url()))external.push(request.url());});
      const root=path.resolve(process.argv[2],language);
      const url=file=>pathToFileURL(path.join(root,file)).href;
      const ready=()=>page.waitForSelector('html[data-ready="true"]');
      const noOverflow=async()=>assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.goto(url('journey/project.html'));await ready();
      if(dark)await page.locator('#theme-toggle').click();
      assert.equal(await page.locator('#entry-catalog').evaluate(node=>node.open),false,'The first picture precedes the catalog');
      assert(await page.locator('#entry-map').isVisible());
      assert.equal(await page.locator('#entry-map .code-name,#entry-map .location').count(),0,'Implementation metadata stays on demand');
      const mapData=await page.locator('#s2s-data').evaluate(node=>JSON.parse(node.textContent));
      const feature=mapData.subjects[0];
      assert.equal(await page.locator('#entry-map [data-edge-id]').count(),mapData.edges.length,'Map connections come from recorded edges');
      const entry=page.locator('.atlas-map-node[data-feature-id="'+feature.id+'"]');
      assert.equal(await entry.evaluate(node=>node.tagName),'A','Generated single capability opens directly');
      if(width<720)assert(await page.locator('#entry-map').evaluate(node=>node.scrollWidth<=node.clientWidth+1),'Narrow connection view remains readable without horizontal panning');
      await noOverflow();
      await entry.focus();await page.keyboard.press('Enter');await ready();
      assert(page.url().includes('/journey/behavior.html'));
      const state=new URLSearchParams(new URL(page.url()).search).get('s2s-atlas');
      assert.equal(new URLSearchParams(state.slice(1)).get('feature'),feature.id);
      await page.locator('.node[data-id="node-main"]').click();
      assert.equal(await page.locator('.node-data-item strong').textContent(),language==='ko'?'판단 결과':'Decision result');
      assert(!(await page.locator('.node-rules').textContent()).includes(language==='ko'?'별도 처리의 합성 규칙':'Synthetic rule for the separate step'));
      assert.equal(await page.locator('.node-reference').first().evaluate(node=>node.open),false);
      const lesson=page.locator('.node-rules a');
      await lesson.focus();await page.keyboard.press('Enter');await ready();
      assert.equal(new URL(page.url()).searchParams.get('s2s-node'),'node-main');
      assert(await page.locator('#figure-cancellation').isVisible());
      assert(!(await page.locator('#figure-separate').isVisible()),'Another node must not leak into this lesson');
      assert(await page.locator('.node-lesson-context').isVisible());
      await page.locator('.node-lesson-context button').click();
      assert(await page.locator('#figure-separate').isVisible(),'The full lesson remains reachable');
      await noOverflow();
      await page.locator('.primer-intro > .links a[data-layer="behavior"]').click();await ready();
      assert.equal(await page.locator('.node.selected').getAttribute('data-id'),'node-main');
      assert(await page.locator('#panel').evaluate(node=>node.classList.contains('open')));
      await page.locator('#links a').filter({hasText:language==='ko'?'프로젝트 지도':'Project map'}).click();await ready();
      const returned=page.locator('.atlas-map-node.is-selected');
      assert.equal(await returned.getAttribute('data-feature-id'),feature.id);
      assert(await returned.evaluate(node=>node===document.activeElement),'Return restores keyboard focus');
      const bounds=await returned.boundingBox();assert(bounds.y>=0&&bounds.y+bounds.height<=1001);
      await page.goto(url('entry-missing.html'));await ready();
      const missing=page.locator('.atlas-map-node[data-feature-id]');
      assert.equal(await missing.evaluate(node=>node.tagName),'BUTTON');
      await missing.click();assert(await page.locator('#entry-context').isVisible(),'Missing details expose scoped context');
      await page.keyboard.press('Escape');
      await noOverflow();
      assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
      await context.close();checks++;
    }
  } finally {await browser.close();}
  console.log(checks+' learning journeys passed: diagram, labeled data, isolated node lessons, context return, missing detail, themes and offline use.');
})().catch(error=>{console.error(error);process.exitCode=1;});
