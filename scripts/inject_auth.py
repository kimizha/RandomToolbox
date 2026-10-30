from pathlib import Path
import os, json

p = Path('app/src/main/assets/index.html')
s = p.read_text(encoding='utf-8')
key = os.environ.get('CLOUDBASE_PUBLISHABLE_KEY', '').strip()
if not key or not key.startswith('eyJ'):
    raise SystemExit('Missing or invalid CLOUDBASE_PUBLISHABLE_KEY secret')
if 'RT_AUTH_NATIVE_V3' in s or 'RT_AUTH_FULLSCREEN_V2' in s:
    raise SystemExit('Account UI already injected. Build from clean source HTML.')

def replace(old, new):
    global s
    if old not in s:
        raise SystemExit('HTML anchor not found: ' + old[:70])
    s = s.replace(old, new, 1)

replace('function openGame(type){party=', "function openGame(type){if(!window.rtLoggedIn){rtShowLogin('登录后即可体验趣味玩法');return}party=")
replace('<section id="games" class="view">', '<section id="games" class="view"><div id="rtGuestBanner" class="panel" style="padding:16px;margin-bottom:14px"><strong>解锁更多趣味玩法</strong><p class="hint">登录后即可体验狼人杀、真心话大冒险和谁是卧底。</p><button class="primary" onclick="rtShowLogin()">登录 / 注册</button></div>')
replace('<section id="settings" class="view">', '<section id="settings" class="view"><div class="panel" style="padding:16px;margin-bottom:14px"><h2>我的账号</h2><p class="hint" id="rtUserStatus">正在检查登录状态…</p><button id="rtLoginButton" class="primary" onclick="rtShowLogin()">登录 / 注册</button><button id="rtProfileButton" class="secondary" style="display:none;width:100%;margin-top:10px" onclick="rtShowProfile()">个人资料 · 头像 / 昵称 / 玩家 ID ›</button><button id="rtSecurityButton" class="secondary" style="display:none;width:100%;margin-top:10px" onclick="rtShowSecurity()">账号安全 ›</button><button id="rtLogoutButton" class="secondary" style="display:none;width:100%;margin-top:10px" onclick="rtLogout()">退出登录</button></div>')

css = r'''<style id="rt-auth-style">
.rt-auth{position:fixed;inset:0;z-index:999999;background:#f7f7fb;color:#26243a;overflow:auto;overscroll-behavior:contain;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.rt-auth[hidden]{display:none!important}.rt-auth *{box-sizing:border-box}.rt-wrap{max-width:460px;min-height:100dvh;margin:auto;padding:calc(env(safe-area-inset-top) + 14px) 24px calc(env(safe-area-inset-bottom) + 38px)}
.rt-back{width:42px;height:42px;border:0;border-radius:14px;background:#fff;color:inherit;font-size:26px;box-shadow:0 3px 12px #33255d0c}
.rt-head{margin:34px 0 28px}.rt-mark{width:66px;height:66px;display:grid;place-items:center;border-radius:22px;background:#e9e2ff;color:#7356da;font-size:30px;font-weight:800;margin-bottom:24px;box-shadow:0 9px 18px #7153d31a}
.rt-head h1{font-size:30px;letter-spacing:-.7px;margin:0 0 9px;font-weight:780}.rt-head p{font-size:14px;color:#87859a;margin:0;line-height:1.7}
.rt-field{margin:16px 0}.rt-field label{display:block;font-size:13px;font-weight:650;margin-bottom:9px;color:#5e5a71}.rt-input{display:flex;align-items:center;background:#fff;border:1px solid #e9e7f0;border-radius:16px;min-height:56px;padding:0 15px}.rt-input:focus-within{border-color:#9778ed;box-shadow:0 0 0 3px #9778ed1a}.rt-input input{width:100%;min-width:0;background:none;border:0;outline:0;color:inherit;font-size:15px}.rt-eye{border:0;background:none;color:#847e97;font-size:16px;padding:8px;white-space:nowrap}
.rt-btn{width:100%;min-height:53px;border:0;border-radius:16px;font-size:15px;font-weight:730;margin-top:10px}.rt-primary{color:#fff;background:#8063e7;box-shadow:0 9px 18px #8063e72b}.rt-btn:disabled{opacity:.5}.rt-link{background:none;border:0;color:#7554df;font-size:14px;font-weight:680;padding:10px}.rt-center{text-align:center}.rt-msg{min-height:24px;color:#b34458;font-size:13px;line-height:1.6;margin:12px 0}.rt-hint{padding:14px 15px;border-radius:16px;background:#fff5e6;color:#91602b;font-size:13px;line-height:1.7;margin:18px 0}.rt-item{display:flex;align-items:center;justify-content:space-between;width:100%;padding:19px 17px;border:1px solid #ebe8f2;border-radius:17px;background:#fff;text-align:left;color:inherit;margin:12px 0;font-size:15px}.rt-item small{display:block;color:#89869a;font-size:12px;margin-top:6px}.rt-pill{font-size:12px;color:#8063e7;background:#eee8ff;padding:5px 9px;border-radius:10px}.rt-footer{font-size:12px;color:#9390a1;line-height:1.6}
@media(prefers-color-scheme:dark){.rt-auth{background:#171720;color:#f5f3ff}.rt-back,.rt-input,.rt-item{background:#272633;border-color:#3a3748}.rt-field label,.rt-head p,.rt-item small{color:#ada8bd}.rt-input input{color:#fff}.rt-hint{background:#3b3028;color:#f2c38b}}
</style>'''

