const {test,expect}=require('@playwright/test');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const cases=JSON.parse(fs.readFileSync(path.join(root,'eval/m1/cases.json'),'utf8'));
const url=id=>pathToFileURL(path.join(root,'build/m1',id+'.html')).href;

test.beforeEach(async({context})=>context.setOffline(true));

for(const item of cases)test('M1 '+item.id+' renders source evidence and sound geometry',async({page},info)=>{
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(/^https?:/.test(r.url()))requests.push(r.url())});
  await page.goto(url(item.id));
  await expect(page.locator('html')).toHaveAttribute('data-ready','true');
  await expect(page.locator('html')).toHaveAttribute('data-viewer','canvas');
  await page.evaluate(()=>document.fonts.ready);
  const result=await page.evaluate(()=>{
    const data=JSON.parse(document.getElementById('s2s-data').textContent);
    const rects=[...document.querySelectorAll('.node')].map(n=>({id:n.dataset.id,r:n.getBoundingClientRect()}));
    const collisions=[],endpoints=[],crossings=[];
    for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){
      const a=rects[i].r,b=rects[j].r;
      if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2)collisions.push([rects[i].id,rects[j].id]);
    }
    for(const group of document.querySelectorAll('.edge')){
      const edge=data.edges.find(e=>e.id===group.dataset.id),route=group.querySelector('.edge-path'),length=route.getTotalLength();
      for(const [id,distance] of [[edge.from,0],[edge.to,length]]){
        const r=rects.find(n=>n.id===id).r,p=route.getPointAtLength(distance).matrixTransform(route.getScreenCTM()),x=p.x,y=p.y;
        if(!(x>=r.left-3&&x<=r.right+3&&y>=r.top-3&&y<=r.bottom+3&&Math.min(Math.abs(x-r.left),Math.abs(x-r.right),Math.abs(y-r.top),Math.abs(y-r.bottom))<=3))endpoints.push([edge.id,id]);
      }
      for(const n of rects){if([edge.from,edge.to].includes(n.id))continue;
        for(let d=0;d<length;d+=3){const p=route.getPointAtLength(d).matrixTransform(route.getScreenCTM()),x=p.x,y=p.y,r=n.r;
          if(x>r.left+2&&x<r.right-2&&y>r.top+2&&y<r.bottom-2){crossings.push([edge.id,n.id]);break;}}
      }
    }
    return {collisions,endpoints,crossings,overflow:document.documentElement.scrollWidth>innerWidth,
      evidence:data.evidence.every(e=>e.locationStatus==='passed'&&!('anchorText'in e)),humanReviewed:data.provenance.humanReviewed};
  });
  expect(errors).toEqual([]);expect(requests).toEqual([]);
  expect(result).toEqual({collisions:[],endpoints:[],crossings:[],overflow:false,evidence:true,humanReviewed:false});
  await page.locator('.node').first().click();
  await expect(page.locator('#panel')).toBeVisible();
  await expect(page.locator('#panel .location').first()).toBeVisible();
  await page.screenshot({path:path.join(root,'build/m1/qa',info.project.name+'-'+item.id+'.png'),fullPage:true});
});

test('M1 small utility and unordered event graph do not invent playback',async({page})=>{
  await page.goto(url('utility-strip'));await expect(page.locator('.node')).toHaveCount(1);await expect(page.locator('#player')).toBeHidden();
  await page.goto(url('event-receivers'));await expect(page.locator('#player')).toBeHidden();
  const graph=await page.locator('#s2s-data').textContent();
  const data=JSON.parse(graph);expect(data.nodes.find(n=>n.id==='receiver').displayStatus).toBe('uncertain');
  expect(data.edges.find(e=>e.id==='send-receiver').displayStatus).toBe('confirmed');
  expect(data.analysis.profiles).toEqual(['data-event','library-sdk','framework-plugin']);
});

test('M1 callback walkthrough retains its condition and state evidence',async({page})=>{
  await page.goto(url('library-eviction'));
  await page.locator('#workflow').click();
  await page.locator('#next').click();await expect(page.locator('#caption')).toContainText('새 항목');
  await page.locator('.node[data-id=buffer]').click();await expect(page.locator('#panel')).toContainText('퇴출 콜백이 등록되어 있고');
});
