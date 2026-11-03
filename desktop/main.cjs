const {app,BrowserWindow,ipcMain,dialog,protocol}=require('electron');
const {spawn}=require('node:child_process');
const {randomBytes}=require('node:crypto');
const path=require('node:path');
const fs=require('node:fs/promises');
const net=require('node:net');
protocol.registerSchemesAsPrivileged([{scheme:'aios-media',privileges:{standard:true,secure:true,stream:true,supportFetchAPI:true}}]);
let backend,win,port,token;const base=()=>`http://127.0.0.1:${port}`;
const allowed=/^\/(health|auth|contacts|export|gmail|campaigns|jobs|media|exports|settings|finance|records|invoices|stats|plans|videos|permissions|music|analytics)(\/[^?#]*)?(\?[^#]*)?$/;
function senderOK(event){if(!win||event.sender!==win.webContents)throw Error('Unknown sender');}
async function request(method,route,body){
 if(!['GET','POST','PUT','DELETE'].includes(method)||typeof route!=='string'||!allowed.test(route)||route.includes('..')||route.includes('%'))throw Error('Invalid request');
 const response=await fetch(base()+route,{method,headers:{Authorization:`Bearer ${token}`,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(180000)});
 if(!response.ok){let msg=await response.text();throw Error(msg.slice(0,500));}return response.json();
}
async function freePort(){return new Promise((resolve,reject)=>{const server=net.createServer();server.listen(0,'127.0.0.1',()=>{const p=server.address().port;server.close(()=>resolve(p));});server.on('error',reject);});}
app.whenReady().then(async()=>{
 if(!app.requestSingleInstanceLock()){app.quit();return;}
 token=randomBytes(48).toString('hex');port=await freePort();
 const executable=app.isPackaged?path.join(process.resourcesPath,'backend','aios-backend.exe'):(process.env.AIOS_PYTHON||'python');
 const args=app.isPackaged?[]:[path.join(__dirname,'../backend/run.py')];
 backend=spawn(executable,args,{windowsHide:true,env:{...process.env,AIOS_PORT:String(port),AIOS_SESSION_TOKEN:token,AIOS_DATA:path.join(app.getPath('userData'),'data')},stdio:'ignore'});
 let startupError;backend.on('error',e=>{startupError=e;});
 let ready=false;
 for(let i=0;i<120;i++){if(startupError)break;try{await request('GET','/health');ready=true;break;}catch{}await new Promise(r=>setTimeout(r,500));}
 if(!ready){dialog.showErrorBox('Backend startup failed',startupError?.message||'Local service did not start. See installation troubleshooting.');app.quit();return;}
 win=new BrowserWindow({width:1500,height:980,minWidth:1050,minHeight:720,backgroundColor:'#070c19',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true,webSecurity:true}});
 win.webContents.setWindowOpenHandler(()=>({action:'deny'}));win.webContents.on('will-navigate',e=>e.preventDefault());
 win.webContents.session.setPermissionRequestHandler((_w,_p,cb)=>cb(false));
 ipcMain.handle('api',(event,{method,path:route,body})=>{senderOK(event);return request(method,route,body);});
 ipcMain.handle('upload',async event=>{senderOK(event);const result=await dialog.showOpenDialog(win,{properties:['openFile'],filters:[{name:'Video or contacts',extensions:['mp4','mov','mkv','csv','xlsx','mp3','wav','m4a']}]});if(result.canceled)return null;
 const file=result.filePaths[0],ext=path.extname(file).toLowerCase();const stat=await fs.stat(file);if(stat.size>2e9)throw Error('Maximum 2 GB');const bytes=await fs.readFile(file);const form=new FormData();form.append('file',new Blob([bytes]),path.basename(file));
 const isMusic=['.mp3','.wav','.m4a'].includes(ext);if(isMusic){const approval=await dialog.showMessageBox(win,{type:'question',buttons:['Cancel','I have a valid license'],defaultId:0,cancelId:0,message:'Confirm you own this music or have a license covering its use in your video.'});if(approval.response!==1)return null;}const route=isMusic?'/music?licensed=true':['.csv','.xlsx'].includes(ext)?'/contacts/import':'/media';const r=await fetch(base()+route,{method:'POST',headers:{Authorization:`Bearer ${token}`},body:form});if(!r.ok)throw Error((await r.text()).slice(0,500));return r.json();});
 ipcMain.handle('download',async(event,name)=>{senderOK(event);if(!/^video-\d+\.(mp4|json|srt)$/.test(name))throw Error('Invalid output');const save=await dialog.showSaveDialog(win,{defaultPath:name});if(save.canceled)return;const r=await fetch(base()+'/exports/'+name,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw Error('Output unavailable');await fs.writeFile(save.filePath,Buffer.from(await r.arrayBuffer()));return true;});
 ipcMain.handle('invoice',async(event,id)=>{senderOK(event);if(!Number.isSafeInteger(id)||id<1)throw Error('Invalid invoice');const save=await dialog.showSaveDialog(win,{defaultPath:`invoice-${id}.pdf`});if(save.canceled)return;const r=await fetch(base()+`/invoices/${id}/print`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw Error('Invoice missing');const html=await r.text();const pdfWindow=new BrowserWindow({show:false,webPreferences:{sandbox:true,nodeIntegration:false,contextIsolation:true}});try{await pdfWindow.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'+html));const pdf=await pdfWindow.webContents.printToPDF({pageSize:'A4',printBackground:true});await fs.writeFile(save.filePath,pdf);}finally{pdfWindow.destroy();}return true;});
 ipcMain.handle('export',async(event,{kind,format})=>{senderOK(event);if(!['contacts','leads','finance','analytics'].includes(kind)||!['csv','xlsx'].includes(format))throw Error('Invalid export');const save=await dialog.showSaveDialog(win,{defaultPath:`${kind}.${format}`});if(save.canceled)return;const r=await fetch(`${base()}/export/${kind}?format=${format}`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw Error('Export failed');await fs.writeFile(save.filePath,Buffer.from(await r.arrayBuffer()));return true;});
 protocol.handle('aios-media',async request=>{const url=new URL(request.url);const name=url.pathname.slice(1);if(url.hostname!=='exports'||!/^video-\d+\.mp4$/.test(name))return new Response('Invalid media',{status:403});const response=await fetch(base()+'/exports/'+name,{headers:{Authorization:`Bearer ${token}`,...(request.headers.has('Range')?{Range:request.headers.get('Range')}:{})}});return new Response(response.body,{status:response.status,headers:response.headers});});
 await win.loadFile(path.join(__dirname,'../dist/index.html'));
});
app.on('window-all-closed',()=>app.quit());app.on('before-quit',()=>backend?.kill());
