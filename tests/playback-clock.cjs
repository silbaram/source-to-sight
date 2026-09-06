const {expect}=require('@playwright/test');

async function settleCamera(page){
  for(let i=0;i<40;i++){
    if(!await page.locator('#canvas').evaluate(n=>n.classList.contains('camera-moving')))return;
    await page.clock.runFor(16);
  }
  expect(await page.locator('#canvas').evaluate(n=>n.classList.contains('camera-moving'))).toBe(false);
}

async function reachStep(page,index,total){
  const wanted=String(index).padStart(2,'0')+' / '+String(total).padStart(2,'0');
  for(let i=0;i<360;i++){
    if(await page.locator('#step-count').textContent()===wanted){await settleCamera(page);return;}
    await page.clock.runFor(50);
  }
  await expect(page.locator('#step-count')).toHaveText(wanted);
}

module.exports={settleCamera,reachStep};
