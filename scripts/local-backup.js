/* Local, user-initiated export. Never enumerate/export SDK credentials or call the network. */
const RT_BACKUP_FIXED_KEYS=new Set(['rt_settings','rt_wheelItems','rt_drawItems','rt_favorites','rt_history','hb_start_page','hb_party_local_v1','rt_sync_active_uid','rt_sync_guest_cache']);
let rtBackupPending=null;
function rtBackupAllowedKey(key){return RT_BACKUP_FIXED_KEYS.has(key)||/^rt_(profile|sync_cache)_.+$/.test(key)}
function rtBuildLocalBackup(){
 const storage={};
 // Keep raw strings, including damaged JSON, to preserve recoverable local data exactly.
 // A storage read failure aborts the whole export instead of creating a misleading partial backup.
 for(let i=0;i<localStorage.length;i++){
  const key=localStorage.key(i);if(!key||!rtBackupAllowedKey(key))continue;
  const value=localStorage.getItem(key);if(value!==null)Object.defineProperty(storage,key,{value,enumerable:true});
 }
 const backup={format:'happybox-local-backup',formatVersion:1,accountBackupSchema:2,exportedAt:new Date().toISOString(),storage};
 const json=JSON.stringify(backup,null,2);
 if(new TextEncoder().encode(json).length>16*1024*1024)throw Error('BACKUP_TOO_LARGE');
 return json;
}
function rtBackupBusy(value){document.querySelectorAll('[data-rt-backup-export]').forEach(button=>button.disabled=value)}
window.rtBackupExportFinished=function(requestId,code){
 if(!rtBackupPending||rtBackupPending!==requestId)return;
 rtBackupPending=null;rtBackupBusy(false);
 toast(code==='SAVED'?'本机 JSON 备份已保存':code==='CANCELLED'?'已取消导出，本机数据保持不变':'备份未保存，请检查文件位置和空间后重试');
};
function rtExportLocalBackup(){
 if(rtBackupPending)return;
 let json;try{json=rtBuildLocalBackup()}catch(_){toast('备份生成失败，请检查本机存储空间；原数据保持不变');return}
 if(window.RandomToolboxNative){
  if(typeof RandomToolboxNative.exportLocalBackup!=='function'){toast('当前 APK 暂不支持文件导出，请等待支持本机备份的测试版本');return}
  const id='backup-'+Date.now()+'-'+Math.random().toString(36).slice(2);rtBackupPending=id;rtBackupBusy(true);
  try{RandomToolboxNative.exportLocalBackup(json,id)}catch(_){window.rtBackupExportFinished(id,'FAILED')}
  return;
 }
 // Browser preview/Desktop only. Android uses ACTION_CREATE_DOCUMENT, not blob downloads.
 try{
  const blob=new Blob([json],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download='Happybox-local-backup-'+new Date().toISOString().slice(0,10)+'.json';document.body.appendChild(a);
  try{a.click()}finally{a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000)}
  toast('已请求下载，请确认 JSON 文件已保存');
 }catch(_){toast('备份未保存，请重试；原数据保持不变')}
}
