/* Automatic per-account synchronization. Only the explicit data allowlist leaves the device. */
const RT_SYNC_KEYS=['rt_settings','rt_wheelItems','rt_drawItems','rt_favorites'];
let rtSyncOwner='',rtSyncReady=false,rtSyncBusy=false,rtSyncGeneration=0,rtSyncBaseline={},rtSyncState='登录后自动同步';
function rtSyncUid(){return window.rtLoggedIn?String(rtUser?.uid||rtUser?.id||rtUser?._id||''):''}
function rtSyncSnapshot(){return Object.fromEntries([...RT_SYNC_KEYS,'rt_profile_'+rtSyncOwner].map(k=>[k,localStorage.getItem(k)]))}
function rtSyncMessage(text){rtSyncState=text;const e=rtElem('rtSyncStatus');if(e)e.textContent=text}
function rtSyncCacheKey(uid){return 'rt_sync_cache_'+uid}
function rtSyncLoad(uid){try{return JSON.parse(localStorage.getItem(rtSyncCacheKey(uid))||'null')}catch(e){return null}}
function rtSyncSaveCache(){if(rtSyncOwner)localStorage.setItem(rtSyncCacheKey(rtSyncOwner),JSON.stringify({values:rtSyncSnapshot(),baseline:rtSyncBaseline}))}
function rtSyncApply(values){
 for(const k of [...RT_SYNC_KEYS,'rt_profile_'+rtSyncOwner]){
  const v=values[k]??null;if(v!==null){if(typeof v!=='string')throw Error('同步数据格式异常');JSON.parse(v)}
 }
 for(const k of [...RT_SYNC_KEYS,'rt_profile_'+rtSyncOwner]){const v=values[k]??null;if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}
 settings=Object.assign({dark:false,vibe:true,sound:true,volume:65,speed:'normal'},get('settings',{}));
 wheelItems=get('wheelItems',['吃火锅','看电影','去散步','打游戏','喝奶茶','在家休息']);drawItems=get('drawItems',['选项一','选项二','选项三']);
 favorites=get('favorites',[]).filter(x=>toolIds.includes(x));remaining=[];rtAccountRefresh();
 // Re-render the visible page through the app's existing navigation.
 const page=document.querySelector('.view.active')?.id;if(page&&typeof go==='function')go(page);
 if(window.RandomToolboxNative)RandomToolboxNative.setDarkMode(!!settings.dark);
}
function rtSyncAccountChanged(){
 const uid=rtSyncUid();if(uid===rtSyncOwner)return;
 if(rtSyncOwner){try{rtSyncSaveCache()}catch(e){console.error(e)}}
 ++rtSyncGeneration;rtSyncReady=false;
 const previous=rtSyncOwner;rtSyncOwner=uid;
 if(!uid){rtSyncMessage('登录后自动同步');return}
 rtProfileClose();
 const cache=rtSyncLoad(uid);
 // Legacy unscoped settings may belong to another account: never upload them automatically.
 const values=cache?.values||Object.fromEntries(RT_SYNC_KEYS.map(k=>[k,null]));
 values['rt_profile_'+uid]=cache?.values?.['rt_profile_'+uid]??localStorage.getItem('rt_profile_'+uid);
 rtSyncBaseline=cache?.baseline||{};
 try{rtSyncApply(values)}catch(e){rtSyncMessage('本机账号缓存读取失败');return}
 rtSyncMessage('正在同步账号数据…');rtSyncTick();
}
async function rtSyncTick(){
 if(rtSyncBusy||!rtSyncOwner||rtSyncUid()!==rtSyncOwner)return;
 rtSyncBusy=true;const uid=rtSyncOwner,generation=rtSyncGeneration;
 try{
  const col=window.rtCloudApp.database().collection('account_backups');
  const r=await col.where({_id:uid}).get();if(r.error)throw r.error;
  if(generation!==rtSyncGeneration||rtSyncUid()!==uid)return;
  const rows=Array.isArray(r.data)?r.data:r.data?.list;
  if(!Array.isArray(rows))throw Error('云端响应格式异常');
  const remote=rows[0];if(remote&&remote.schema!==2)throw Error('云端数据版本不兼容');
  const local=rtSyncSnapshot(),merged={...local},changes={};
  for(const key of Object.keys(local)){
   const dirty=local[key]!== (rtSyncBaseline[key]??null);
   if(dirty){changes[key]=local[key]}
   else if(remote)merged[key]=remote.values?.[key]??null;
  }
  // Pull only fields without pending local edits; edits made during network requests win.
  if(JSON.stringify(merged)!==JSON.stringify(local))rtSyncApply(merged);
  if(Object.keys(changes).length||!remote){
   const values={...(remote?.values||{}),...changes};
   if(!remote)Object.assign(values,merged);
   const payload={schema:2,values,updatedAt:Date.now()};
   if(new TextEncoder().encode(JSON.stringify(payload)).length>800000)throw Error('数据过大，请缩小头像');
   const w=await col.doc(uid).set(payload);if(w.error)throw w.error;
   if(generation!==rtSyncGeneration||rtSyncUid()!==uid)return;
   rtSyncBaseline={...values};
  }else rtSyncBaseline={...merged};
  rtSyncReady=true;rtSyncSaveCache();rtSyncMessage('账号数据已同步');
 }catch(e){if(generation===rtSyncGeneration){rtSyncMessage('暂未同步，数据保留在本机，联网后自动重试');try{rtSyncSaveCache()}catch(_){}console.error('Account sync:',e)}}
 finally{rtSyncBusy=false}
}
setInterval(()=>{rtSyncAccountChanged();if(rtSyncOwner){try{rtSyncSaveCache()}catch(e){}rtSyncTick()}},5000);
window.addEventListener('online',()=>rtSyncTick());
document.addEventListener('visibilitychange',()=>{if(!document.hidden)rtSyncTick();else try{rtSyncSaveCache()}catch(e){}});
