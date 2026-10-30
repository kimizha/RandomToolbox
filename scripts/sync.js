/* Account-scoped explicit cloud backup; never includes authentication tokens. */
const RT_SYNC_KEYS=['rt_settings','rt_wheelItems','rt_drawItems','rt_favorites'];
function rtSyncUid(){return String(rtUser?.uid||rtUser?.id||rtUser?._id||'')}
function rtSyncPanel(){
 if(!window.rtLoggedIn)return rtShowLogin();
 let root=rtElem('rtSyncRoot');if(root)root.remove();
 root=document.createElement('div');root.id='rtSyncRoot';root.className='rt-auth';
 root.innerHTML='<div class="rt-wrap"><button class="rt-back" onclick="document.getElementById(\'rtSyncRoot\').remove()">‹</button><div class="rt-head"><h1>账号同步</h1><p>备份昵称、头像、设置、自定义转盘和抽签名单、收藏。登录凭证不会上传。</p></div><p>上传会替换此账号的云端备份；恢复会替换本机对应数据。请在换设备前上传。</p><button class="rt-btn rt-primary" onclick="rtSyncRun(false)">备份到云端</button><button class="rt-btn" onclick="rtSyncRun(true)">从云端恢复</button><p id="rtSyncMsg" role="status"></p></div>';
 document.body.appendChild(root);
}
let rtSyncBusy=false;
async function rtSyncRun(restore){
 if(rtSyncBusy)return;
 const uid=rtSyncUid(),owner=rtProfileKey(),msg=rtElem('rtSyncMsg');
 if(!uid||!window.rtLoggedIn)return;
 if(!confirm(restore?'用云端备份替换本机资料和设置？':'用本机数据替换此账号的云端备份？'))return;
 rtSyncBusy=true;msg.textContent=restore?'正在读取备份…':'正在上传备份…';
 try{
  const col=window.rtCloudApp.database().collection('account_backups');
  const result=await col.where({_id:uid}).get();
  if(result.error)throw result.error;
  const docs=Array.isArray(result.data)?result.data:result.data?.list||[];
  if(rtSyncUid()!==uid||!window.rtLoggedIn)throw Error('账号已改变，请重新操作');
  if(restore){
   if(!docs.length)throw Error('此账号还没有云端备份，请先在原设备上传');
   const b=docs[0];if(b.schema!==1||!b.values||!b.profile)throw Error('备份格式不兼容');
   const entries=RT_SYNC_KEYS.map(k=>[k,b.values[k]??null]);entries.push([owner,JSON.stringify(b.profile)]);
   for(const [k,v] of entries){if(v!==null){if(typeof v!=='string')throw Error('备份格式错误');JSON.parse(v)}}
   const before=entries.map(([k])=>[k,localStorage.getItem(k)]);
   try{for(const [k,v] of entries){if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}}
   catch(e){for(const [k,v] of before){if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}throw e}
   msg.textContent='恢复成功，正在重新加载…';location.reload();
  }else{
   const values=Object.fromEntries(RT_SYNC_KEYS.map(k=>[k,localStorage.getItem(k)]));
   const data={schema:1,profile:rtProfileGet(),values,updatedAt:Date.now()};
   if(new TextEncoder().encode(JSON.stringify(data)).length>800000)throw Error('备份过大，请更换较小头像后重试');
   const saved=await col.doc(uid).set(data);if(saved.error)throw saved.error;
   msg.textContent='云端备份成功 · '+new Date().toLocaleString();
  }
 }catch(e){msg.textContent='同步未完成：'+(e.message||String(e))+'。本机数据保留；请确认云端集合与权限已配置。'}
 finally{rtSyncBusy=false}
}
