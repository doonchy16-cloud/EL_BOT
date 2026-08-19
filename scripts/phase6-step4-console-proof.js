'use strict';
const fs=require('fs');const os=require('os');const path=require('path');const {app}=require('electron');
const target=process.argv[2]||path.join('data','phase6-step4','console-proof.json');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'el-step4-console-'));app.setPath('userData',temp);
let captured=null;app.on('browser-window-created',(_e,w)=>{captured=w;});
require('../⚡/⚡');
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
async function waitFor(fn,timeout=30000){const end=Date.now()+timeout;while(Date.now()<end){try{const v=await fn();if(v)return v;}catch(_){}await sleep(100);}throw new Error('proof timeout');}
(async()=>{await app.whenReady();const win=await waitFor(async()=>captured&&!captured.isDestroyed()?captured:null);await waitFor(()=>win.webContents.executeJavaScript("Boolean(document.getElementById('el-admin-entry'))",true));
await win.webContents.executeJavaScript(`(async()=>{const e=document.getElementById('el-admin-entry');for(let i=0;i<5;i++){e.dispatchEvent(new MouseEvent('click',{bubbles:true}));await new Promise(r=>setTimeout(r,80));}return true;})()`,true);
await waitFor(()=>win.webContents.executeJavaScript("Boolean(document.getElementById('el-admin-auth-backdrop'))",true));
const fixture=['console','proof','fixture','credential','2026'].join('-');
await win.webContents.executeJavaScript(`(()=>{const b=document.getElementById('el-admin-auth-backdrop');const i=[...b.querySelectorAll('input')];i[0].value=${JSON.stringify(fixture)};i[1].value=${JSON.stringify(fixture)};[...b.querySelectorAll('button')].find(x=>x.textContent.includes('Create')).click();return true;})()`,true);
await waitFor(()=>win.webContents.executeJavaScript("Boolean(document.getElementById('el-admin-console'))",true),30000);
await waitFor(()=>win.webContents.executeJavaScript("document.getElementById('el-admin-training-page') && document.getElementById('el-admin-training-page').innerText.includes('Trainable parameters')",true),30000);
const ui=await win.webContents.executeJavaScript(`(()=>{const c=document.getElementById('el-admin-console');const nav=[...c.querySelectorAll('.el-admin-nav button')].map(x=>x.textContent.trim());const pages=[...c.querySelectorAll('.el-admin-page')].map(x=>x.id);return{nav,pages,entryTitle:document.getElementById('el-admin-entry').getAttribute('title'),entryTab:document.getElementById('el-admin-entry').getAttribute('tabindex'),statusText:document.getElementById('el-admin-status-page').innerText,trainingText:document.getElementById('el-admin-training-page').innerText};})()`,true);
if(JSON.stringify(ui.nav)!==JSON.stringify(['📊 Current Status','🏋️ Training Center']))throw new Error('two-page nav mismatch');if(ui.pages.length!==2)throw new Error('page count mismatch');if(ui.entryTitle!==null||ui.entryTab!==null)throw new Error('hidden entry clue');if(!ui.statusText.includes('App active time')||!ui.trainingText.includes('Current Model')||!ui.trainingText.includes('Trainable parameters'))throw new Error('status/training data surface missing');
const evidence={schema_version:1,gesture:'5-clicks-within-3s',auth_bootstrap:true,page_count:2,pages:ui.nav,hidden_entry_no_title:true,hidden_entry_no_tabindex:true,status_page:true,training_center:true};fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,JSON.stringify(evidence,null,2));console.log('PHASE6_STEP4_CONSOLE_OK');if(!win.isDestroyed())win.destroy();app.quit();})().catch(e=>{console.error(e&&e.stack||e);app.exit(1);});
