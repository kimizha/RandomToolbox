/* Profile edits are scoped to the signed-in UID; cloud sync remains deferred. */
const RT_AVATARS=['wolf','fox','panda','cat','bear','frog','rabbit','penguin','shiba'];
const RT_AVATAR_NAMES=['小灰狼','小狐狸','熊猫','小猫','小熊','青蛙','兔子','企鹅','柴犬'];
function rtProfileKey(){const id=rtUser?.uid||rtUser?.id||rtUser?._id;return id?'rt_profile_'+String(id):null}
function rtProfileGet(){const k=rtProfileKey();if(!k)return {};try{const p=JSON.parse(localStorage.getItem(k)||'{}');return p&&typeof p==='object'&&!Array.isArray(p)?p:{}}catch(e){return {}}}
function rtProfileSave(p){const k=rtProfileKey();if(!k)return false;try{localStorage.setItem(k,JSON.stringify(p));return true}catch(e){return false}}
function rtProfileDefaultName(p=rtProfileGet()){return String(p.defaultName||rtUser?.phone||rtUser?.phoneNumber||rtUser?.email||rtUser?.emailAddress||rtUser?.username||'开心盒用户').replace(/^\+86\s*/, '')}
function rtProfileName(p=rtProfileGet()){return p.name||rtProfileDefaultName(p)}
function rtApplyAvatar(el,p){if(!el)return;const i=Math.max(0,RT_AVATARS.indexOf(p.avatar||'shiba'));const photo=typeof p.photo==='string'&&/^data:image\/(jpeg|png|webp);base64,/.test(p.photo)?p.photo:null;el.style.backgroundImage='url("'+(photo||RT_AVATAR_SPRITE)+'")';el.style.backgroundSize=photo?'cover':'300% 300%';el.style.backgroundPosition=photo?'center':(i%3*50)+'% '+(Math.floor(i/3)*50)+'%'}
function rtAccountRefresh(){const guest=!window.rtLoggedIn,p=guest?{}:rtProfileGet();const name=rtElem('rtAccountName'),status=rtElem('rtUserStatus'),badge=rtElem('rtAccountBadge');if(name)name.textContent=guest?'欢迎来到开心盒':rtProfileName(p);if(status)status.textContent=!rtSessionKnown?'正在检查登录状态…':guest?'登录后，开启更多趣味玩法':'查看和编辑个人资料';if(badge)badge.textContent=guest?'游客':'已登录';rtApplyAvatar(rtElem('rtAccountAvatar'),p)}
function rtShowProfile(){
 if(!window.rtLoggedIn)return rtShowLogin();
 const p=rtProfileGet();let root=rtElem('rtProfileRoot');
 if(!root){root=document.createElement('div');root.id='rtProfileRoot';document.body.appendChild(root)}
 window.rtProfileDraft={...p};window.rtProfileDraftOwner=rtProfileKey();root.className='rt-profile-mask';
 root.innerHTML=`<div class="rt-profile-sheet">
 <button class="rt-profile-back" onclick="rtProfileClose()">‹ 返回</button><h2>个人资料</h2>
 <div class="rt-profile-avatar-wrap"><div class="rt-profile-main" id="rtProfilePreview" role="img" aria-label="当前头像"></div>
 <button type="button" class="rt-avatar-edit" aria-label="从相册更改头像" onclick="rtElem('rtAvatarUpload').click()">${hbIcon('edit')}</button>
 <input id="rtAvatarUpload" type="file" accept="image/*" hidden onchange="rtProfileUpload(event)"></div>
 <label class="rt-profile-label" for="rtProfileName">昵称</label>
 <form class="rt-profile-name-row" onsubmit="event.preventDefault();rtProfileCommit()"><input id="rtProfileName" maxlength="254" placeholder="请输入昵称" autocomplete="nickname"><button type="submit" class="rt-name-save">保存</button></form>
 <p id="rtProfileNotice" class="rt-profile-notice" role="status" aria-live="polite" hidden></p>
 <p class="rt-profile-note">默认使用登录手机号或邮箱，也可以改成喜欢的昵称。</p>
 <h3>选择头像</h3><div class="rt-avatar-grid" id="rtAvatarGrid"></div>
 <p class="rt-profile-note">点击头像即可保存，也可以点击铅笔从相册选择。</p>
 <p id="rtProfileError" class="rt-profile-error" role="status"></p></div>`;
 rtElem('rtProfileName').value=rtProfileName(p);rtProfileDraw();
}
function rtProfileClose(){rtElem('rtProfileRoot')?.remove();window.rtProfileDraft=null;window.rtProfileDraftOwner=null;window.rtProfileUploadToken=null}
function rtProfileDraw(){const p=window.rtProfileDraft,root=rtElem('rtProfileRoot');if(!p||!root)return;rtApplyAvatar(rtElem('rtProfilePreview'),p);const grid=rtElem('rtAvatarGrid');grid.replaceChildren();RT_AVATARS.forEach((k,i)=>{const b=document.createElement('button');b.type='button';b.className='rt-avatar-choice'+(!p.photo&&(p.avatar||'shiba')===k?' selected':'');b.setAttribute('aria-label',RT_AVATAR_NAMES[i]);b.setAttribute('aria-pressed',String(!p.photo&&(p.avatar||'shiba')===k));b.onclick=()=>rtProfileChoose(k);rtApplyAvatar(b,{avatar:k});grid.appendChild(b)})}
// Avatar and nickname save independently; pending nickname text stays in the input.
function rtProfileStoreAvatar(next){
 if(!window.rtProfileDraft||window.rtProfileDraftOwner!==rtProfileKey())return rtProfileError('登录状态已改变，请重新打开个人资料');
 const p={...rtProfileGet(),avatar:next.avatar};
 if(next.photo)p.photo=next.photo;else delete p.photo;
 if(!rtProfileSave(p))return rtProfileError('保存失败，本机存储空间不足，请换一张较小的头像');
 window.rtProfileDraft=p;rtProfileDraw();rtAccountRefresh();rtProfileError('');
 if(typeof toast==='function')toast('头像已保存');
}
function rtProfileChoose(k){
 if(!window.rtProfileDraft||!RT_AVATARS.includes(k))return;
 window.rtProfileUploadToken=null;rtProfileStoreAvatar({avatar:k});
}
function rtProfileError(m){const e=rtElem('rtProfileError');if(e)e.textContent=m;if(m){const notice=rtElem('rtProfileNotice');if(notice)notice.hidden=true}}
function rtProfileUpload(ev){const f=ev.target.files?.[0],draft=window.rtProfileDraft;if(!f||!draft)return;if(!f.type.startsWith('image/'))return rtProfileError('请选择图片');if(f.size>12*1024*1024)return rtProfileError('图片不能超过12MB');const token={};window.rtProfileUploadToken=token;rtProfileError('正在处理图片…');const reader=new FileReader();const fail=()=>{if(window.rtProfileUploadToken===token)rtProfileError('图片读取失败，请换一张图片')};reader.onerror=fail;reader.onload=()=>{const im=new Image();im.onerror=fail;im.onload=()=>{if(window.rtProfileUploadToken!==token||window.rtProfileDraft!==draft)return;try{const c=document.createElement('canvas'),size=768;c.width=size;c.height=size;const ctx=c.getContext('2d'),side=Math.min(im.width,im.height);ctx.fillStyle='#fff';ctx.fillRect(0,0,size,size);ctx.imageSmoothingQuality='high';ctx.drawImage(im,(im.width-side)/2,(im.height-side)/2,side,side,0,0,size,size);rtProfileStoreAvatar({...draft,photo:c.toDataURL('image/jpeg',.92)})}catch(e){fail()}};im.src=reader.result};reader.readAsDataURL(f);ev.target.value=''}
function rtProfileCommit(){
 if(!window.rtProfileDraft||window.rtProfileDraftOwner!==rtProfileKey())return rtProfileError('登录状态已改变，请重新打开个人资料');
 const name=rtElem('rtProfileName').value.trim();if(!name)return rtProfileError('请输入昵称');
 const p={...rtProfileGet(),name};
 if(!rtProfileSave(p))return rtProfileError('保存失败，本机存储空间不足');
 // Keep the same draft object while an image is decoding, so saving the name does not cancel it.
 Object.assign(window.rtProfileDraft,p);rtElem('rtProfileName').value=name;rtAccountRefresh();rtProfileError('');
 const notice=rtElem('rtProfileNotice');if(notice){clearTimeout(window.rtProfileNoticeTimer);notice.innerHTML=hbIcon('check')+'<span>已保存</span>';notice.hidden=false;window.rtProfileNoticeTimer=setTimeout(()=>{notice.hidden=true},2400)}
}
