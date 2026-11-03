// Browser regression against a real isolated local backend. No production bridge changes.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');const http=require('node:http');const fs=require('node:fs/promises');const path=require('node:path');const os=require('node:os');
(async()=>{
 const data=await fs.mkdtemp(path.join(os.tmpdir(),'aios-ui-'));const token=require('node:crypto').randomBytes(32).toString('hex');
 const server=http.createServer(async(req,res)=>{try{const relative=decodeURIComponent(req.url.split('?')[0]);const file=path.resolve('dist','.'+(relative==='/'?'/index.html':relative));if(!file.startsWith(path.resolve('dist')+path.sep))throw Error();const bytes=await fs.readFile(file);res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html');res.end(bytes);}catch{res.statusCode=404;res.end();}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const backend=spawn(process.env.AIOS_PYTHON||'.venv/bin/python',['backend/run.py'],{env:{...process.env,AIOS_DATA:data,AIOS_SESSION_TOKEN:token,AIOS_PORT:'19876'},stdio:'ignore'});
 let browser;
 try{
  const request=async(method,route,body)=>{const r=await fetch('http://127.0.0.1:19876'+route,{method,headers:{Authorization:'Bearer '+token,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok)throw Error(await r.text());return r.json();};
  let ready=false;for(let i=0;i<100;i++){try{await request('GET','/health');ready=true;break;}catch{}await new Promise(r=>setTimeout(r,100));}if(!ready)throw Error('Backend failed');
  browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
  const page=await browser.newPage({viewport:{width:1500,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.stack||e.message));
  await page.exposeFunction('desktopRequest',request);
  await page.addInitScript(()=>{window.company={request:(...args)=>window.desktopRequest(...args),upload:()=>Promise.reject(Error('Native dialog tested in desktop')),download:()=>Promise.resolve(),export:()=>Promise.resolve(),invoice:()=>Promise.resolve()};});
  await page.goto('http://127.0.0.1:'+server.address().port);await page.getByLabel('Create an owner password (12+ characters)').fill('ui-smoke-test-password');await page.getByRole('button',{name:'Create local workspace'}).click();
  await page.getByRole('heading',{name:'Company overview'}).waitFor();await page.waitForTimeout(3000);
  const canvas=page.locator('canvas');await canvas.waitFor();await canvas.hover();await page.mouse.wheel(0,100);await page.mouse.move(700,400);await page.mouse.down();await page.mouse.move(760,430,{steps:8});await page.mouse.up();
  await fs.mkdir('docs/screenshots',{recursive:true});await page.screenshot({path:'docs/screenshots/office.png',fullPage:true});
  await page.getByRole('button',{name:'Customers',exact:true}).click();await page.getByLabel('Name',{exact:true}).fill('UI integration customer');await page.getByLabel('Email',{exact:true}).fill('ui-test@example.com');await page.getByRole('button',{name:'Save customer'}).click();await page.getByRole('cell',{name:'ui-test@example.com',exact:true}).waitFor();
  await page.getByRole('button',{name:'Finance',exact:true}).click();await page.getByLabel('Amount',{exact:true}).fill('123.45');await page.getByLabel('Description',{exact:true}).fill('UI test payment');await page.getByLabel('Payment / receipt reference').fill('integration test receipt');await page.getByLabel('I confirm this transaction occurred').check();await page.getByRole('button',{name:'Record transaction'}).click();await page.getByText('UI test payment',{exact:true}).waitFor();
  const stats=await request('GET','/stats');if(stats.finance.USD.revenue_minor!==12345)throw Error('UI finance persistence failed');
  await page.getByRole('button',{name:'AI team',exact:true}).click();await page.getByRole('button',{name:'05 Sales Agent Ready'}).click();await page.getByLabel('Business objective').fill('Draft an integration test proposal');await page.getByRole('button',{name:'Run task',exact:true}).click();await page.getByText('Draft an integration test proposal',{exact:true}).waitFor();
  if(errors.length)throw Error('Renderer errors: '+errors.join('; '));console.log('UI smoke passed: owner setup, live 3D office, camera interaction, CRM persistence, finance persistence, task creation.');
 }finally{await browser?.close();backend.kill();server.close();await fs.rm(data,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
