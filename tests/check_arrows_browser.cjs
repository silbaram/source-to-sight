'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.argv[3]||'playwright');

const styleOf=locator=>locator.evaluate(group=>{
  const route=group.querySelector('.edge-path'),style=getComputedStyle(route);
  const markerId=route.getAttribute('marker-end').match(/#([^\)]+)/)[1];
  const head=document.getElementById(markerId).querySelector('path'),headStyle=getComputedStyle(head);
  return {stroke:style.stroke,width:Number.parseFloat(style.strokeWidth),dash:style.strokeDasharray,
    cap:style.strokeLinecap,markerId,headFill:headStyle.fill,headStroke:headStyle.stroke,
    headShape:head.getAttribute('d'),label:group.querySelector('.edge-label').textContent,
    accessible:group.getAttribute('aria-label')};
});
const meaning=style=>({stroke:style.stroke,dash:style.dash,cap:style.cap,markerId:style.markerId,
  headFill:style.headFill,headStroke:style.headStroke,headShape:style.headShape,label:style.label,accessible:style.accessible});

async function checkContrast(page,phase){
  const results=await page.evaluate(()=>{
    const rgba=value=>{
      const parts=value.match(/[\d.]+/g).map(Number);
      return [...parts.slice(0,3),parts[3]??1];
    };
    const over=(foreground,background)=>foreground.slice(0,3).map((channel,index)=>channel*foreground[3]+background[index]*(1-foreground[3]));
    const luminance=color=>color.map(channel=>{const value=channel/255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4}).reduce((value,channel,index)=>value+channel*[.2126,.7152,.0722][index],0);
    const ratio=(foreground,background)=>{const a=luminance(foreground),b=luminance(background);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
    const background=element=>{
      const layers=[];
      for(let node=element;node;node=node.parentElement)layers.push(rgba(getComputedStyle(node).backgroundColor));
      return layers.reverse().reduce((color,layer)=>over(layer,color),[255,255,255]);
    };
    const canvas=document.getElementById('canvas'),base=background(canvas);
    // Regions are siblings behind the SVG, so walking SVG ancestors alone
    // misses their surfaces. Include every rendered region's real background.
    const surfaces=[base,...[...document.querySelectorAll('.map-region')].map(region=>over(rgba(getComputedStyle(region).backgroundColor),base))];
    const measured=[];
    for(const edge of document.querySelectorAll('.edge')){
      const route=edge.querySelector('.edge-path'),style=getComputedStyle(route);
      const markerId=route.getAttribute('marker-end').match(/#([^\)]+)/)[1];
      const headStyle=getComputedStyle(document.getElementById(markerId).querySelector('path'));
      const rect=edge.querySelector('.edge-label-bg'),label=edge.querySelector('.edge-label');
      for(const [index,surface] of surfaces.entries()){
        measured.push({kind:'line',id:edge.dataset.id,surface:index,ratio:ratio(over(rgba(style.stroke),surface),surface),minimum:3});
        const headColor=headStyle.fill==='none'?headStyle.stroke:headStyle.fill;
        measured.push({kind:'head',id:edge.dataset.id,surface:index,ratio:ratio(over(rgba(headColor),surface),surface),minimum:3});
        const labelBackground=over(rgba(getComputedStyle(rect).fill),surface);
        measured.push({kind:'label',id:edge.dataset.id,surface:index,ratio:ratio(over(rgba(getComputedStyle(label).fill),labelBackground),labelBackground),minimum:4.5});
      }
    }
    for(const sample of document.querySelectorAll('.legend-arrow')){
      const surface=background(sample);
      measured.push({kind:'legend',id:sample.classList.value,ratio:ratio(over(rgba(getComputedStyle(sample).color),surface),surface),minimum:3});
      const text=sample.parentElement.querySelector('span');
      if(text)measured.push({kind:'legend-label',id:sample.classList.value,ratio:ratio(over(rgba(getComputedStyle(text).color),surface),surface),minimum:4.5});
    }
    return measured;
  });
  assert(results.length>0);
  assert(results.every(item=>item.ratio>=item.minimum),phase+' contrast: '+JSON.stringify(results.filter(item=>item.ratio<item.minimum)));
}

(async()=>{
  const browser=await chromium.launch({headless:true,...(process.env.S2S_CHROMIUM_EXECUTABLE?{executablePath:process.env.S2S_CHROMIUM_EXECUTABLE}:{})});
  let checks=0;
  try{for(const language of ['ko','en'])for(const width of [1440,390])for(const dark of [false,true]){
    const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
    const page=await context.newPage(),errors=[],network=[];
    page.on('pageerror',error=>errors.push(error.message));
    page.on('request',request=>{if(/^https?:/.test(request.url()))network.push(request.url())});
    await page.goto(pathToFileURL(path.resolve(process.argv[2],language,'arrows.html')).href);
    await page.waitForSelector('html[data-ready=true]');
    if(dark)await page.locator('#theme-toggle').click();
    assert.equal(await page.locator('#connections').isVisible(),false,'The default operation board stays free of arrows');
    await page.locator('#show-connections').click();
    const edge=id=>page.locator('.edge[data-id="edge-'+id+'"]');
    const original=await Promise.all([0,1,2,3,4].map(id=>styleOf(edge(id))));
    assert.equal(new Set(original.slice(0,4).map(style=>style.stroke)).size,4,'Calls, data, dependencies and uncertainty have distinct colors');
    assert.equal(original[3].stroke,original[4].stroke,'Uncertain and unverified connections share the warning color');
    assert.equal(original[0].dash,'none');assert.equal(original[1].dash,'none');
    assert.notEqual(original[2].dash,'none','Dependencies have a dashed line');
    assert.notEqual(original[3].dash,'none','Review uncertainty has a dotted line');
    assert.notEqual(original[2].dash,original[3].dash,'Dependency and uncertainty do not share one dash pattern');
    assert.equal(original[3].dash,original[4].dash);
    assert.equal(original[3].cap,'round','The short uncertainty pattern renders as dots');
    assert.equal(original[2].headFill,'none','Dependencies have an open arrowhead');
    assert.equal(original[4].headFill,'none','An unverified dependency retains its open arrowhead');
    for(const id of [0,1,3])assert.equal(original[id].headFill,original[id].stroke,'Filled arrowhead and line use the same relationship color');
    for(const id of [2,4])assert.equal(original[id].headStroke,original[id].stroke,'Open arrowhead and line use the same relationship color');
    const caption=language==='ko'?'주문 처리':'Process order';
    assert.equal(new Set(original.slice(0,3).map(style=>style.label)).size,3,'Text distinguishes different relations with an identical business caption');
    for(const item of original){
      assert(item.label.includes(caption),'The reviewed business caption stays visible');
      assert(item.label.length>caption.length,'Every arrow names its relationship as well as its caption');
      assert(item.accessible.includes(caption),'The accessible name includes the reviewed caption');
    }
    for(const id of [3,4]){
      assert(original[id].label.includes('?'),'Uncertainty remains visible without color');
      assert(original[id].accessible.toLowerCase().includes(language==='ko'?(id===3?'추정':'미확인'):(id===3?'uncertain':'unverified')),'The accessible name communicates the review status');
    }
    for(const [id,kind] of [[0,'normal'],[1,'data'],[2,'structural'],[3,'uncertain']]){
      const legend=page.locator('.legend-arrow.'+kind).first();
      const sample=await legend.evaluate(svg=>({color:getComputedStyle(svg).color,
        dash:getComputedStyle(svg.querySelector('.legend-arrow-shaft')).strokeDasharray,
        fill:getComputedStyle(svg.querySelector('.legend-arrow-tip')).fill}));
      assert.equal(sample.color,original[id].stroke,kind+' legend matches the actual line color');
      assert.equal(sample.dash,original[id].dash,kind+' legend matches the actual line pattern');
      if(kind==='structural')assert.equal(sample.fill,'none','The dependency legend also has an open arrowhead');
    }
    assert.equal(await page.locator('#arrow-active').count(),0,'Selection does not introduce a second semantic arrow color');
    await checkContrast(page,'Initial '+language+'/'+width+'/'+dark);
    for(const id of [0,1,2,3,4]){
      await page.keyboard.press('Tab');await edge(id).focus();
      assert(await edge(id).evaluate(node=>node.matches(':focus-visible')),'Keyboard focus is visibly represented');
      const focused=await styleOf(edge(id));
      assert.deepEqual(meaning(focused),meaning(original[id]),'Keyboard focus preserves relation '+id);
      assert(focused.width>original[id].width,'Keyboard focus increases line weight');
      await edge(id).press('Enter');
      assert.equal(await page.locator('#panel.open').count(),1);
      assert((await edge(id).getAttribute('class')).split(' ').includes('active'));
      const selected=await styleOf(edge(id));
      assert.deepEqual(meaning(selected),meaning(original[id]),'Selection preserves relation '+id);
      assert(selected.width>original[id].width,'Selection increases line weight');
      await checkContrast(page,'Selected edge '+id);
      await page.locator('#close-panel').click();
    }
    await page.locator('#process-groups button').first().click();
    assert.equal(await page.locator('.map-region.selected').count(),1,'The selected group surface is exercised');
    await checkContrast(page,'Selected group');
    await page.locator('#close-panel').click();
    await page.locator('#workflow').click();
    for(const id of [0,1,2,3,4]){
      await page.locator('#step-picker').selectOption(String(id));
      await page.locator('#play').click();
      assert.equal(await page.locator('#play').getAttribute('aria-pressed'),'true');
      const playing=await styleOf(edge(id));
      assert.deepEqual(meaning(playing),meaning(original[id]),'Playback preserves relation '+id);
      assert(playing.width>original[id].width,'Playback increases line weight');
      await checkContrast(page,'Playing edge '+id);
      await page.locator('#play').click();
    }
    if(language==='en'&&width===1440&&!dark){
      await page.emulateMedia({reducedMotion:'no-preference'});
      for(const id of [0,1]){
        await page.locator('#step-picker').selectOption(String(id));await page.locator('#play').click();
        await edge(id).locator('.transfer-core').waitFor();
        assert.equal(await edge(id).locator('.transfer-core').evaluate(node=>getComputedStyle(node).fill),original[id].stroke,'The moving token keeps its relationship color');
        await page.locator('#play').click();
      }
      for(const id of [2,3,4]){
        await page.locator('#step-picker').selectOption(String(id));await page.locator('#play').click();
        assert.equal(await page.locator('.flow-token').count(),0,'Structural or unverified relations never imply a confirmed transfer');
        await page.locator('#play').click();
      }
    }
    await page.locator('#structure').click();
    assert(await page.locator('#legend').evaluate(node=>node.scrollWidth<=node.clientWidth+1),'The relationship legend wraps in the viewport');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'The page fits the viewport');
    if(language==='ko'){
      await edge(1).focus();await edge(1).press('Enter');await page.locator('#close-panel').click();
      await page.locator('#zoom-level').click();
      await edge(1).evaluate(group=>{
        const canvas=document.getElementById('canvas'),frame=canvas.getBoundingClientRect();
        const connection=group.querySelector('.edge-path').getBoundingClientRect();
        canvas.scrollLeft+=(connection.left+connection.right-frame.left-frame.right)/2;
        canvas.scrollTop+=(connection.top+connection.bottom-frame.top-frame.bottom)/2;
      });
      await page.locator('#canvas').scrollIntoViewIfNeeded();
      await page.locator('#canvas').screenshot({path:path.resolve(process.argv[2],'arrows-'+width+'-'+(dark?'dark':'light')+'.png')});
      await page.locator('#legend').screenshot({path:path.resolve(process.argv[2],'arrow-legend-'+width+'-'+(dark?'dark':'light')+'.png')});
    }
    assert.deepEqual(errors,[]);assert.deepEqual(network,[]);
    await context.close();checks++;
  }}finally{await browser.close()}
  console.log(checks+' arrow journeys passed: relation labels, line/head/legend consistency, stable selection/focus/playback, uncertainty, contrast and offline rendering.');
})().catch(error=>{console.error(error);process.exitCode=1});