js = r'''
/* RT_AUTH_NATIVE_V3 */
window.rtLoggedIn=false;
let rtAuth=null,rtUser=null,rtVerify=null,rtVerifyAction='login',rtPage='login',rtMode='email',rtBusy=false,rtSessionKnown=false,rtAuthError='';
const RT_AUTH_BUILD='AUTH-DIAG-20261030-1';
function rtElem(id){return document.getElementById(id)}
function rtStatus(){
 const guest=!window.rtLoggedIn;
 if(rtElem('rtGuestBanner'))rtElem('rtGuestBanner').style.display=guest?'block':'none';
 if(rtElem('rtUserStatus'))rtElem('rtUserStatus').textContent=!rtSessionKnown?'正在检查登录状态…':guest?'游客模式 · 趣味玩法需登录':('已登录 · '+(rtUser?.username||rtUser?.email||'趣味玩法已解锁'));
 for(const [id,visible] of [['rtLoginButton',guest],['rtProfileButton',!guest],['rtSecurityButton',!guest],['rtLogoutButton',!guest]])if(rtElem(id))rtElem(id).style.display=visible?'block':'none';
}
function rtShowLogin(note){if(window.rtLoggedIn)return rtShowSecurity();let r=rtElem('rtAuthRoot');if(!r){r=document.createElement('div');r.id='rtAuthRoot';r.className='rt-auth';document.body.appendChild(r)}r.hidden=false;rtRender('login',note)}
function rtClose(){const r=rtElem('rtAuthRoot');if(r)r.hidden=true;rtVerify=null}
function rtExistingAccountDialog(){
 const old=document.getElementById('rtExistingAccountModal');if(old)old.remove();
 const tip=document.createElement('div');tip.id='rtExistingAccountModal';
 tip.setAttribute('role','status');tip.setAttribute('aria-live','polite');
 tip.textContent='✓ 已有账号，已自动登录';
 tip.style.cssText='position:fixed;left:50%;bottom:110px;transform:translate(-50%,8px);z-index:2147483646;max-width:calc(100vw - 48px);padding:12px 20px;border-radius:14px;background:rgba(38,38,52,.92);color:#fff;font-size:14px;font-weight:600;text-align:center;box-shadow:0 8px 24px #0003;opacity:0;transition:opacity .35s ease,transform .35s ease;pointer-events:none';
 document.body.appendChild(tip);
 requestAnimationFrame(()=>{tip.style.opacity='1';tip.style.transform='translate(-50%,0)'});
 setTimeout(()=>{tip.style.opacity='0';tip.style.transform='translate(-50%,8px)';setTimeout(()=>tip.remove(),400)},4700);
}
function rtEsc(x){return String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function rtRender(page,note){rtPage=page;let r=rtElem('rtAuthRoot');if(!r)return;
 const head=(title,sub)=>`<div class="rt-head"><div class="rt-mark">✦</div><h1>${title}</h1><p>${sub}</p></div>`;
 const input=(id,label,type='text',hint='')=>`<div class="rt-field"><label for="${id}">${label}</label><div class="rt-input"><input id="${id}" type="${type}" placeholder="${hint}" ${type==='password'?'autocomplete="new-password"':''}>${type==='password'?`<button type="button" class="rt-eye" onclick="rtEye('${id}',this)">显示</button>`:''}</div></div>`;
 let body='';
 if(page==='login')body=head('欢迎回来','登录随机工具箱')+input('rtIdentifier','邮箱','email','请输入邮箱')+input('rtPassword','密码','password','请输入密码')+'<button class="rt-btn rt-primary" onclick="rtLogin()">邮箱密码登录</button><p class="rt-center"><button class="rt-link" onclick="rtMode=\'email\';rtRender(\'otpLogin\')">邮箱验证码登录</button> · <button class="rt-link" onclick="rtMode=\'phone\';rtRender(\'otpLogin\')">手机号验证码登录</button></p><p class="rt-center">还没有账号？<button class="rt-link" onclick="rtRender(\'choose\')">立即注册</button></p><p class="rt-center"><button class="rt-link" onclick="rtRender(\'forgot\')">忘记密码？</button></p>';
 else if(page==='choose')body=head('创建账号','选择一种注册方式')+'<button class="rt-item" onclick="rtMode=\'email\';rtRender(\'register\')"><span>邮箱注册<small>邮箱验证码验证</small></span><span>›</span></button><button class="rt-item" onclick="rtMode=\'phone\';rtRender(\'register\')"><span>手机号注册<small>短信验证码验证</small></span><span>›</span></button>';
 else if(page==='register')body=head(rtMode==='phone'?'手机号注册':'邮箱注册','验证联系方式后即可创建账号')+input('rtContact',rtMode==='phone'?'手机号':'邮箱',rtMode==='phone'?'tel':'email',rtMode==='phone'?'请输入手机号':'请输入邮箱')+(rtMode==='phone'?'':input('rtNewPassword','设置密码','password','至少 8 位')+input('rtConfirmPassword','确认密码','password','请再次输入密码'))+'<button class="rt-btn rt-primary" onclick="rtRegister()">发送验证码</button>';
 else if(page==='otpLogin')body=head(rtMode==='phone'?'手机验证码登录':'邮箱验证码登录','仅登录已注册账号，不会自动创建新账号')+input('rtContact',rtMode==='phone'?'手机号':'邮箱',rtMode==='phone'?'tel':'email',rtMode==='phone'?'请输入手机号':'请输入邮箱')+'<button class="rt-btn rt-primary" onclick="rtSendOtpLogin()">发送验证码</button>';
 else if(page==='verify')body=head('验证'+(rtMode==='phone'?'手机号':'邮箱'),'请输入收到的验证码')+input('rtOtp','验证码','text','请输入验证码')+'<button class="rt-btn rt-primary" onclick="rtVerifyEmail()">验证并完成</button>';
 else if(page==='security'){let email=rtUser?.email||rtUser?.emailAddress||'',phone=rtUser?.phone||rtUser?.phoneNumber||'';body=head('账号安全','保护好你的随机工具箱账号')+(!email&&!phone?'<div class="rt-hint">你的账号尚未绑定邮箱或手机号，建议至少绑定一种联系方式，以便日后找回密码。</div>':'')+`<div class="rt-item"><span>绑定邮箱<small>${email?rtEsc(email):'未绑定 · 后续开放绑定功能'}</small></span><span class="rt-pill">${email?'已绑定':'待绑定'}</span></div><div class="rt-item"><span>绑定手机号<small>${phone?rtEsc(phone):'未绑定 · 后续开放绑定功能'}</small></span><span class="rt-pill">${phone?'已绑定':'待绑定'}</span></div><p class="rt-footer">绑定邮箱、绑定手机号、修改密码和账号找回功能将在后续版本逐步开放。当前页面不会执行虚假的绑定操作。</p>`;}
 else if(page==='forgot')body=head('找回密码','请使用已绑定的联系方式恢复账号')+'<div class="rt-hint">安全的密码重置流程尚未开放。没有绑定联系方式的账号可能无法找回，请妥善保管密码。</div><button class="rt-btn rt-primary" onclick="rtRender(\'login\')">返回登录</button>';
 r.innerHTML=`<div class="rt-wrap"><button class="rt-back" onclick="rtBack()" aria-label="返回">‹</button>${body}<p id="rtMsg" class="rt-msg" role="status"></p></div>`;if(note)rtMsg(note,false);
}
function rtBack(){if(rtPage==='login'||rtPage==='security')rtClose();else if(rtPage==='register')rtRender('choose');else if(rtPage==='otpLogin')rtRender('login');else if(rtPage==='verify')rtRender('choose');else rtRender('login')}
function rtEye(id,b){let x=rtElem(id);x.type=x.type==='password'?'text':'password';b.textContent=x.type==='password'?'显示':'隐藏'}
function rtMsg(m,error=true){let e=rtElem('rtMsg');if(e){e.textContent=m;e.style.color=error?'#b34458':'#7857dc'}}
function rtErr(e){let m=e?.message||e?.error_description||String(e||'网络请求失败');if(/failed to fetch|networkerror|load failed/i.test(m)){let origin=location.origin||'(无来源)';return '网络请求失败。页面来源：'+origin+'；网络状态：'+(navigator.onLine?'在线':'离线')+'。请检查 CloudBase 安全域名、手机网络及 VPN。原始错误：'+m}return m}
function rtCheck(r){if(r?.error)throw r.error;return r?.data}
async function rtSession(){let r=await rtAuth.getSession();rtCheck(r);let d=r?.data||{};window.rtLoggedIn=!!d.session;rtUser=d.user||d.session?.user||null;rtSessionKnown=true;rtStatus();return window.rtLoggedIn}
async function rtFinishLogin(result){rtCheck(result);if(!(await rtSession()))throw Error('未获得有效登录会话，请重试');rtClose();if(typeof toast==='function')toast('登录成功')}
async function rtLogin(){if(rtBusy)return;if(!rtAuth)return rtMsg('认证服务未连接：'+(rtAuthError||'请检查网络或稍后重试'));let id=rtElem('rtIdentifier').value.trim(),password=rtElem('rtPassword').value;if(!id||!password)return rtMsg('请输入邮箱和密码');if(!/^\S+@\S+\.\S+$/.test(id))return rtMsg('请输入正确的邮箱');rtBusy=true;rtMsg('正在验证账号…',false);try{await rtFinishLogin(await rtAuth.signInWithPassword({email:id,password}))}catch(e){rtMsg('登录失败：'+rtErr(e))}finally{rtBusy=false}}
function rtContactValue(){let contact=rtElem('rtContact').value.trim();if(rtMode==='phone'){if(!/^1[3-9]\d{9}$/.test(contact))throw Error('请输入正确的中国大陆11位手机号');return '+86 '+contact}if(!/^\S+@\S+\.\S+$/.test(contact))throw Error('请输入正确的邮箱');return contact}
function rtAccountMissingError(e){let c=String(e?.code||e?.errorCode||e?.name||'').toLowerCase(),m=String(e?.message||e?.error_description||'').toLowerCase();return /not_found|user_not_found|user.?not.?exist|account.?not.?exist|用户不存在|账号不存在|未注册|尚未注册/.test(c+' '+m)}
function rtAccountExistsError(e){let c=String(e?.code||e?.errorCode||e?.name||'').toLowerCase(),m=String(e?.message||e?.error_description||'').toLowerCase();return /already.?exist|already.?register|duplicate|already.?in.?use|email.?taken|phone.?taken|account.?exist|user.?exist|failed_precondition|已注册|已经注册|已存在|已被使用|已绑定|重复/.test(c+' '+m)}
let rtPendingSignup=null;
async function rtStartRealSignup(){if(!rtPendingSignup)throw Error('注册信息已过期，请重新填写');let d=rtCheck(await rtAuth.signUp(rtPendingSignup));if(typeof d?.verifyOtp!=='function')throw Error('注册接口未返回验证码流程');rtVerify=d.verifyOtp;rtVerifyAction='register';rtRender('verify');rtMsg('已发送新账号注册验证码，请输入最新收到的验证码',false)}
async function rtRegister(){if(rtBusy)return;if(!rtAuth)return rtMsg('认证服务未连接：'+(rtAuthError||'请检查网络'));let contact,password=rtMode==='phone'?null:rtElem('rtNewPassword').value,confirm=rtMode==='phone'?null:rtElem('rtConfirmPassword').value;try{contact=rtContactValue()}catch(e){return rtMsg(e.message)}if(rtMode!=='phone'&&password.length<8)return rtMsg('密码至少需要 8 位');if(rtMode!=='phone'&&password!==confirm)return rtMsg('两次输入的密码不一致');rtBusy=true;rtPendingSignup=rtMode==='phone'?{phone:contact}:{email:contact,password};rtMsg('正在验证该联系方式是否已经注册…',false);try{let d;try{d=rtCheck(await rtAuth.signInWithOtp({...(rtMode==='phone'?{phone:contact}:{email:contact}),options:{shouldCreateUser:false}}))}catch(e){if(rtAccountMissingError(e)){await rtStartRealSignup();return}throw e}if(typeof d?.verifyOtp!=='function')throw Error('未返回验证码验证流程');rtVerify=d.verifyOtp;rtVerifyAction='registrationCheck';rtRender('verify');rtMsg('验证码已发送',false)}catch(e){rtPendingSignup=null;rtMsg('发送失败：'+rtErr(e))}finally{rtBusy=false}}
async function rtSendOtpLogin(){if(rtBusy)return;if(!rtAuth)return rtMsg('认证服务未连接：'+(rtAuthError||'请检查网络'));let contact;try{contact=rtContactValue()}catch(e){return rtMsg(e.message)}rtBusy=true;rtMsg('正在发送验证码…',false);try{let d=rtCheck(await rtAuth.signInWithOtp({... (rtMode==='phone'?{phone:contact}:{email:contact}),options:{shouldCreateUser:false}}));if(typeof d?.verifyOtp!=='function')throw Error('未返回验证码验证流程');rtVerify=d.verifyOtp;rtVerifyAction='login';rtRender('verify');rtMsg('验证码已发送',false)}catch(e){rtMsg('发送失败：'+rtErr(e))}finally{rtBusy=false}}
async function rtVerifyEmail(){if(rtBusy)return;let code=rtElem('rtOtp').value.trim();if(!code)return rtMsg('请输入验证码');if(typeof rtVerify!=='function')return rtMsg('验证码已失效，请重新注册');rtBusy=true;try{try{rtCheck(await rtVerify({token:code}))}catch(e){if(rtVerifyAction==='registrationCheck'&&rtAccountMissingError(e)){await rtStartRealSignup();return}throw e}if(await rtSession()){let wasCheck=rtVerifyAction==='registrationCheck';rtPendingSignup=null;rtClose();if(wasCheck){rtExistingAccountDialog()}else if(typeof toast==='function')toast(rtVerifyAction==='register'?'注册成功':'登录成功');return}rtRender('login','验证成功，请登录')}catch(e){rtMsg(rtAccountExistsError(e)?'该联系方式已经注册，请返回登录，不会创建重复账号':rtErr(e))}finally{rtBusy=false}}
function rtShowSecurity(){if(!window.rtLoggedIn)return rtShowLogin();let r=rtElem('rtAuthRoot');if(!r){r=document.createElement('div');r.id='rtAuthRoot';r.className='rt-auth';document.body.appendChild(r)}r.hidden=false;rtRender('security')}
async function rtLogout(){if(!rtAuth||rtBusy)return;rtBusy=true;try{rtCheck(await rtAuth.signOut());window.rtLoggedIn=false;rtUser=null;rtSessionKnown=true;rtStatus();if(typeof toast==='function')toast('已退出登录')}catch(e){if(typeof toast==='function')toast(rtErr(e))}finally{rtBusy=false}}
async function rtStartAuth(){try{if(!window.RTCloudbaseSDK)throw Error('CloudBase SDK 未加载');let app=window.RTCloudbaseSDK.init({env:'randomtoolbox-d5gg1p6rg1d2287eb',region:'ap-shanghai',accessKey:__RT_KEY__});rtAuth=typeof app.auth==='function'?app.auth():app.auth;await Promise.race([rtSession(),new Promise((_,reject)=>setTimeout(()=>reject(Error('登录状态检查超时，已进入离线模式')),8000))]);if(typeof rtAuth.onAuthStateChange==='function')rtAuth.onAuthStateChange(()=>{rtSession().catch(console.error)})}catch(e){rtAuthError=rtErr(e);console.error('CloudBase authentication unavailable:',e);window.rtLoggedIn=false;rtSessionKnown=true;rtStatus()}}
rtStatus();setTimeout(rtStartAuth,250);
'''.replace('__RT_KEY__', json.dumps(key))
replace('</head>', css + "\n<style id=\"rt-profile-css\">\n.rt-profile-mask{position:fixed;inset:0;z-index:2147483600;background:var(--bg,#f6f7fb);color:var(--text,#19213b);overflow:auto}\n.rt-profile-sheet{max-width:520px;margin:auto;padding:calc(env(safe-area-inset-top) + 20px) 22px 45px;text-align:center}\n.rt-profile-back{display:block;border:0;background:none;font-size:17px;color:#7463ee;padding:6px}\n.rt-profile-sheet h2{font-size:23px;margin:12px 0 20px}\n.rt-profile-main{display:block;width:116px;height:116px;border-radius:50%;background-repeat:no-repeat;border:4px solid white;box-shadow:0 8px 28px #27326426;margin:0 auto}\n.rt-profile-label{display:block;text-align:left;font-size:14px;margin:22px 0 10px}\n.rt-profile-label input{display:block;width:100%;border:1px solid var(--line,#ddd);border-radius:14px;padding:13px;margin-top:8px;background:var(--card,#fff);color:var(--text,#222)}\n.rt-profile-id{font-size:13px;color:var(--muted,#888);word-break:break-all}\n.rt-profile-note{font-size:12px;line-height:1.7;color:var(--muted,#888)}\n.rt-profile-sheet h3{text-align:left;font-size:16px;margin:25px 0 15px}\n.rt-avatar-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}\n.rt-avatar-choice{border:3px solid transparent;border-radius:50%;padding:0;background-color:transparent;background-repeat:no-repeat;aspect-ratio:1}\n.rt-avatar-choice.selected{border-color:#7463ee}\n\n.rt-upload,.rt-profile-save{display:block;width:100%;margin-top:20px;border:0;border-radius:16px;padding:15px;background:#ece9ff;color:#6752d4;font-weight:600}\n.rt-profile-save{background:#7463ee;color:#fff}\n</style>\n" + '</head>')
replace('<script>', '<script src="cloudbase-sdk.js"></script><script>')
# Keep account navigation available even when the CloudBase SDK is offline.
# A separate listener makes failures visible instead of silently ignoring taps.
account_fallback = r'''<script>
(function(){
  function showAccountError(message){
    var box=document.getElementById('rtAccountError');
    if(!box){box=document.createElement('div');box.id='rtAccountError';box.setAttribute('role','alert');box.style.cssText='position:fixed;z-index:2147483647;left:16px;right:16px;bottom:24px;padding:16px;border-radius:14px;background:#fff1f2;color:#881337;box-shadow:0 6px 30px #0003;font-size:14px';document.body.appendChild(box)}
    box.textContent=message;
  }
  document.addEventListener('click',function(event){
    var btn=event.target.closest && event.target.closest('[onclick]');
    if(!btn)return;
    var action=btn.getAttribute('onclick')||'';
    if(!(action.includes('rtShowLogin(')||action.includes('rtShowSecurity(')))return;
    if(typeof window.rtShowLogin!=='function'){
      event.preventDefault();event.stopImmediatePropagation();
      showAccountError('账号界面未加载成功，请更新应用或联系开发者。');
    }
  },true);
  window.addEventListener('error',function(event){
    if(event && event.message && /rtShowLogin|rtShowSecurity|rtRender|rtLogin/.test(event.message))showAccountError('账号功能运行错误：'+event.message);
  });
})();
</script>'''
avatar_sprite = Path('scripts/avatars-sprite.webp.b64').read_text(encoding='ascii').strip()
if not avatar_sprite or len(avatar_sprite) < 1000:
    raise SystemExit('Missing or invalid original avatar sprite')
