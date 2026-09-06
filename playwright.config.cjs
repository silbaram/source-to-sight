const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({
  testDir:'./tests',testMatch:'**/*.spec.cjs',fullyParallel:true,workers:2,
  timeout:30000,expect:{timeout:5000},reporter:'list',
  use:{browserName:'chromium',headless:true},
  projects:[
    {name:'desktop',use:{viewport:{width:1440,height:1000}}},
    {name:'narrow',use:{viewport:{width:390,height:844},reducedMotion:'reduce'}}
  ]
});
