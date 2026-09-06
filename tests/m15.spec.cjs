const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const run=path.resolve(root,process.env.S2S_EVAL_DIR||'build/eval/m15');
const cases=JSON.parse(fs.readFileSync(path.join(root,'eval/cases.json'),'utf8')).cases;

test.beforeEach(async({context})=>context.setOffline(true));

for(const item of cases)test('M1.5 '+item.id+' uses the common offline viewer',async({page})=>{
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
  await page.goto(pathToFileURL(path.join(run,item.id+'.html')).href);
  await expect(page.locator('html')).toHaveAttribute('data-ready','true');
  await expect(page.locator('html')).toHaveAttribute('data-viewer','canvas');
  await page.evaluate(()=>document.fonts.ready);
  const ref=JSON.parse(fs.readFileSync(path.join(root,'eval',item.expectation),'utf8'));
  const state=await page.evaluate(()=>{
    const data=JSON.parse(document.getElementById('s2s-data').textContent);
    const nodes=[...document.querySelectorAll('.node')].map(n=>({id:n.dataset.id,r:n.getBoundingClientRect()}));
    const overlaps=[],endpoints=[];
    for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
      const a=nodes[i].r,b=nodes[j].r;
      if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2)overlaps.push([nodes[i].id,nodes[j].id]);
    }
    for(const group of document.querySelectorAll('.edge')){
      const e=data.edges.find(e=>e.id===group.dataset.id),p=group.querySelector('.edge-path'),length=p.getTotalLength();
      for(const [id,d] of [[e.from,0],[e.to,length]]){
        const r=nodes.find(n=>n.id===id).r,point=p.getPointAtLength(d).matrixTransform(p.getScreenCTM());
        if(!(point.x>=r.left-3&&point.x<=r.right+3&&point.y>=r.top-3&&point.y<=r.bottom+3))endpoints.push([e.id,id]);
      }
    }
    return {status:data.analysis.status,overlaps,endpoints,overflow:document.documentElement.scrollWidth>innerWidth,
      safeEvidence:data.evidence.every(e=>e.locationStatus==='passed'&&!('anchorText' in e)),humanReviewed:data.provenance.humanReviewed};
  });
  expect(ref.statuses).toContain(state.status);
  expect(state.overlaps).toEqual([]);expect(state.endpoints).toEqual([]);
  expect(state.overflow).toBe(false);expect(state.safeEvidence).toBe(true);expect(state.humanReviewed).toBe(false);
  if(ref.noScenarios)await expect(page.locator('#player')).toBeHidden();
  await page.locator('.node').first().click();
  await expect(page.locator('#panel')).toBeVisible();
  await expect(page.locator('#panel .location').first()).toBeVisible();
  expect(errors).toEqual([]);expect(requests).toEqual([]);
});