js = js.replace('/* RT_AUTH_NATIVE_V3 */', "/* RT_AUTH_NATIVE_V3 */\nconst RT_AVATAR_SPRITE='data:image/webp;base64," + avatar_sprite + "';")

replace('</script></body></html>', '</script><script>' + js + '\n' + "\n/* RT_PROFILE_LOCAL_V1: cloud profile sync intentionally deferred */\nconst RT_AVATARS=['wolf','fox','panda','cat','bear','frog','rabbit','penguin','shiba'];\nfunction rtAvatarSrc(kind){return RT_AVATAR_SPRITE}\nfunction rtProfileKey(){let id=rtUser?.uid||rtUser?.id||rtUser?._id;return id?'rt_profile_'+String(id):null}\nfunction rtProfileGet(){let k=rtProfileKey();if(!k)return {};try{return JSON.parse(localStorage.getItem(k)||'{}')}catch(e){return {}}}\nfunction rtProfileSave(p){let k=rtProfileKey();if(!k)return;try{localStorage.setItem(k,JSON.stringify(p))}catch(e){alert('头像图片过大，无法保存在本机，请选择较小的图片')}}\nfunction rtProfileId(){return String(rtUser?.uid||rtUser?.id||rtUser?._id||'待云端分配')}\nfunction rtProfilePic(p){return p.photo||rtAvatarSrc(p.avatar||'shiba')}\nfunction rtShowProfile(){if(!window.rtLoggedIn)return rtShowLogin();let p=rtProfileGet(),root=document.getElementById('rtProfileRoot');if(!root){root=document.createElement('div');root.id='rtProfileRoot';document.body.appendChild(root)}\n root.className='rt-profile-mask';root.innerHTML='<div class=\"rt-profile-sheet\"><button class=\"rt-profile-back\" onclick=\"rtProfileClose()\">‹ 返回</button><h2>个人资料</h2><div class=\\\"rt-profile-main\\\" id=\\\"rtProfilePreview\\\" role=\\\"img\\\" aria-label=\\\"当前头像\\\"></div><label class=\"rt-profile-label\">昵称<input id=\"rtProfileName\" maxlength=\"20\" placeholder=\"请输入昵称\"></label><div class=\"rt-profile-id\">玩家 ID：<span id=\"rtProfileUid\"></span></div><p class=\"rt-profile-note\">目前仅保存到本机，云端同步将在后续版本接入。更换设备暂时无法恢复。</p><h3>选择内置头像</h3><div class=\"rt-avatar-grid\" id=\"rtAvatarGrid\"></div><label class=\"rt-upload\">从相册上传头像<input type=\"file\" accept=\"image/*\" hidden onchange=\"rtProfileUpload(event)\"></label><button class=\"rt-profile-save\" onclick=\"rtProfileCommit()\">保存资料</button></div>';\n root.querySelector('#rtProfileName').value=p.name||'';root.querySelector('#rtProfileUid').textContent=rtProfileId();window.rtProfileDraft={...p};rtProfileDraw();\n}\nfunction rtProfileClose(){let e=document.getElementById('rtProfileRoot');if(e)e.remove()}\nfunction rtProfileDraw(){let p=window.rtProfileDraft||{},root=document.getElementById('rtProfileRoot');if(!root)return;let key=p.avatar||'shiba',idx=Math.max(0,RT_AVATARS.indexOf(key)),pos=(idx%3*50)+'% '+(Math.floor(idx/3)*50)+'%';let preview=root.querySelector('#rtProfilePreview');preview.style.backgroundImage='url('+rtProfilePic(p)+')';preview.style.backgroundSize=p.photo?'cover':'300% 300%';preview.style.backgroundPosition=p.photo?'center':pos;let grid=root.querySelector('#rtAvatarGrid');grid.innerHTML=RT_AVATARS.map(k=>'<button type=\"button\" class=\"rt-avatar-choice '+(!p.photo&&key===k?'selected':'')+'\" onclick=\"rtProfileChoose(\\''+k+'\\')\" aria-label=\"'+k+'\"></button>').join('');Array.from(grid.children).forEach((el,i)=>{el.style.backgroundImage='url('+RT_AVATAR_SPRITE+')';el.style.backgroundSize='300% 300%';el.style.backgroundPosition=((i%3)*50)+'% '+(Math.floor(i/3)*50)+'%'})}\nfunction rtProfileChoose(k){window.rtProfileDraft.avatar=k;delete window.rtProfileDraft.photo;rtProfileDraw()}\nfunction rtProfileUpload(ev){let f=ev.target.files?.[0];if(!f)return;if(!f.type.startsWith('image/'))return alert('请选择图片');if(f.size>12*1024*1024)return alert('图片不能超过12MB');let reader=new FileReader();reader.onload=()=>{let im=new Image();im.onload=()=>{let c=document.createElement('canvas'),size=240;c.width=size;c.height=size;let ctx=c.getContext('2d'),side=Math.min(im.width,im.height);ctx.drawImage(im,(im.width-side)/2,(im.height-side)/2,side,side,0,0,size,size);window.rtProfileDraft.photo=c.toDataURL('image/jpeg',.78);rtProfileDraw()};im.src=reader.result};reader.readAsDataURL(f)}\nfunction rtProfileCommit(){let p=window.rtProfileDraft||{};p.name=document.getElementById('rtProfileName').value.trim().slice(0,20);if(!p.name)return alert('请输入昵称');rtProfileSave(p);rtProfileClose();if(typeof toast==='function')toast('个人资料已保存到本机')}\n" + '</script></body></html>')
replace('</body></html>', account_fallback + '</body></html>')
p.write_text(s, encoding='utf-8')
print('Injected RT_AUTH_NATIVE_V3 account UI')

# GitHub connector write access verification (dev branch only).
