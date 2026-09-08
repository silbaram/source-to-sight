/* Optional offline project-entry QA using an existing Playwright installation. */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.argv[3] || 'playwright');

(async () => {
  const root = path.resolve(process.argv[2]);
  const browser = await chromium.launch({headless:true});
  let checks = 0;
  try {
    for (const language of ['ko','en']) {
      for (const width of [1440,768,390,320]) {
        const context = await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
        // Exercise command-copy fallback without any network or clipboard dependency.
        await context.addInitScript(() => {
          Object.defineProperty(navigator, 'clipboard', {value:{writeText:async text => {window.copiedCommand=text;}}});
        });
        const page = await context.newPage(), errors = [], external = [];
        page.on('pageerror',error => errors.push(error.message));
        page.on('console',message => {if(message.type()==='error')errors.push(message.text());});
        page.on('request',request => {if(/^https?:/.test(request.url()))external.push(request.url());});
        const url = name => pathToFileURL(path.join(root,language,name+'.html')).href;
        const ready = () => page.waitForSelector('html[data-ready="true"]');
        const selectedInView = async () => {
          const position = await page.locator('.entry-selected').evaluate(card => {
            const bounds = card.getBoundingClientRect();
            return {top:bounds.top,bottom:bounds.bottom,height:innerHeight,focused:document.activeElement===card};
          });
          assert(position.focused,'The returned capability receives focus');
          assert(position.top>=-1&&position.bottom<=position.height+1,
            'Returned capability must be in the viewport: '+JSON.stringify(position));
        };
        const overflow = async () => assert.equal(await page.evaluate(() => document.documentElement.scrollWidth>innerWidth+1),false,language+' '+width+' overflow');
        await page.goto(url('project'));await ready();
        assert(await page.locator('#atlas-entry').isVisible());
        assert(!(await page.locator('#workspace').isVisible()));
        assert.equal(await page.locator('#canvas .node').count(),0,'Diagram layout is lazy');
        assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('view'),'overview');
        await overflow();
        await page.locator('#scope-title').click();
        assert(await page.locator('#scope-body').isVisible());
        assert((await page.locator('#scope-body').textContent()).includes('validation-example'));
        await page.locator('#scope-title').click();
        const ids = await page.locator('[id]').evaluateAll(nodes => nodes.map(n=>n.id));
        assert.equal(ids.length,new Set(ids).size);
        await page.locator('#entry-search').fill('not-a-capability');
        assert.equal(await page.locator('.feature-card').count(),0);
        await page.locator('#entry-reset').click();
        await page.locator('#entry-availability').selectOption('missing');
        assert.equal(await page.locator('.feature-card').count(),0);
        await page.locator('#entry-availability').selectOption('ready');
        await page.locator('#entry-group').selectOption('region-main');
        await page.locator('#entry-search').fill('example.py');
        assert.equal(await page.locator('.feature-card').count(),1);
        await page.locator('#entry-files-tab').focus();await page.keyboard.press('Enter');
        assert.equal(await page.locator('#entry-files-tab').getAttribute('aria-pressed'),'true');
        await page.locator('[data-structure-id="structure-root"] > summary').click();
        await page.locator('[data-structure-id="structure-check"] > summary').click();
        await page.locator('[data-structure-id="structure-check"] > .entry-tree-body > .entry-evidence > summary').click();
        assert(await page.locator('[data-structure-id="structure-check"] .evidence-item').isVisible());
        await overflow();
        if([1440,390].includes(width))await page.screenshot({path:path.join(root,language,'entry-folders-'+width+'.png'),fullPage:true});
        await page.locator('.feature-card .entry-actions a').click();await ready();
        const state = new URL(page.url()).searchParams.get('s2s-atlas');
        const params = new URLSearchParams(state.slice(1));
        assert.equal(params.get('view'),'overview');
        assert.equal(params.get('feature'),'subject-main');
        assert.equal(params.get('q'),'example.py');
        assert.equal(params.get('tab'),'files');
        assert.equal(params.has('camera'),false);
        await page.locator('#links a[href*="logic.html"]').click();await ready();
        await page.locator('a[data-layer="atlas"]').click();await ready();
        assert.equal(new URL(page.url()).hash,state);
        assert(await page.locator('#atlas-entry').isVisible());
        assert.equal(await page.locator('#entry-search').inputValue(),'example.py');
        assert.equal(await page.locator('#entry-group').inputValue(),'region-main');
        assert.equal(await page.locator('#entry-availability').inputValue(),'ready');
        assert.equal(await page.locator('.entry-selected').getAttribute('data-feature-id'),'subject-main');
        await selectedInView();
        if([1440,390].includes(width))await page.screenshot({path:path.join(root,language,'entry-return-'+width+'.png')});
        // The direct behavior → entry return must frame the capability too.
        await page.locator('.feature-card .entry-actions a').click();await ready();
        await page.locator('#links a[href*="project.html"]').click();await ready();
        await selectedInView();
        await page.locator('#entry-reset').click();
        await page.locator('#entry-roles-tab').click();
        for(const theme of ['light','dark']) {
          if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('#theme-toggle').click();
          await page.evaluate(()=>scrollTo(0,0));
          if([1440,390].includes(width))await page.screenshot({path:path.join(root,language,'entry-'+width+'-'+theme+'.png'),fullPage:true});
        }
        await page.locator('.role-card > button').click();
        assert(await page.locator('#workspace').isVisible());
        assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('region'),'region-main');
        await page.locator('#entry-home').click();
        await page.locator('.feature-card .entry-actions button').click();
        assert(await page.locator('#panel.open').isVisible());
        assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('item'),'subject-main');
        // The user's existing full-diagram URL must still open directly.
        await page.goto(url('project')+'#s2s=1&subject=project-orders&view=structure&detail=detail&speed=1&node=node-main&panel=1');
        await ready();
        assert(await page.locator('#panel.open').isVisible());
        assert(!(await page.locator('#atlas-entry').isVisible()));
        assert.equal(await page.locator('#mode').inputValue(),'detail');
        await page.goto(url('project')+'#s2s=1&subject=wrong&view=overview');await ready();
        assert(await page.locator('#navigation-notice').isVisible());
        assert(await page.locator('#atlas-entry').isVisible());
        for(const variant of ['legacy','empty','missing','uncertain','ungrouped']) {
          await page.goto(url('entry-'+variant));await ready();
          if(variant==='legacy') {
            await page.locator('#entry-files-tab').click();
            assert(await page.locator('#entry-files .entry-empty').isVisible());
            await page.locator('#entry-diagram').click();
            assert(await page.locator('#canvas').isVisible());
          } else if(variant==='empty') {
            assert(await page.locator('#entry-features .entry-empty').isVisible());
          } else if(variant==='missing') {
            assert.equal(await page.locator('.feature-card a').count(),0);
            await page.locator('.feature-card .entry-actions button').first().click();
            const copied = await page.evaluate(()=>window.copiedCommand);
            assert(copied.includes('subject-main'));
            assert(!new URL(page.url()).pathname.endsWith('/behavior.html'));
          } else if(variant==='uncertain') {
            await page.locator('#entry-files-tab').click();
            assert(await page.locator('[data-structure-id="structure-root"] > summary .uncertain').isVisible());
          } else {
            assert.equal(await page.locator('.role-card').count(),1);
            await page.locator('.role-card > button').click();
            assert(await page.locator('#panel.open').isVisible());
          }
          await overflow();
        }
        await page.goto(url('project')+'#entry-title');await ready();
        assert.equal(new URL(page.url()).hash,'#entry-title');
        assert(await page.locator('#atlas-entry').isVisible());
        // Resizing on the entry must not lay out the hidden canvas.
        await page.setViewportSize({width:width===1440?390:1440,height:900});
        await page.locator('#entry-diagram').click();
        assert(await page.locator('#canvas .node').first().isVisible());
        await page.locator('#entry-home').click();
        await page.locator('.skip').focus();await page.keyboard.press('Enter');
        assert(await page.locator('#atlas-entry').isVisible());
        assert.deepEqual(errors,[]);
        assert.deepEqual(external,[]);
        await context.close();checks++;
      }
    }
    let localeChecks=0;
    for(const language of ['en-GB-oed','en-foo','ko-foo','en-US','ko-KR']) {
      for(const width of [1440,390]) {
        const context=await browser.newContext({viewport:{width,height:900}});
        const page=await context.newPage(),errors=[],external=[];
        page.on('pageerror',error=>errors.push(error.message));
        page.on('request',request=>{if(/^https?:/.test(request.url()))external.push(request.url());});
        await page.goto(pathToFileURL(path.join(root,'en','entry-locale-'+language+'.html')).href);
        await page.waitForSelector('html[data-ready="true"]',{timeout:5000});
        assert(await page.locator('#atlas-entry').isVisible(),language+' entry initializes');
        await page.locator('#entry-files-tab').click();
        await page.locator('[data-structure-id="structure-root"] > summary').click();
        assert(await page.locator('[data-structure-id="structure-check"] > summary').isVisible());
        // Sorting is presentation-only; never rewrite the recorded language.
        assert.equal(await page.locator('#s2s-data').evaluate(el=>JSON.parse(el.textContent).language),language);
        await page.locator('#entry-diagram').click();
        assert(await page.locator('#canvas .node').first().isVisible());
        await page.locator('#entry-home').click();
        assert(await page.locator('#atlas-entry').isVisible());
        assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
        await context.close();localeChecks++;
      }
    }
    let treeChecks=0;
    for(const language of ['ko','en'])for(const width of [1440,390]) {
      const context=await browser.newContext({viewport:{width,height:900}});
      const page=await context.newPage(),errors=[],external=[];
      page.on('pageerror',error=>errors.push(error.message));
      page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
      page.on('request',request=>{if(/^https?:/.test(request.url()))external.push(request.url());});
      for(const variant of ['rooted','rootless']) {
        const label=language+' '+width+' '+variant;
        await page.goto(pathToFileURL(path.join(root,language,'entry-tree-'+variant+'.html')).href);
        await page.waitForSelector('html[data-ready="true"]',{timeout:5000});
        await page.locator('#entry-files-tab').click();
        const parents=await page.locator('.entry-tree-item').evaluateAll(items=>Object.fromEntries(items.map(item=>[
          item.querySelector(':scope > summary > code').textContent,
          item.parentElement.closest('.entry-tree-item')?.querySelector(':scope > summary > code').textContent??null
        ])));
        const parentRoot=variant==='rooted'?'.':null;
        const expected={'example.py':parentRoot};
        if(parentRoot)expected['.']=null;
        for(const directory of ['R','_','가','R/skipped/nested','Rextra']) {
          expected[directory]=directory==='R/skipped/nested'?'R':parentRoot;
          expected[directory+'/example.py']=directory;
        }
        assert.deepEqual(parents,expected,label+' literal parents; no invented intermediate folders');
        if(parentRoot)await page.locator('[data-structure-id="structure-root"] > summary').click();
        const folder=page.locator('[data-structure-id="structure-tree-0-directory"] > summary');
        const child=page.locator('[data-structure-id="structure-tree-0-file"] > summary');
        assert(await folder.isVisible(),label+' R starts under its recorded root');
        assert(!(await child.isVisible()),label+' child starts collapsed');
        await folder.click();assert(await child.isVisible(),label+' opening R reveals its child');
        await folder.click();assert(!(await child.isVisible()),label+' closing R hides its child');
        // Open all recorded levels to inspect the deepest mobile layout too.
        await page.locator('.entry-tree-item').evaluateAll(items=>items.forEach(item=>{item.open=true;}));
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false,label+' overflow');
        if(variant==='rooted')await page.locator('.entry-tree').screenshot({path:path.join(root,language,'entry-tree-'+width+'.png')});
        treeChecks++;
      }
      assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
      await context.close();
    }
    console.log('Atlas entry browser checks passed: '+checks+' language/viewport cases, '+localeChecks+' locale cases and '+treeChecks+' ancestry cases.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
