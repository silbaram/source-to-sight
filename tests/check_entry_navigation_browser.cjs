/* Content-based project navigation; no fixed section count or fabricated flow. */
'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.argv[3]||'playwright');

(async()=>{
  const root=path.resolve(process.argv[2]);
  const browser=await chromium.launch({headless:true});let checks=0;
  try {
    for(const language of ['ko','en'])for(const width of [1440,390])for(const dark of [false,true]) {
      const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
      const page=await context.newPage(),errors=[],requests=[];
      page.on('pageerror',error=>errors.push(error.message));
      page.on('request',request=>{if(/^https?:/.test(request.url()))requests.push(request.url());});
      const ready=()=>page.waitForSelector('html[data-ready="true"]');
      const url=name=>pathToFileURL(path.join(root,language,name+'.html')).href;
      const navigate=async id=>{
        // Select by the recorded target rather than trusting a possibly repeated title.
        const target=page.locator('#entry-toc button').filter({visible:true});
        const index=await target.evaluateAll((nodes,id)=>nodes.findIndex(node=>node.dataset.tocTarget===id),id);
        assert(index>=0,'A navigation item exists for '+id);
        await target.nth(index).focus();await page.keyboard.press('Enter');
        await page.waitForFunction(id=>document.activeElement===document.getElementById(id),id);
        assert(await page.locator('[id]').evaluateAll((nodes,id)=>{
          const rect=nodes.find(node=>node.id===id).getBoundingClientRect();
          return rect.bottom>0&&rect.top<innerHeight;
        },id),'Keyboard navigation brings the heading into view');
        assert(!(await page.locator('#navigation-notice').isVisible()),'Section navigation preserves the URL contract');
      };
      const tocTargets=()=>page.locator('#entry-toc button').evaluateAll(nodes=>nodes.map(node=>node.dataset.tocTarget));
      const overflow=async()=>assert(!(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1)),language+' '+width+' overflow');

      await page.goto(url('features/no-project-context'));await ready();
      if(dark)await page.locator('#theme-toggle').click();
      const data=await page.locator('#s2s-data').evaluate(node=>JSON.parse(node.textContent));
      const original=JSON.stringify(data);
      assert(await page.locator('.coverage-label').isVisible());
      assert(await page.locator('#entry-gaps-body').isVisible());
      assert(await page.locator('#entry-files').isVisible());
      assert(!(await page.locator('#entry-recorded-flow').isVisible()),'Child flows are not promoted to a project-wide sequence');
      assert(!(await page.locator('#entry-recorded-cautions').isVisible()),'Child rules are not promoted to project-wide claims');
      const targets=await tocTargets();
      assert(targets.includes('title')&&targets.includes('entry-title')&&targets.includes('entry-capabilities-title'));
      assert.equal(targets.filter(id=>id.startsWith('entry-feature-heading-')).length,data.subjects.length);
      assert(!targets.includes('entry-recorded-flow-title')&&!targets.includes('entry-recorded-cautions-title'));
      for(const subject of data.subjects)assert(targets.includes('entry-feature-heading-'+subject.id));
      assert.notEqual(targets.length,7,'Navigation follows this fixture content rather than a seven-section template');
      await overflow();
      for(const id of ['entry-title','entry-feature-heading-'+data.subjects.at(-1).id,'entry-gaps-title'])await navigate(id);
      await page.waitForFunction(()=>document.querySelector('#entry-toc button[aria-current="location"]')?.dataset.tocTarget==='entry-gaps-title');
      assert.equal(await page.locator('#entry-toc [aria-current]').count(),1);
      if(width>1100)assert(await page.locator('#entry-toc').evaluate(node=>Math.abs(node.getBoundingClientRect().top-24)<2),'Desktop contents stay beside the document');
      await navigate('entry-feature-heading-'+data.subjects[0].id);
      assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('feature'),data.subjects[0].id);
      await page.reload();await ready();
      assert.equal(await page.locator('.feature-heading.is-selected').getAttribute('data-feature-id'),data.subjects[0].id);
      assert(await page.locator('#entry-toc').isVisible());
      // Close a reference deliberately: navigating to it must reopen it while
      // keeping the native summary in the keyboard tab order.
      await page.locator('#entry-files-section').evaluate(node=>{node.open=false;});
      await navigate('entry-files-title');
      assert(await page.locator('#entry-files').isVisible());
      assert.equal(await page.locator('#entry-files-title').evaluate(node=>node.tabIndex),0);
      await navigate('title');
      await page.waitForFunction(()=>document.querySelector('#entry-toc button[aria-current="location"]')?.dataset.tocTarget==='title');
      assert.equal(await page.locator('#s2s-data').evaluate(node=>JSON.stringify(JSON.parse(node.textContent))),original,'Navigation never edits reviewed data');
      await overflow();
      if(language==='ko')await page.screenshot({path:path.join(root,'entry-navigation-'+width+'-'+(dark?'dark':'light')+'.png')});

      await page.goto(url('project'));await ready();
      const recorded=await page.locator('#s2s-data').evaluate(node=>JSON.parse(node.textContent));
      assert((await tocTargets()).includes('entry-recorded-flow-title'));
      assert((await tocTargets()).includes('entry-recorded-cautions-title'));
      assert.deepEqual(await page.locator('#entry-recorded-flow .entry-flow-step').evaluateAll(nodes=>nodes.map(node=>node.dataset.stepId)),recorded.scenarios[0].steps.map(step=>step.id));
      assert.equal(await page.locator('#entry-recorded-cautions .entry-caution').count(),recorded.rules.length);
      for(const rule of recorded.rules) {
        const text=await page.locator('#entry-recorded-cautions').innerText();
        assert(text.includes(rule.condition)&&text.includes(rule.outcome),'Rule conditions and outcomes are visible without expanding evidence');
        for(const exception of rule.exceptions||[])assert(text.includes(exception));
      }
      await navigate('entry-recorded-flow-title');await navigate('entry-recorded-cautions-title');
      await page.locator('#entry-recorded-flow .entry-flow-button').first().click();
      assert(await page.locator('#workspace').isVisible(),'Recorded flow steps reach the existing diagram');
      const first=recorded.scenarios[0].steps[0];
      const owner=first.nodeId||recorded.edges.find(edge=>edge.id===first.edgeId).to;
      assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('node'),owner);
      await page.locator('#entry-home').click();
      assert(await page.locator('#entry-toc').isVisible());
      await overflow();

      await page.goto(url('journey/project'));await ready();
      const rootHeadings=await tocTargets();
      await page.locator('.atlas-area-open').first().click();
      const scoped=await tocTargets();
      assert(!scoped.includes('title'),'Area navigation removes the project introduction from local contents');
      assert.notDeepEqual(scoped,rootHeadings,'Contents update to the current area');
      assert(await page.locator('#entry-toc button').evaluateAll(nodes=>nodes.every(node=>document.getElementById(node.dataset.tocTarget))),'No links to removed headings survive an area change');
      await navigate('entry-title');
      await page.locator('#entry-area-breadcrumb button').first().click();
      assert.deepEqual(await tocTargets(),rootHeadings,'Returning to the project restores its contents');

      await page.goto(url('entry-narrative-empty'));await ready();
      assert(!(await page.locator('#entry-recorded-flow').isVisible()));
      assert(!(await page.locator('#entry-recorded-cautions').isVisible()));
      assert(!(await tocTargets()).some(id=>id.startsWith('entry-recorded-')));
      await page.goto(url('entry-narrative-documentation'));await ready();
      assert.equal(await page.locator('#entry-recorded-cautions .entry-caution').count(),1,'Unsupported numeric rules remain withheld');
      assert((await page.locator('#entry-recorded-cautions').innerText()).includes(language==='ko'?'모든 코드의 준수를 보장하지 않습니다':'does not guarantee compliance'));
      await page.goto(url('entry-narrative-uncertain'));await ready();
      const uncertain=page.locator('#entry-recorded-flow .entry-flow-step.uncertain');
      assert.equal(await uncertain.count(),1);
      assert((await uncertain.innerText()).includes(language==='ko'?'병렬 구간':'Parallel'));
      assert.equal(await uncertain.evaluate(node=>getComputedStyle(node,'::after').display),'none');
      assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);await context.close();checks++;
    }
  } finally {await browser.close();}
  console.log(checks+' project navigation journeys passed: content-based contents, keyboard focus, scroll position, optional reviewed sections, visible scope, legacy links and offline rendering.');
})().catch(error=>{console.error(error);process.exitCode=1;});
