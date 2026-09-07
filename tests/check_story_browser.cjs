/* Optional local Chromium QA. Runtime generation does not depend on Playwright. */
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
    for (const language of ['ko', 'en']) {
      for (const viewport of [{width:1440,height:1000}, {width:390,height:844}]) {
        const context = await browser.newContext({viewport, reducedMotion:viewport.width<700?'reduce':'no-preference'});
        const page = await context.newPage();
        const errors = [], external = [];
        page.on('pageerror', error => errors.push(error.message));
        page.on('console', message => {if(message.type()==='error') errors.push(message.text());});
        page.on('request', request => {if(/^https?:/.test(request.url())) external.push(request.url());});
        const url = pathToFileURL(path.join(root, language, 'project.html')).href;
        await page.goto(url);
        await page.waitForSelector('html[data-ready="true"]');
        await page.locator('#capabilities [data-capability-id="subject-main"]').click();
        await page.waitForFunction(() => !document.querySelector('.camera-moving'));
        await page.locator('.capability-action a').click();
        await page.waitForURL('**/behavior.html?*');
        await page.waitForSelector('html[data-ready="true"]');
        const state = new URL(page.url()).searchParams.get('s2s-atlas');
        assert(state.startsWith('#s2s=1&'));
        await page.locator('#links a[href*="logic.html"]').click();
        await page.waitForURL('**/logic.html?*');
        await page.waitForSelector('html[data-ready="true"]');
        assert.equal(new URL(page.url()).searchParams.get('s2s-atlas'), state);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
        assert.equal(overflow, false, language+' '+viewport.width+' overflow');
        const ids = await page.locator('[id]').evaluateAll(nodes => nodes.map(node => node.id));
        assert.equal(new Set(ids).size, ids.length, 'Duplicate output IDs');
        for (const choice of ['before', 'after']) {
          const button = page.locator('[data-choice="'+choice+'"]');
          await button.focus();
          await page.keyboard.press('Enter');
          assert.equal(await button.getAttribute('aria-pressed'), 'true');
          const expected = language==='ko' ? (choice==='before'?'취소 완료':'별도 검토') : (choice==='before'?'Cancelled':'Manual review');
          assert((await page.locator('.lesson-result').textContent()).endsWith(expected));
          assert.equal(await page.locator('[data-route].active').count(), 1);
        }
        await page.locator('[data-reset]').click();
        assert.equal(await page.locator('[data-route].inactive').count(), 0);
        await page.locator('.authored-evidence > summary').click();
        assert.equal(await page.locator('.authored-evidence .rule-case').count(), 2);
        await page.locator('.authored-evidence > summary').click();
        for (const theme of ['light','dark']) {
          if(await page.locator('html').getAttribute('data-theme')!==theme) await page.locator('#theme-toggle').click();
          await page.evaluate(() => scrollTo(0, 0));
          await page.screenshot({path:path.join(root, language, `lesson-${viewport.width}-${theme}.png`), fullPage:true});
          assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
        }
        await page.locator('a[data-layer="behavior"]').click();
        await page.waitForURL('**/behavior.html?*');
        await page.waitForSelector('html[data-ready="true"]');
        assert.equal(new URL(page.url()).searchParams.get('s2s-atlas'), state);
        await page.locator('#links a[href*="logic.html"]').click();
        await page.waitForSelector('html[data-viewer="primer"][data-ready="true"]');
        await page.locator('a[data-layer="atlas"]').click();
        await page.waitForURL('**/project.html#*');
        await page.waitForSelector('html[data-ready="true"]');
        // The map canonicalizes its hash after restoring the supplied camera.
        const expectedState = new URLSearchParams(state.slice(1));
        const camera = JSON.parse(expectedState.get('camera'));
        expectedState.delete('camera'); expectedState.delete('layout');
        assert.equal(new URL(page.url()).hash, '#'+expectedState.toString());
        const actualCamera = await page.evaluate(() => [
          parseFloat(document.querySelector('#zoom-level').textContent)/100,
          document.querySelector('#canvas').scrollLeft, document.querySelector('#canvas').scrollTop, scrollY,
        ]);
        camera.forEach((value,index) => assert(Math.abs(value-actualCamera[index])<2, `Camera ${index}: ${value} != ${actualCamera[index]}`));
        assert.equal(await page.locator('#capabilities [data-capability-id="subject-main"]').getAttribute('class').then(value=>value.includes('active')), true);
        assert.deepEqual(errors, []);
        assert.deepEqual(external, []);
        await context.close();
        checks++;
      }
      const context = await browser.newContext({javaScriptEnabled:false, viewport:{width:390,height:844}});
      const page = await context.newPage();
      await page.goto(pathToFileURL(path.join(root, language, 'logic.html')).href);
      assert.equal(await page.locator('.authored-picture svg').count(), 1);
      assert(await page.locator('.lesson-result').isVisible());
      assert.equal(await page.locator('a[data-layer="behavior"]').count(), 1);
      await page.locator('.authored-evidence > summary').click();
      assert(await page.locator('.authored-evidence .rule-case').first().isVisible());
      await context.close();
      checks++;

      for (const kind of ['authored', 'comparison', 'incomplete', 'navigation', 'copy']) {
        const context = await browser.newContext();
        await context.addInitScript(() => {
          window.clipboardWrites=[];
          Object.defineProperty(navigator, 'clipboard', {value:{writeText:async value => {
            window.copiedCommand=String(value);
            window.clipboardWrites.push(window.copiedCommand);
          }}});
        });
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const url = pathToFileURL(path.join(root, language, `runtime-${kind}.html`));
        if(kind==='navigation') url.searchParams.set('s2s-atlas', '#s2s=1&selected=node-main');
        await page.goto(url.href);
        assert.deepEqual(errors, [], kind+' initialization');
        assert.equal(await page.locator('html').getAttribute('data-ready'), 'true');
        assert.equal(await page.locator('#s2s-data').count(), 1);
        assert((await page.locator('#offline-note').textContent()).length>0);
        if(kind==='authored') {
          assert.equal(await page.locator('.authored-evidence').count(), 1);
          assert.equal(await page.locator('.authored-picture .rule-figure.comparison').count(), 2);
          assert.deepEqual(await page.locator('.authored-picture .rule-case').evaluateAll(nodes => nodes.map(node=>node.hidden)), [false,false]);
          assert.equal(await page.locator('.authored-picture .case-controls').evaluate(node=>node.hidden), true);
          assert.equal(await page.locator('.authored-picture .case-controls button').getAttribute('aria-pressed'), 'false');
          assert.equal(await page.locator('.authored-picture textarea').inputValue(), 'Complete explanation');
        } else if(kind==='comparison') {
          const cases = page.locator('#figure-cancellation > .rule-case');
          const buttons = page.locator('#figure-cancellation > .case-controls > button');
          assert.deepEqual(await cases.evaluateAll(nodes => nodes.map(node=>node.hidden)), [false,true]);
          await buttons.nth(1).focus();
          await page.keyboard.press('Enter');
          assert.deepEqual(await cases.evaluateAll(nodes => nodes.map(node=>node.hidden)), [true,false]);
          assert.deepEqual(await buttons.evaluateAll(nodes => nodes.map(node=>node.getAttribute('aria-pressed'))), ['false','true']);
          await buttons.first().click();
          assert.deepEqual(await cases.evaluateAll(nodes => nodes.map(node=>node.hidden)), [false,true]);
        } else if(kind==='incomplete') {
          assert.deepEqual(await page.locator('#figure-cancellation > .rule-case').evaluateAll(nodes => nodes.map(node=>node.hidden)), [false,false]);
          assert.equal(await page.locator('.incomplete-controls').evaluate(node=>node.hidden), true);
        } else if(kind==='navigation') {
          assert.deepEqual(await page.locator('.authored-picture a[data-layer]').evaluateAll(nodes => nodes.map(node=>node.getAttribute('href'))),
            ['#scene-cancellation-outcome', '#scene-cancellation-outcome']);
          await page.locator('.authored-picture svg a').click();
          assert.equal(new URL(page.url()).hash, '#scene-cancellation-outcome');
        } else if(kind==='copy') {
          const buttons = page.locator('.authored-picture button.copy-command');
          const outcome = await page.locator('.authored-picture output').textContent();
          await buttons.first().click();
          assert.deepEqual(await page.evaluate(() => window.clipboardWrites), [outcome]);
          await buttons.nth(1).click();
          assert.deepEqual(await page.evaluate(() => window.clipboardWrites), [outcome, outcome]);
          assert.equal(await page.locator('#announcement').textContent(), '');
        }
        const initialTheme = await page.locator('html').getAttribute('data-theme');
        await page.locator('#theme-toggle').click();
        assert.notEqual(await page.locator('html').getAttribute('data-theme'), initialTheme);
        const copy = page.locator('#explanation > .primer-intro > .links > .copy-command');
        await copy.click();
        assert.equal(await page.evaluate(() => window.copiedCommand), await copy.getAttribute('data-command'));
        assert((await page.locator('#announcement').textContent()).length>0);
        if(kind==='copy') {
          const writes = await page.evaluate(() => window.clipboardWrites);
          for(const value of [null, '', '   ']) {
            await copy.evaluate((button, command) => {
              if(command===null) button.removeAttribute('data-command');
              else button.setAttribute('data-command', command);
            }, value);
            await copy.click();
            assert.deepEqual(await page.evaluate(() => window.clipboardWrites), writes);
          }
        }
        assert.deepEqual(errors, []);
        await context.close();
        checks++;
      }
    }
    console.log(`${checks} browser scenarios passed: bilingual round trips, themes, offline/static content, authored control isolation and legacy controls.`);
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
