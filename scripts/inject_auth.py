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
replace('<section id="settings" class="view">', '<section id="settings" class="view"><div class="panel" style="padding:16px;margin-bottom:14px"><h2>我的账号</h2><p class="hint" id="rtUserStatus">正在检查登录状态…</p><button id="rtLoginButton" class="primary" onclick="rtShowLogin()">登录 / 注册</button><button id="rtSecurityButton" class="secondary" style="display:none;width:100%;margin-top:10px" onclick="rtShowSecurity()">账号安全 ›</button><button id="rtLogoutButton" class="secondary" style="display:none;width:100%;margin-top:10px" onclick="rtLogout()">退出登录</button></div>')

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
let rtAuth=null,rtUser=null,rtVerify=null,rtPage='login',rtMode='email',rtBusy=false,rtSessionKnown=false;
function rtElem(id){return document.getElementById(id)}
function rtStatus(){
 const guest=!window.rtLoggedIn;
 if(rtElem('rtGuestBanner'))rtElem('rtGuestBanner').style.display=guest?'block':'none';
 if(rtElem('rtUserStatus'))rtElem('rtUserStatus').textContent=!rtSessionKnown?'正在检查登录状态…':guest?'游客模式 · 趣味玩法需登录':('已登录 · '+(rtUser?.username||rtUser?.email||'趣味玩法已解锁'));
 for(const [id,visible] of [['rtLoginButton',guest],['rtSecurityButton',!guest],['rtLogoutButton',!guest]])if(rtElem(id))rtElem(id).style.display=visible?'block':'none';
}
function rtShowLogin(note){if(window.rtLoggedIn)return rtShowSecurity();let r=rtElem('rtAuthRoot');if(!r){r=document.createElement('div');r.id='rtAuthRoot';r.className='rt-auth';document.body.appendChild(r)}r.hidden=false;rtRender('login',note)}
function rtClose(){const r=rtElem('rtAuthRoot');if(r)r.hidden=true;rtVerify=null}
function rtEsc(x){return String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function rtRender(page,note){rtPage=page;let r=rtElem('rtAuthRoot');if(!r)return;
 const head=(title,sub)=>`<div class="rt-head"><div class="rt-mark">✦</div><h1>${title}</h1><p>${sub}</p></div>`;
 const input=(id,label,type='text',hint='')=>`<div class="rt-field"><label for="${id}">${label}</label><div class="rt-input"><input id="${id}" type="${type}" placeholder="${hint}" ${type==='password'?'autocomplete="new-password"':''}>${type==='password'?`<button type="button" class="rt-eye" onclick="rtEye('${id}',this)">显示</button>`:''}</div></div>`;
 let body='';
 if(page==='login')body=head('欢迎回来','登录随机工具箱，开启更多有趣体验')+input('rtIdentifier','邮箱','email','请输入注册邮箱')+input('rtPassword','密码','password','请输入密码')+'<button class="rt-btn rt-primary" onclick="rtLogin()">登录</button><p class="rt-center">还没有账号？<button class="rt-link" onclick="rtRender(\'choose\')">立即注册</button></p><p class="rt-center"><button class="rt-link" onclick="rtRender(\'forgot\')">忘记密码？</button></p>';
 else if(page==='choose')body=head('创建账号','选择一种适合你的注册方式')+'<button class="rt-item" type="button" onclick="rtMsg('用户名注册正在开发中，请先使用邮箱注册。',false)"><span>用户名注册<small>开发中 · 暂不可用</small></span><span class="rt-pill">即将开放</span></button><button class="rt-item" onclick="rtMode=\'email\';rtRender(\'register\')"><span>邮箱注册<small>使用邮箱验证码完成注册</small></span><span>›</span></button>';
 else if(page==='register')body=head(rtMode==='username'?'用户名注册':'邮箱注册',rtMode==='username'?'创建专属账号，记得妥善保管密码':'验证邮箱后即可使用趣味玩法')+input('rtContact',rtMode==='username'?'用户名':'邮箱',rtMode==='username'?'text':'email',rtMode==='username'?'5–24 位字母、数字或允许的符号':'请输入邮箱')+input('rtNewPassword','设置密码','password','至少 8 位')+input('rtConfirmPassword','确认密码','password','请再次输入密码')+(rtMode==='username'?'<div class="rt-hint">请牢记用户名和密码。未绑定邮箱或手机号时，忘记密码可能无法找回。注册后建议尽快绑定联系方式。</div>':'')+`<button class="rt-btn rt-primary" onclick="rtRegister()">${rtMode==='username'?'创建账号':'发送验证码'}</button>`;
 else if(page==='verify')body=head('验证邮箱','请输入发送到邮箱的验证码')+input('rtOtp','验证码','text','请输入验证码')+'<button class="rt-btn rt-primary" onclick="rtVerifyEmail()">验证并完成注册</button>';
 else if(page==='security'){let email=rtUser?.email||rtUser?.emailAddress||'',phone=rtUser?.phone||rtUser?.phoneNumber||'';body=head('账号安全','保护好你的随机工具箱账号')+(!email&&!phone?'<div class="rt-hint">你的账号尚未绑定邮箱或手机号，建议至少绑定一种联系方式，以便日后找回密码。</div>':'')+`<div class="rt-item"><span>绑定邮箱<small>${email?rtEsc(email):'未绑定 · 后续开放绑定功能'}</small></span><span class="rt-pill">${email?'已绑定':'待绑定'}</span></div><div class="rt-item"><span>绑定手机号<small>${phone?rtEsc(phone):'未绑定 · 后续开放绑定功能'}</small></span><span class="rt-pill">${phone?'已绑定':'待绑定'}</span></div><p class="rt-footer">绑定邮箱、绑定手机号、修改密码和账号找回功能将在后续版本逐步开放。当前页面不会执行虚假的绑定操作。</p>`;}
 else if(page==='forgot')body=head('找回密码','请使用已绑定的联系方式恢复账号')+'<div class="rt-hint">安全的密码重置流程尚未开放。没有绑定联系方式的账号可能无法找回，请妥善保管密码。</div><button class="rt-btn rt-primary" onclick="rtRender(\'login\')">返回登录</button>';
 r.innerHTML=`<div class="rt-wrap"><button class="rt-back" onclick="rtBack()" aria-label="返回">‹</button>${body}<p id="rtMsg" class="rt-msg" role="status"></p></div>`;if(note)rtMsg(note,false);
}
function rtBack(){if(rtPage==='login'||rtPage==='security')rtClose();else if(rtPage==='register')rtRender('choose');else if(rtPage==='verify')rtRender('register');else rtRender('login')}
function rtEye(id,b){let x=rtElem(id);x.type=x.type==='password'?'text':'password';b.textContent=x.type==='password'?'显示':'隐藏'}
function rtMsg(m,error=true){let e=rtElem('rtMsg');if(e){e.textContent=m;e.style.color=error?'#b34458':'#7857dc'}}
function rtErr(e){let m=e?.message||e?.error_description||String(e||'网络请求失败');if(/failed to fetch|networkerror|load failed/i.test(m)){let origin=location.origin||'(无来源)';return '网络请求失败。页面来源：'+origin+'；网络状态：'+(navigator.onLine?'在线':'离线')+'。请检查 CloudBase 安全域名、手机网络及 VPN。原始错误：'+m}return m}
function rtCheck(r){if(r?.error)throw r.error;return r?.data}
async function rtSession(){let r=await rtAuth.getSession();rtCheck(r);let d=r?.data||{};window.rtLoggedIn=!!d.session;rtUser=d.user||d.session?.user||null;rtSessionKnown=true;rtStatus();return window.rtLoggedIn}
async function rtFinishLogin(result){rtCheck(result);if(!(await rtSession()))throw Error('未获得有效登录会话，请重试');rtClose();if(typeof toast==='function')toast('登录成功')}
async function rtLogin(){if(rtBusy)return;if(!rtAuth)return rtMsg('认证服务未连接，请检查网络');let id=rtElem('rtIdentifier').value.trim(),password=rtElem('rtPassword').value;if(!id||!password)return rtMsg('请输入邮箱和密码');if(!/^\S+@\S+\.\S+$/.test(id))return rtMsg('目前仅支持邮箱登录');rtBusy=true;try{await rtFinishLogin(await rtAuth.signInWithPassword({... (id.includes('@')?{email:id}:{username:id}),password}))}catch(e){rtMsg(rtErr(e))}finally{rtBusy=false}}
async function rtRegister(){if(rtBusy)return;if(!rtAuth)return rtMsg('认证服务未连接，请检查网络');let contact=rtElem('rtContact').value.trim(),password=rtElem('rtNewPassword').value,confirm=rtElem('rtConfirmPassword').value;if(rtMode==='username')return rtMsg('用户名注册暂不可用，请使用邮箱注册');if(rtMode==='username'&&!/^[A-Za-z0-9][A-Za-z0-9_.:+@-]{4,23}$/.test(contact))return rtMsg('用户名须为 5–24 位，以字母或数字开头');if(rtMode==='email'&&!/^\S+@\S+\.\S+$/.test(contact))return rtMsg('请输入正确的邮箱');if(password.length<8)return rtMsg('密码至少需要 8 位');if(password!==confirm)return rtMsg('两次输入的密码不一致');rtBusy=true;try{let r=await rtAuth.signUp({... (rtMode==='email'?{email:contact}:{username:contact}),password});let d=rtCheck(r);if(typeof d?.verifyOtp==='function'){rtVerify=d.verifyOtp;rtRender('verify');return}if(await rtSession()){rtClose();if(typeof toast==='function')toast('注册成功');return}rtMsg(rtMode==='username'?'后台未返回可用登录会话。当前 CloudBase 可能不支持直接用户名注册，需配置服务端注册接口。':'注册请求已返回，但尚未建立登录会话。请尝试使用密码登录。')}catch(e){rtMsg(rtErr(e))}finally{rtBusy=false}}
async function rtVerifyEmail(){if(rtBusy)return;let code=rtElem('rtOtp').value.trim();if(!code)return rtMsg('请输入验证码');if(typeof rtVerify!=='function')return rtMsg('验证码已失效，请重新注册');rtBusy=true;try{let r=await rtVerify({token:code});rtCheck(r);if(await rtSession()){rtClose();if(typeof toast==='function')toast('注册成功');return}rtRender('login','邮箱验证成功，请使用邮箱和密码登录')}catch(e){rtMsg(rtErr(e))}finally{rtBusy=false}}
function rtShowSecurity(){if(!window.rtLoggedIn)return rtShowLogin();let r=rtElem('rtAuthRoot');if(!r){r=document.createElement('div');r.id='rtAuthRoot';r.className='rt-auth';document.body.appendChild(r)}r.hidden=false;rtRender('security')}
async function rtLogout(){if(!rtAuth||rtBusy)return;rtBusy=true;try{rtCheck(await rtAuth.signOut());window.rtLoggedIn=false;rtUser=null;rtSessionKnown=true;rtStatus();if(typeof toast==='function')toast('已退出登录')}catch(e){if(typeof toast==='function')toast(rtErr(e))}finally{rtBusy=false}}
async function rtStartAuth(){try{if(!window.RTCloudbaseSDK)throw Error('CloudBase SDK 未加载');let app=window.RTCloudbaseSDK.init({env:'randomtoolbox-d5gg1p6rg1d2287eb',region:'ap-shanghai',accessKey:__RT_KEY__});rtAuth=typeof app.auth==='function'?app.auth():app.auth;await rtSession();if(typeof rtAuth.onAuthStateChange==='function')rtAuth.onAuthStateChange(()=>{rtSession().catch(console.error)})}catch(e){console.error('CloudBase authentication unavailable:',e);window.rtLoggedIn=false;rtSessionKnown=true;rtStatus()}}
rtStatus();rtStartAuth();
'''.replace('__RT_KEY__', json.dumps(key))
replace('</head>', css + '</head>')
replace('<script>', '<script src="cloudbase-sdk.js"></script><script>')
replace('</script></body></html>', js + '\n</script></body></html>')
p.write_text(s, encoding='utf-8')
print('Injected RT_AUTH_NATIVE_V3 account UI')

# GitHub connector write access verification (dev branch only).
