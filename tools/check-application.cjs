const {chromium}=require(process.argv[2] || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const errors=[];const base='http://127.0.0.1:5175/';
 try{
  const page=await browser.newPage({viewport:{width:1520,height:1080}});
  page.on('pageerror',error=>errors.push(error.message));
  async function login(name){await page.getByLabel('Username',{exact:true}).fill(name);await page.getByLabel('Password',{exact:true}).fill('harbor-demo');await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.getByRole('heading',{name:'Purchase requisitions',exact:true}).waitFor()}
  async function logout(){await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('heading',{name:'Sign in to procurement',exact:true}).waitFor()}
  const title='Pump seals · browser '+Date.now();
  await page.goto(base+'?theme=dark');await login('aina');
  await page.getByRole('button',{name:'Create PR',exact:true}).click();
  await page.getByLabel('Title',{exact:true}).fill(title);
  await page.getByLabel('Required date',{exact:true}).fill('2026-12-01');
  await page.getByLabel('Vessel',{exact:true}).fill('MV Harbor One');
  await page.getByLabel('Location',{exact:true}).fill('Port Klang');
  await page.getByLabel('Business purpose',{exact:true}).fill('Replace worn pump seals before departure');
  await page.getByLabel('Suggested supplier',{exact:false}).fill('Demo Marine Supply');
  await page.getByLabel('Description',{exact:true}).fill('Pump seals');
  await page.getByLabel('Quantity',{exact:true}).fill('10');
  await page.getByLabel('Unit estimate (MYR)',{exact:true}).fill('200.00');
  await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await page.getByRole('heading',{name:title,exact:true}).waitFor();
  assert.match(await page.locator('.total').innerText(),/2,000/);
  // Browser refresh must reauthenticate from HttpOnly cookie and read PostgreSQL.
  await page.reload();await page.getByRole('button',{name:new RegExp('PR-.*'+title.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).click();
  await page.getByRole('button',{name:'Submit for approval',exact:true}).click();
  await page.getByText('Submitted to Ben',{exact:true}).waitFor();
  await logout();await login('ben');
  await page.getByRole('button').filter({hasText:title}).click();
  await page.getByRole('button',{name:'Return for changes',exact:true}).click();
  await page.getByLabel('Reason for returning',{exact:true}).fill('Confirm the required quantity');
  await page.getByRole('button',{name:'Confirm return',exact:true}).click();
  await page.getByText('Returned to the requester',{exact:true}).waitFor();
  await logout();await login('aina');
  await page.getByRole('button').filter({hasText:title}).click();
  await page.getByRole('button',{name:'Edit draft',exact:true}).click();
  await page.getByLabel('Business purpose',{exact:true}).fill('Confirmed 10 replacement pump seals before departure');
  await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await page.getByRole('heading',{name:title,exact:true}).waitFor();
  await page.getByRole('button',{name:'Submit for approval',exact:true}).click();
  await page.getByText('Submitted to Ben',{exact:true}).waitFor();
  await logout();await login('ben');
  await page.getByRole('button').filter({hasText:title}).click();
  await page.getByRole('button',{name:'Approve PR',exact:true}).click();
  await page.getByText('PR approved',{exact:true}).waitFor();
  assert.match(await page.locator('.activity').innerText(),/Approved PR/);
  const dir=require('node:path').resolve('mockups')+require('node:path').sep;
  await page.screenshot({path:dir+'application-pr-dark.png',fullPage:true});
  await page.getByRole('button',{name:'Light theme',exact:true}).click();
  assert.match(await page.locator('html').getAttribute('data-color-mode'),/light/);
  await page.screenshot({path:dir+'application-pr-light.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:dir+'application-pr-mobile.png',fullPage:true});
  await logout();await login('chloe');
  await page.getByRole('button').filter({hasText:title}).click();
  assert.equal(await page.getByRole('button',{name:'Approve PR',exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Create PR',exact:true}).count(),0);
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({status:'passed',record_title:title,checks:['login','save MYR 2000 draft','reload persists record/session','submit','return with reason','edit and resubmit','Ben approves','audit visible','light/dark','390px no page overflow','buyer read-only'],page_errors:errors},null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
