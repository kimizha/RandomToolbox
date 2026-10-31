/* Keep schema:2 / account_backups and existing serialized preference keys. */
const RT_SYNC_KEYS=['rt_settings','rt_wheelItems','rt_drawItems','rt_favorites'];
const RT_SYNC_OWNER_KEY='rt_sync_active_uid';
let rtSyncOwner='',rtSyncReady=false,rtSyncBusy=false,rtSyncGeneration=0,rtSyncBaseline={},rtSyncState='登录后自动同步';
let rtSyncTask=null,rtSyncTimer=null,rtSyncAgain=false,rtSyncApplying=false,rtSyncLastSuccess=0,rtSyncError='';
function rtSyncUid(){return window.rtLoggedIn?String(rtUser?.uid||rtUser?.id||rtUser?._id||''):''}
function rtSyncKeys(uid=rtSyncOwner){return uid?[...RT_SYNC_KEYS,'rt_profile_'+uid]:[...RT_SYNC_KEYS]}
function rtSyncSnapshot(uid=rtSyncOwner){return Object.fromEntries(rtSyncKeys(uid).map(k=>[k,localStorage.getItem(k)]))}
function rtSyncCacheKey(uid){return 'rt_sync_cache_'+uid}
function rtSyncLoad(uid){try{return JSON.parse(localStorage.getItem(rtSyncCacheKey(uid))||'null')}catch(e){return null}}
function rtSyncMessage(text){
 rtSyncState=text;
 for(const id of ['rtSyncStatus','rtSyncSummary']){const e=rtElem(id);if(e)e.textContent=text}
 const when=rtElem('rtSyncLastTime');if(when)when.textContent=rtSyncLastSuccess?'最近成功同步：'+new Date(rtSyncLastSuccess).toLocaleString():'尚未完成云端同步';
 const error=rtElem('rtSyncError');if(error)error.textContent=rtSyncError;
 const summary=rtElem('rtSyncSummary');if(summary)summary.hidden=!window.rtLoggedIn;
}
function rtSyncSaveCache(){
 if(rtSyncOwner)localStorage.setItem(rtSyncCacheKey(rtSyncOwner),JSON.stringify({values:rtSyncSnapshot(),baseline:rtSyncBaseline,lastSyncedAt:rtSyncLastSuccess}));
}
function rtSyncValues(uid,source={}){
 const values={};for(const k of rtSyncKeys(uid)){
  const v=source[k]??null;values[k]=v;if(v===null)continue;
  if(typeof v!=='string')throw Error('配置格式异常：'+k);
  const data=JSON.parse(v);
  if(k==='rt_wheelItems'||k==='rt_drawItems'){
   if(!Array.isArray(data)||data.length<2||data.length>(k==='rt_wheelItems'?12:200)||data.some(x=>typeof x!=='string'||!x.trim()))throw Error('选项格式异常');
  }else if(k==='rt_favorites'){
   if(!Array.isArray(data)||data.some(x=>!toolIds.includes(x)))throw Error('常用工具格式异常');
  }else if(!data||typeof data!=='object'||Array.isArray(data))throw Error('配置对象格式异常');
 }
 return values;
}
function rtSyncApply(uid,values){
 values=rtSyncValues(uid,values);const before=rtSyncSnapshot(uid);
 rtSyncApplying=true;
 try{for(const [k,v] of Object.entries(values)){if(v===before[k])continue;if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}}
 catch(e){for(const [k,v] of Object.entries(before)){try{if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(_){}}throw e}
 finally{rtSyncApplying=false}
 const previousDraw=JSON.stringify(drawItems);
 settings=Object.assign({dark:false,vibe:true,sound:true,volume:65,speed:'normal'},get('settings',{}));
 wheelItems=get('wheelItems',['吃火锅','看电影','去散步','打游戏','喝奶茶','在家休息']);drawItems=get('drawItems',['选项一','选项二','选项三']);
 favorites=get('favorites',[]).filter(x=>toolIds.includes(x));if(JSON.stringify(drawItems)!==previousDraw)remaining=[];
 initSettings();renderFav();renderCatalog();renderManage();rtAccountRefresh();
 if(document.querySelector('.view.active')?.id==='tool'&&activeTool==='wheel'&&!busy)renderWheel();
}
function rtSyncAccountChanged(){
 if(!rtSessionKnown)return;
 const uid=rtSyncUid();if(uid===rtSyncOwner&&localStorage.getItem(RT_SYNC_OWNER_KEY)===(uid||'guest'))return;
 const storedStamp=localStorage.getItem(RT_SYNC_OWNER_KEY)||'',stamp=storedStamp==='pending'?'':storedStamp,previous=rtSyncOwner||(stamp!=='guest'?stamp:'');
 try{
  // Save the prior owner's data before changing any unscoped runtime keys.
  if(previous){const old=previous===rtSyncOwner?{baseline:rtSyncBaseline,lastSyncedAt:rtSyncLastSuccess}:rtSyncLoad(previous)||{};localStorage.setItem(rtSyncCacheKey(previous),JSON.stringify({...old,values:rtSyncSnapshot(previous)}))}
  else{const guest=rtSyncSnapshot('');if(Object.values(guest).some(v=>v!==null))localStorage.setItem('rt_sync_guest_cache',JSON.stringify({values:guest}))}
  const cache=uid?rtSyncLoad(uid):JSON.parse(localStorage.getItem('rt_sync_guest_cache')||'null');
  const values=rtSyncValues(uid,cache?.values||(stamp===uid&&uid?rtSyncSnapshot(uid):{}));
  // Per-UID profile storage is safe to restore, but never synthesize an empty/default profile on login.
  if(uid){const profile=localStorage.getItem('rt_profile_'+uid);if(profile!==null)values['rt_profile_'+uid]=profile}
  rtSyncValues(uid,values);
  const baseline=rtSyncValues(uid,cache?.baseline||{});
  const before=rtSyncSnapshot(uid);
  // The marker prevents a process interruption from attributing a half-applied account to another UID.
  localStorage.setItem(RT_SYNC_OWNER_KEY,'pending');
  try{rtProfileClose();rtSyncApply(uid,values);localStorage.setItem(RT_SYNC_OWNER_KEY,uid||'guest')}
  catch(e){try{rtSyncApply(uid,before);if(storedStamp)localStorage.setItem(RT_SYNC_OWNER_KEY,storedStamp);else localStorage.removeItem(RT_SYNC_OWNER_KEY)}catch(_){}throw e}
  ++rtSyncGeneration;rtSyncReady=false;rtSyncError='';rtSyncLastSuccess=cache?.lastSyncedAt||0;
  rtSyncOwner=uid;rtSyncBaseline=baseline;
  if(!uid){rtSyncMessage('登录后自动同步');return}
  rtSyncSaveCache();rtSyncMessage('正在恢复账号配置…');
  if(rtSyncBusy)rtSyncAgain=true;else rtSyncTick();
 }catch(e){rtSyncError='本机配置未能安全保存，已暂停同步：'+String(e.message||e);rtSyncMessage('本机存储异常，请重试')}
}
function rtSyncMerge(key,local,base,remote){
 if(local===base)return remote;
 if(local===null)return null;
 // Merge profile/settings fields individually so login defaults cannot overwrite a cloud avatar/name.
 if(key==='rt_settings'||key==='rt_profile_'+rtSyncOwner){
  const defaults=key==='rt_settings'?{dark:false,vibe:true,sound:true,volume:65,speed:'normal'}:{};
  const l=JSON.parse(local),b=base===null?defaults:JSON.parse(base),r=remote===null?{}:JSON.parse(remote),out={...r};
  for(const field of new Set([...Object.keys(l),...Object.keys(b)])){
   if(JSON.stringify(l[field])!==JSON.stringify(b[field])){if(l[field]===undefined)delete out[field];else out[field]=l[field]}
   else if(remote===null&&l[field]!==undefined)out[field]=l[field];
  }
  if(key!=='rt_settings'&&l.avatar!==b.avatar&&!l.photo)delete out.photo;
  return JSON.stringify(out);
 }
 return local;
}
function rtSyncWithTimeout(promise){let timer;return Promise.race([promise,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('同步请求超时')),10000)})]).finally(()=>clearTimeout(timer))}
function rtSyncDescribeError(e){
 const code=String(e?.code||e?.errorCode||''),text=String(e?.message||e||'未知错误');
 if(/permission|denied|unauthorized|权限/i.test(code+' '+text))return '云端拒绝访问，请管理员检查账号备份集合的权限。错误代码：'+(code||'permission denied');
 if(/collection.*not.*exist|collection.*not.*found/i.test(code+' '+text))return '云端备份集合不可用，请管理员检查现有同步服务。';
 if(/database.*function|数据同步组件/.test(text))return '当前版本的数据同步组件不可用，请联系开发者。';
 return (code?code+'：':'')+text.slice(0,180);
}
function rtSyncTick(){
 if(!rtSyncOwner||rtSyncUid()!==rtSyncOwner)return Promise.resolve(false);
 if(rtSyncBusy)return rtSyncTask||Promise.resolve(false);
 const uid=rtSyncOwner,generation=rtSyncGeneration;rtSyncBusy=true;
 rtSyncTask=(async()=>{
  try{
   if(typeof window.rtCloudApp?.database!=='function')throw Error('数据同步组件不可用');
   const col=window.rtCloudApp.database().collection('account_backups');
   const response=await rtSyncWithTimeout(col.where({_id:uid}).get());if(response.error)throw response.error;
   if(generation!==rtSyncGeneration||rtSyncUid()!==uid)return false;
   const rows=Array.isArray(response.data)?response.data:response.data?.list;
   if(!Array.isArray(rows))throw Error('云端响应格式异常');
   const remote=rows[0];if(remote&&remote.schema!==2)throw Error('云端数据版本不兼容，未覆盖任何配置');
   const remoteValues=rtSyncValues(uid,remote?.values||{}),local=rtSyncSnapshot(),base=rtSyncValues(uid,rtSyncBaseline),merged={};
   for(const key of rtSyncKeys())merged[key]=rtSyncMerge(key,local[key],base[key],remoteValues[key]);
   rtSyncValues(uid,merged);
   // Do not change options while an animation is using those arrays.
   if(busy&&document.querySelector('.view.active')?.id==='tool'){rtSyncReady=false;rtSyncMessage('本次操作结束后自动同步');return false}
   rtSyncApply(uid,merged);
   const changed=rtSyncKeys().some(k=>merged[k]!==remoteValues[k]);
   if(changed||!remote){
    const values={...(remote?.values||{}),...merged},payload={schema:2,values,updatedAt:Date.now()};
    if(new TextEncoder().encode(JSON.stringify(payload)).length>800000)throw Error('头像或配置过大，已保存在本机，请缩小头像后重试');
    const write=await rtSyncWithTimeout(col.doc(uid).set(payload));if(write.error)throw write.error;
    if(generation!==rtSyncGeneration||rtSyncUid()!==uid)return false;
   }
   rtSyncBaseline={...merged};rtSyncReady=true;rtSyncError='';rtSyncLastSuccess=Date.now();rtSyncSaveCache();
   rtSyncMessage(Object.values(merged).some(v=>v!==null)?'账号配置已同步':'云端暂无历史配置，新设置将自动保存');return true;
  }catch(e){
   if(generation===rtSyncGeneration){rtSyncReady=false;rtSyncError=rtSyncDescribeError(e);rtSyncMessage('尚未同步，本机修改已保留');try{rtSyncSaveCache()}catch(_){}console.error('Account sync:',rtSyncError)}return false;
  }finally{
   rtSyncBusy=false;rtSyncTask=null;
   if(rtSyncAgain){rtSyncAgain=false;rtSyncSchedule()}
  }
 })();return rtSyncTask;
}
function rtSyncSchedule(){clearTimeout(rtSyncTimer);rtSyncTimer=setTimeout(()=>{rtSyncAccountChanged();rtSyncTick()},400)}
function rtSyncLocalChanged(key){
 if(rtSyncApplying)return;
 const uid=rtSyncUid();if(!uid)return;
 if(!rtSyncKeys(uid).includes(key))return;
 if(uid!==rtSyncOwner){const value=localStorage.getItem(key);rtSyncAccountChanged();if(rtSyncOwner!==uid)return;if(value!==null)localStorage.setItem(key,value)}
 try{rtSyncSaveCache()}catch(e){rtSyncError='本机账号缓存保存失败，请检查存储空间'}
 rtSyncReady=false;rtSyncMessage('配置已保存在本机，正在同步…');if(rtSyncBusy)rtSyncAgain=true;rtSyncSchedule();
}
async function rtSyncBeforeLogout(){
 try{rtSyncSaveCache();await Promise.race([rtSyncTick(),new Promise(resolve=>setTimeout(resolve,3000))])}catch(_){}
}
function rtSyncPanel(){
 if(!window.rtLoggedIn)return rtShowLogin();
 rtElem('rtModalShade')?.remove();const shade=document.createElement('div');shade.id='rtModalShade';shade.className='rt-modal-shade';
 shade.innerHTML=`<div class="rt-modal rt-sync-modal" role="dialog" aria-modal="true"><h3>账号同步</h3><p id="rtSyncStatus"></p><p id="rtSyncLastTime" class="hint"></p><p>昵称、头像、常用工具、转盘选项、抽签名单和设置会随账号同步。</p><p id="rtSyncError" role="status"></p><button id="rtSyncRetry" class="primary">立即同步</button><button id="rtSyncImport" class="secondary">导入本机游客配置</button><button id="rtSyncClose" class="textbtn">关闭</button></div>`;
 document.body.appendChild(shade);rtSyncMessage(rtSyncState);
 rtElem('rtSyncClose').onclick=()=>shade.remove();
 rtElem('rtSyncRetry').onclick=async()=>{rtSyncAccountChanged();await rtSyncTick()};
 const importButton=rtElem('rtSyncImport');importButton.hidden=!localStorage.getItem('rt_sync_guest_cache');
 importButton.onclick=()=>{shade.remove();rtDialog('导入本机游客配置？','将用本机的工具配置替换当前账号对应的配置，并同步到云端。昵称和头像保持不变。',()=>{
  try{const guest=JSON.parse(localStorage.getItem('rt_sync_guest_cache')||'null');if(!guest)return;const values=rtSyncSnapshot();for(const k of RT_SYNC_KEYS)if(guest.values[k]!==null&&guest.values[k]!==undefined)values[k]=guest.values[k];rtSyncApply(rtSyncOwner,values);rtSyncSaveCache();rtSyncReady=false;rtSyncMessage('配置已导入，正在同步…');rtSyncSchedule();toast('已导入，正在同步')}catch(e){toast('导入失败，本机数据已保留')}
 })};
}
setInterval(()=>{rtSyncAccountChanged();if(rtSyncOwner){try{rtSyncSaveCache()}catch(_){}rtSyncTick()}},5000);
window.addEventListener('online',()=>{rtSyncAccountChanged();rtSyncTick()});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){rtSyncAccountChanged();rtSyncTick()}else try{rtSyncSaveCache()}catch(_){}});
