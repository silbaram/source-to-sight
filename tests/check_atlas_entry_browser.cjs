/* Optional offline project-entry QA using an existing Playwright installation. */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.argv[3] || 'playwright');

async function checkContrast(page, selector) {
  const failures=await page.locator(selector).evaluateAll(elements=>{
    const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
    const context=canvas.getContext('2d',{willReadFrequently:true});
    const rgba=color=>{context.clearRect(0,0,1,1);context.fillStyle=color;context.fillRect(0,0,1,1);return [...context.getImageData(0,0,1,1).data].map((value,index)=>index===3?value/255:value);};
    const blend=(front,back)=>front.slice(0,3).map((value,index)=>value*front[3]+back[index]*(1-front[3]));
    const luminance=color=>color.map(value=>{value/=255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;}).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);
    return elements.filter(el=>el.getClientRects().length).flatMap(el=>{
      const ancestors=[];for(let parent=el;parent;parent=parent.parentElement)ancestors.unshift(parent);
      let background=[255,255,255];
      for(const parent of ancestors)background=blend(rgba(getComputedStyle(parent).backgroundColor),background);
      const foreground=blend(rgba(getComputedStyle(el).color),background),a=luminance(foreground),b=luminance(background);
      const ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
      return ratio>=4.5?[]:[{element:el.id||el.className,text:el.textContent.slice(0,50),ratio}];
    });
  });
  assert.deepEqual(failures,[],'Normal text contrast must be at least 4.5:1');
}

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
        const selectedInView = async (focus='card') => {
          const position = await page.locator('.entry-selected').evaluate((card,focus) => {
            const bounds = card.getBoundingClientRect();
            return {top:bounds.top,bottom:bounds.bottom,height:innerHeight,focused:document.activeElement===(focus==='card'?card:card.querySelector('.entry-select'))};
          },focus);
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
        assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).has('tab'),false);
        const data=await page.locator('#s2s-data').evaluate(el=>JSON.parse(el.textContent));
        assert.equal(await page.locator('#entry-toc,#entry-tabs,#entry-roles-tab,#entry-files-tab').count(),0);
        assert(await page.locator('#entry-summary').isVisible());
        assert(!(await page.locator('#entry-context-body').isVisible()),'Do not assume the first capability');
        assert(!(await page.locator('#entry-files').isVisible()),'Full tree is on demand');
        assert(!(await page.locator('#entry-support').isVisible()),'Do not duplicate capability owners as role cards');
        for(const value of [...data.summary.inputs,...data.summary.outputs])assert((await page.locator('#entry-summary').textContent()).includes(value));
        assert.equal(await page.locator('.entry-capability-group').getAttribute('data-group-id'),'region-main');
        assert((await page.locator('#entry-alerts').textContent()).includes(data.analysis.unresolved[0]),'Important limits stay visible before selection');
        assert.equal(await page.locator('#entry-context').evaluate(el=>el.parentElement===document.body),true,'Dialog must not be inside its inert background');
        await page.locator('.entry-select').scrollIntoViewIfNeeded();
        const entryPosition=await page.evaluate(()=>({x:scrollX,y:scrollY}));
        await page.locator('.entry-select').click();
        assert.equal(await page.locator('#entry-context').getAttribute('role'),'dialog');
        assert.equal(await page.locator('#entry-context').getAttribute('aria-modal'),'true');
        assert.equal(await page.locator('main').evaluate(el=>el.inert),true);
        assert(await page.locator('#entry-context-body').isVisible());
        assert.equal(await page.locator('#entry-context-title').textContent(),data.subjects[0].label);
        assert.equal(await page.locator('#entry-context-title').evaluate(el=>el===document.activeElement),true);
        assert.equal(await page.locator('#entry-context-title').evaluate(el=>{
          const bounds=el.getBoundingClientRect();
          return el.contains(document.elementFromPoint(bounds.left+bounds.width/2,bounds.top+bounds.height/2));
        }),true,'Focused title must not be covered by dialog controls');
        assert.equal(await page.locator('.entry-select').getAttribute('aria-haspopup'),'dialog');
        assert.equal(await page.locator('#entry-context details[open]').count(),0,'Long flows, paths, scope and evidence start collapsed');
        assert((await page.locator('#entry-context-owner').textContent()).includes(data.nodes[0].summary));
        assert((await page.locator('#entry-context-paths').textContent()).includes('example.py'));
        assert((await page.locator('#entry-context-checks').textContent()).includes(language==='ko'?'기록되지 않았습니다':'No linked tests'));
        assert.deepEqual(await page.locator('.entry-flow-step').evaluateAll(items=>items.map(item=>item.dataset.stepId)),data.scenarios[0].steps.map(step=>step.id));
        assert.deepEqual(await page.locator('.entry-flow-caption').allTextContents(),data.scenarios[0].steps.map(step=>step.caption));
        assert((await page.locator('.entry-flow-case > summary').textContent()).includes(data.scenarios[0].title));
        assert.equal(await page.locator('.entry-caution').count(),data.rules.length);
        await page.locator('#entry-context-body').evaluate(el=>{el.scrollTop=el.scrollHeight;});
        assert.equal(await page.locator('#entry-context-close').evaluate(el=>{
          const bounds=el.getBoundingClientRect();return bounds.top>=0&&bounds.bottom<=innerHeight;
        }),true,'Close stays in the viewport when the summary body scrolls');
        await page.locator('#entry-context-close').click();
        assert.equal(await page.locator('.entry-selected').count(),1,'Closing does not clear the chosen capability');
        assert.equal(await page.locator('.entry-select').evaluate(el=>el===document.activeElement),true);
        assert.deepEqual(await page.evaluate(()=>({x:scrollX,y:scrollY})),entryPosition,'Closing restores the original page position');
        assert.equal(await page.locator('main').evaluate(el=>el.inert),false);
        assert.equal(await page.locator('html').evaluate(el=>el.style.overflow),'');
        assert(!(await page.locator('#entry-context-body').isVisible()));
        await page.keyboard.press('Enter');
        assert(await page.locator('#entry-context').isVisible());
        assert.equal(await page.locator('#entry-context-body').evaluate(el=>el.scrollTop),0,'Reopening starts the summary at the top');
        await page.locator('#entry-context-close').focus();await page.keyboard.press('Shift+Tab');
        assert.equal(await page.locator('#entry-context-actions > :last-child').evaluate(el=>el===document.activeElement),true);
        await page.keyboard.press('Tab');
        assert.equal(await page.locator('#entry-context-close').evaluate(el=>el===document.activeElement),true);
        await page.keyboard.press('Escape');
        assert(!(await page.locator('#entry-context').isVisible()));
        if(width>=768) {
          await page.locator('.entry-select').click();await page.mouse.click(4,4);
          assert(!(await page.locator('#entry-context').isVisible()),'Backdrop click dismisses the desktop dialog');
        }
        assert.equal(await page.locator('.coverage-label').textContent(),(language==='ko'?'기록된 항목 확인 ':'Recorded items checked ')+'5 / 5');
        await page.locator('#atlas-summary button').click();
        assert.equal(await page.locator('#entry-gaps-title').evaluate(el=>el===document.activeElement),true);
        assert(await page.locator('#entry-gaps-body').isVisible());
        for(const text of [...data.analysis.unresolved,...data.summary.limitations,...data.subject.scope.excludes,...data.analysis.nextAttempts])assert((await page.locator('#entry-gaps-body').textContent()).includes(text));
        await page.locator('#entry-gaps-title').click();
        // Keyboard search is local to the entry and restores focus on dismiss.
        await page.locator('#entry-palette-open').focus();await page.keyboard.press('Control+k');
        assert(await page.locator('#entry-palette').isVisible());
        assert.equal(await page.locator('#entry-palette-input').evaluate(el=>el===document.activeElement),true);
        assert.equal(await page.locator('main').evaluate(el=>el.inert),true);
        await page.keyboard.press('Escape');
        assert(!(await page.locator('#entry-palette').isVisible()));
        assert.equal(await page.locator('#entry-palette-open').evaluate(el=>el===document.activeElement),true);
        assert.equal(await page.locator('main').evaluate(el=>el.inert),false);
        await page.keyboard.press('Meta+k');
        await page.locator('#entry-palette-input').fill('does-not-exist');
        assert.equal(await page.locator('#entry-palette-results button').count(),0);
        await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');
        assert(await page.locator('#entry-palette').isVisible());
        await page.locator('#entry-palette-input').fill(data.subjects[0].label.toLocaleLowerCase());
        await page.keyboard.press('Enter');
        assert(!(await page.locator('#entry-palette').isVisible()));
        assert(await page.locator('#entry-context').isVisible(),'Capability search opens its summary');
        await page.locator('#entry-context-close').click();
        await selectedInView('button');
        // A path result opens its collapsed ancestors and focuses the actual path.
        await page.locator('#entry-palette-open').click();
        await page.locator('#entry-palette-input').fill('EXAMPLE.PY');
        await page.keyboard.press('ArrowDown');
        assert.equal(await page.locator('#entry-palette-results button').first().evaluate(el=>el===document.activeElement),true);
        await page.keyboard.press('Enter');
        assert.equal(await page.locator('[data-structure-id="structure-check"] > summary').evaluate(el=>el===document.activeElement),true);
        assert.equal(await page.locator('[data-structure-id="structure-root"]').getAttribute('open'),'');
        await page.locator('.entry-tree-item').evaluateAll(items=>items.forEach(item=>{item.open=false;}));
        await page.locator('#entry-reset').click();
        // Edge-only and node-only steps resolve to the responsible component.
        for(const index of [0,1]) {
          await page.locator('.entry-select').click();
          await page.locator('#entry-flow-title').click();await page.locator('.entry-flow-case > summary').click();
          await page.locator('.entry-flow-button').nth(index).click();
          assert(!(await page.locator('#entry-context').isVisible()));
          assert.equal(await page.locator('main').evaluate(el=>el.inert),false);
          assert(await page.locator('#panel.open').isVisible());
          assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('node'),'node-main');
          await page.locator('#entry-home').click();
        }
        await overflow();
        await page.locator('#scope-title').click();
        assert(await page.locator('#scope-body').isVisible());
        assert((await page.locator('#scope-body').textContent()).includes('validation-example'));
        await page.locator('#scope-title').click();
        const ids = await page.locator('[id]').evaluateAll(nodes => nodes.map(n=>n.id));
        assert.equal(ids.length,new Set(ids).size);
        await page.locator('#entry-search').fill('not-a-capability');
        assert.equal(await page.locator('.feature-card').count(),0);
        assert(!(await page.locator('#entry-context-body').isVisible()),'Filtered-out selection must not leave stale context');
        await page.locator('#entry-reset').click();
        await page.locator('#entry-availability').selectOption('missing');
        assert.equal(await page.locator('.feature-card').count(),0);
        await page.locator('#entry-availability').selectOption('ready');
        await page.locator('#entry-group').selectOption('region-main');
        await page.locator('#entry-search').fill('example.py');
        assert.equal(await page.locator('.feature-card').count(),1);
        assert(await page.locator('#entry-files').isVisible());
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
        assert.equal(params.has('tab'),false);
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
        assert(!(await page.locator('#entry-context').isVisible()),'Returning highlights the card without automatically reopening a dialog');
        await page.locator('.entry-select').click();
        await page.locator('#entry-context-actions a').click();await ready();
        assert.equal(new URLSearchParams(new URL(page.url()).searchParams.get('s2s-atlas').slice(1)).get('feature'),'subject-main');
        await page.locator('#links a[href*="project.html"]').click();await ready();
        await selectedInView();
        await page.locator('#entry-reset').click();
        for(const theme of ['light','dark']) {
          if(await page.locator('html').getAttribute('data-theme')!==theme)await page.locator('#theme-toggle').click();
          await page.evaluate(()=>scrollTo(0,0));
          await overflow();
          await checkContrast(page,'.coverage-label,.entry-kicker,.entry-note,.entry-io-label,.entry-io li,.entry-select,.entry-feature-meta>span,.entry-path-link,.entry-card p,.atlas-entry .pill,.entry-primary,.entry-group-count,.entry-group-heading h3');
          if([1440,390].includes(width))await page.screenshot({path:path.join(root,language,'entry-'+width+'-'+theme+'.png'),fullPage:true});
          await page.locator('.entry-select').click();
          await checkContrast(page,'#entry-context-title,.entry-flow-caption,.entry-flow-button small,.entry-caution h4,.entry-context-section h3,.entry-location code,.entry-location small,.entry-connection span,.entry-rule-facts dt,.entry-rule-facts dd,.entry-context .pill,.entry-context-disclosure>summary');
          if([1440,390].includes(width))await page.screenshot({path:path.join(root,language,'entry-context-'+width+'-'+theme+'.png')});
          await page.locator('#entry-context-close').click();
          await page.locator('#entry-palette-open').click();
          await overflow();await checkContrast(page,'.entry-palette-heading label,.entry-palette-heading button,#entry-palette-input,.entry-palette-results button span,.entry-palette-results button small,.entry-palette-hint');
          // Tab and Shift+Tab stay inside the modal; close is usable on touch too.
          await page.locator('#entry-palette-close').focus();await page.keyboard.press('Shift+Tab');
          assert.equal(await page.locator('#entry-palette-results button').last().evaluate(el=>el===document.activeElement),true);
          await page.keyboard.press('Tab');
          assert.equal(await page.locator('#entry-palette-close').evaluate(el=>el===document.activeElement),true);
          if([1440,390].includes(width))await page.screenshot({path:path.join(root,language,'entry-search-'+width+'-'+theme+'.png')});
          await page.locator('#entry-palette-close').click();
        }
        // Components (but not context actors) are included in the search index.
        await page.locator('#entry-palette-open').click();
        await page.locator('#entry-palette-input').fill(data.nodes.find(node=>node.contextOnly).label);
        assert.equal(await page.locator('#entry-palette-results button').count(),0);
        await page.locator('#entry-palette-input').fill('CHECK');
        await page.locator('#entry-palette-results button').filter({has:page.locator('small', {hasText:language==='ko'?'구성 요소':'Component'})}).click();
        assert(await page.locator('#panel.open').isVisible());
        await page.locator('#entry-home').click();
        await page.locator('.entry-group-heading > button').click();
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
        await page.locator('#canvas').focus();await page.keyboard.press('Control+k');
        assert(!(await page.locator('#entry-palette').isVisible()),'Do not intercept the diagram shortcut');
        for(const tab of ['roles','files']) {
          await page.goto(url('project')+'#s2s=1&subject=project-orders&view=overview&tab='+tab+'&q=example.py&feature=subject-main');await ready();
          assert(!(await page.locator('#navigation-notice').isVisible()),'Old tab links remain valid');
          assert(await page.locator('.feature-card').isVisible());assert(!(await page.locator('#entry-context').isVisible()));
          assert.equal(await page.locator('#entry-search').inputValue(),'example.py');
          await selectedInView();
          assert.equal(new URLSearchParams(new URL(page.url()).hash.slice(1)).has('tab'),false);
        }
        await page.goto(url('project')+'#s2s=1&subject=wrong&view=overview');await ready();
        assert(await page.locator('#navigation-notice').isVisible());
        assert(await page.locator('#atlas-entry').isVisible());
        for(const variant of ['legacy','empty','missing','uncertain','ungrouped']) {
          await page.goto(url('entry-'+variant));await ready();
          if(variant==='legacy') {
            await page.locator('#entry-files-title').click();
            assert(await page.locator('#entry-files .entry-empty').isVisible());
            assert((await page.locator('.coverage-label').textContent()).endsWith('3 / 3'),'Legacy capability status inherits its owner');
            await page.locator('#entry-diagram').click();
            assert(await page.locator('#canvas').isVisible());
          } else if(variant==='empty') {
            assert(await page.locator('#entry-features .entry-empty').isVisible());
            assert(await page.locator('.role-card').isVisible(),'Uncataloged components remain navigable');
          } else if(variant==='missing') {
            assert.equal(await page.locator('.feature-card a').count(),0);
            await page.locator('.feature-card .entry-actions button').first().click();
            const copied = await page.evaluate(()=>window.copiedCommand);
            assert(copied.includes('subject-main'));
            assert(!new URL(page.url()).pathname.endsWith('/behavior.html'));
          } else if(variant==='uncertain') {
            await page.locator('#entry-files-title').click();
            assert(await page.locator('[data-structure-id="structure-root"] > summary .uncertain').isVisible());
            assert((await page.locator('.coverage-label').textContent()).endsWith('4 / 5'));
          } else {
            assert.equal(await page.locator('.entry-capability-group').count(),1);
            await page.locator('.entry-group-heading > button').click();
            assert(await page.locator('#panel.open').isVisible());
          }
          await overflow();
        }
        for(const variant of ['empty','uncertain','documentation']) {
          await page.goto(url('entry-narrative-'+variant));await ready();
          await page.locator('.entry-select').click();
          if(variant==='empty') {
            assert(!(await page.locator('#entry-flow').isVisible()));
            assert(!(await page.locator('#entry-cautions').isVisible()));
            assert.equal(await page.locator('#entry-gaps-body').textContent(),language==='ko'?'기록된 미확인 항목이 없습니다.':'No unresolved items are recorded.');
          } else if(variant==='uncertain') {
            await page.locator('#entry-flow-title').click();await page.locator('.entry-flow-case > summary').click();
            const step=page.locator('.entry-flow-step.uncertain');
            assert.equal(await step.count(),1);
            assert.equal(await step.evaluate(el=>getComputedStyle(el,'::before').borderTopStyle),'dashed');
            assert.equal(await step.evaluate(el=>getComputedStyle(el,'::after').display),'none');
            assert((await step.textContent()).includes(language==='ko'?'병렬 구간':'Parallel'));
            assert((await step.textContent()).includes(language==='ko'?'다른 경로':'Alternative'));
            assert.equal(await page.locator('.entry-caution > .pill.uncertain').count(),1);
            await checkContrast(page,'.entry-flow-step.uncertain .pill,.entry-caution > .pill.uncertain');
          } else {
            assert.equal(await page.locator('.entry-caution').count(),1,'Unverified numeric rules are pruned before rendering');
            assert.equal(await page.locator('.entry-caution').getAttribute('data-rule-id'),'rule-documentation');
            assert((await page.locator('.entry-caution .entry-meta').textContent()).includes(language==='ko'?'모든 코드의 준수를 보장하지 않습니다':'does not guarantee compliance'));
            await page.locator('.entry-caution .entry-evidence > summary').click();
            assert((await page.locator('.entry-caution .evidence-item').textContent()).includes('CONTRIBUTING.md'));
          }
          await overflow();
        }
        await page.goto(url('entry-workspace'));await ready();
        assert.equal(await page.locator('.entry-capability-group').count(),2);
        assert.equal(await page.locator('.feature-card').count(),2);
        await page.locator('[data-feature-id="subject-main"] .entry-select').click();
        assert.deepEqual(await page.locator('.entry-caution').evaluateAll(items=>items.map(item=>item.dataset.ruleId)),['rule-main']);
        assert.equal(await page.locator('.entry-flow-case').count(),1,'Unrelated component flow is excluded');
        assert((await page.locator('#entry-context-checks').textContent()).includes('test_example.py'));
        assert((await page.locator('#entry-context-checks').textContent()).includes(language==='ko'?'실행 결과를 뜻하지 않습니다':'not test execution results'));
        await page.locator('#entry-context-close').click();
        await page.locator('[data-feature-id="subject-review"] .entry-select').click();
        assert.equal(await page.locator('#entry-context-title').textContent(),language==='ko'?'출고 후 결과 살펴보기':'Explore the shipped outcome');
        assert.deepEqual(await page.locator('.entry-caution').evaluateAll(items=>items.map(item=>item.dataset.ruleId)),['rule-shipped']);
        assert.deepEqual(await page.locator('.entry-flow-step').evaluateAll(items=>items.map(item=>item.dataset.stepId)),['step-review']);
        assert(!(await page.locator('#entry-context-checks').textContent()).includes('test_example.py'));
        // Manual copying stays inside the active dialog when both clipboard
        // methods fail; Escape closes that field before closing the summary.
        await page.evaluate(()=>{navigator.clipboard.writeText=async()=>{throw new Error('denied');};document.execCommand=()=>false;});
        await page.locator('#entry-context-actions button').first().click();
        assert(await page.locator('#copy-fallback').isVisible());
        assert.equal(await page.locator('#copy-text').evaluate(el=>el===document.activeElement&&!!el.closest('#entry-context')),true);
        assert((await page.locator('#copy-text').inputValue()).includes('subject-review'));
        await page.keyboard.press('Escape');
        assert(!(await page.locator('#copy-fallback').isVisible()));assert(await page.locator('#entry-context').isVisible());
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('#copy-fallback').evaluate(el=>el.parentElement===document.body),true);
        await page.locator('[data-feature-id="subject-review"] .entry-select').click();
        await page.evaluate(()=>{navigator.clipboard.writeText=()=>new Promise((resolve,reject)=>{window.rejectPendingCopy=reject;});});
        await page.locator('#entry-context-actions button').first().click();
        await page.keyboard.press('Escape');
        await page.evaluate(()=>window.rejectPendingCopy(new Error('late denial')));
        await page.waitForFunction(()=>document.querySelector('#announcement').textContent.includes('다시 시도')||document.querySelector('#announcement').textContent.includes('Try again'));
        assert(!(await page.locator('#copy-fallback').isVisible()),'Late clipboard denial must not resurrect a dismissed dialog');
        assert.equal(await page.locator('[data-feature-id="subject-review"] .entry-select').evaluate(el=>el===document.activeElement),true);
        await page.locator('#entry-search').fill('no-match');
        assert(!(await page.locator('#entry-context-body').isVisible()));
        await overflow();
        await page.goto(url('entry-groups'));await ready();
        const grouping=await page.locator('.entry-capability-group').evaluateAll(groups=>groups.map(group=>{
          const bounds=group.getBoundingClientRect(),cards=[...group.querySelectorAll('.feature-card')].map(card=>card.getBoundingClientRect());
          return {id:group.dataset.groupId,count:cards.length,label:group.querySelector('.entry-group-count').textContent,
            top:bounds.top,bottom:bounds.bottom,width:bounds.width,cardTops:cards.map(card=>card.top),
            contained:cards.every(card=>card.left>bounds.left&&card.right<bounds.right&&card.top>bounds.top&&card.bottom<bounds.bottom)};
        }));
        assert.deepEqual(grouping.map(group=>group.count),[3,1]);
        assert(grouping.every(group=>group.contained),'Each group visibly encloses every member card');
        assert(grouping[1].top>grouping[0].bottom,'Uneven groups stack instead of leaving an empty column');
        assert(Math.abs(grouping[0].width-grouping[1].width)<1,'Groups use the full catalog width');
        if(width===1440)assert(Math.max(...grouping[0].cardTops)-Math.min(...grouping[0].cardTops)<1,'Three sibling capabilities share a row on desktop');
        assert(grouping[0].label.endsWith('3'));assert(grouping[1].label.endsWith('1'));
        await page.locator('#entry-search').fill(language==='ko'?'취소 조건 살펴보기':'Explore cancellation conditions');
        assert.equal(await page.locator('.feature-card').count(),1);
        assert((await page.locator('.entry-group-count').textContent()).includes('1 / 3'));
        const preservedQuery=await page.locator('#entry-search').inputValue();
        await page.locator('.entry-select').click();await page.locator('#entry-context-close').click();
        assert.equal(await page.locator('#entry-search').inputValue(),preservedQuery);
        assert.equal(await page.locator('.feature-card').count(),1);
        await page.locator('.entry-select').click();
        await page.locator('#entry-context-paths .entry-location').first().click();
        assert(!(await page.locator('#entry-context').isVisible()));
        assert.equal(await page.locator('main').evaluate(el=>el.inert),false);
        assert.equal(await page.locator('[data-structure-id="structure-check"] > summary').evaluate(el=>el===document.activeElement),true,'A dialog path closes the dialog and reveals the actual tree entry');
        await page.locator('.entry-select').click();await page.keyboard.press('Control+k');
        assert(!(await page.locator('#entry-context').isVisible()));assert(await page.locator('#entry-palette').isVisible(),'Search replaces rather than stacks on the summary');
        await page.keyboard.press('Escape');
        assert.equal(await page.locator('main').evaluate(el=>el.inert),false);
        await page.locator('.entry-select').click();
        await page.evaluate(()=>{location.hash='#s2s=1&subject=project-orders&view=structure';});
        await page.waitForSelector('#workspace',{state:'visible'});
        assert(!(await page.locator('#entry-context').isVisible()));
        assert.equal(await page.locator('main').evaluate(el=>el.inert),false);
        assert.equal(await page.locator('html').evaluate(el=>el.style.overflow),'');
        await page.locator('#entry-home').click();
        // Navigation while the palette is open must release its inert/scroll lock.
        await page.locator('#entry-palette-open').click();
        await page.evaluate(()=>{location.hash='#s2s=1&subject=project-orders&view=structure';});
        await page.waitForSelector('#workspace', {state:'visible'});
        assert(!(await page.locator('#entry-palette').isVisible()));
        assert.equal(await page.locator('main').evaluate(el=>el.inert),false);
        assert.equal(await page.locator('html').evaluate(el=>el.style.overflow),'');
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
        await page.locator('#entry-files-title').click();
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
        await page.locator('#entry-files-title').click();
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
