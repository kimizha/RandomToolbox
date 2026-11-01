"""Offline test-only UI and packaging checks. No SDK/network/Android build."""
from pathlib import Path
import os, tempfile, shutil, subprocess, zipfile
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(name, value):
 assert value,name
 checks.append(name)
# Generate HTML only in disposable directories; never alter the shared app HTML.
for enabled in ('0','1'):
 with tempfile.TemporaryDirectory() as directory:
  p=Path(directory);(p/'app/src/main/assets').mkdir(parents=True);shutil.copy(ROOT/'app/src/main/assets/index.html',p/'app/src/main/assets/index.html');shutil.copytree(ROOT/'scripts',p/'scripts')
  subprocess.run(['python3','scripts/inject_auth.py'],cwd=p,env={**os.environ,'CLOUDBASE_PUBLISHABLE_KEY':'eyJ-offline-test-only','HAPPYBOX_SECURITY_PROBE_TEST':enabled},check=True,capture_output=True)
  html=(p/'app/src/main/assets/index.html').read_text()
  check('Explicit injection flag '+enabled,('HAPPYBOX_SECURITY_PROBE_TEST_ONLY' in html)==(enabled=='1'))
with tempfile.TemporaryDirectory() as directory:
 archive=Path(directory)/'changed.zip'
 with zipfile.ZipFile(archive,'w') as z:
  for name in ('index.js','probe.cjs','package.json','package-lock.json'):
   z.writestr(name, b'changed' if name=='probe.cjs' else (ROOT/'cloudfunctions/happyboxSecurityProbe'/name).read_bytes())
 result=subprocess.run(['python3',str(ROOT/'scripts/check_probe_deployment.py'),str(archive)],capture_output=True)
 check('Tampered deployment source comparison fails',result.returncode!=0)
source=(ROOT/'scripts/dev-security-probe.js').read_text()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page();page.route('**/*',lambda r:r.abort())
 def setup(debug=True):
  page.set_content('<main id="settings"></main>')
  page.evaluate('''debug=>{window.RandomToolboxNative={isSecurityProbeTestBuild:()=>debug};window.rtLoggedIn=true;window.rtUser={uid:'fixture-own'};window.calls=0;window.rtAuth={getSession:async()=>({data:{session:{user:{uid:'fixture-own'}}}})};window.rtCloudApp={callFunction:async args=>{window.args=args;calls++;return {result:{ok:true,identityVerified:true,uid:'fixture-own',environment:'randomtoolbox-d5gg1p6rg1d2287eb',transactionReadVerified:true,code:'READ_PREFLIGHT_COMPLETE',token:'SECRET_FIXTURE_NOT_FOR_DISPLAY',photo:'PRIVATE_PHOTO_FIXTURE'}}}}}''',debug)
  page.add_script_tag(content=source)
 def run():
  page.locator('#rtProbeSourceChecked').check();page.locator('#rtProbeRun').click();page.wait_for_timeout(40)
 def text():return page.locator('#rtProbeResult').inner_text()
 setup(False);check('Non-debug runtime has no entry',page.locator('#rtDevSecurityProbe').count()==0)
 setup();check('No automatic network calls',page.evaluate('calls')==0)
 page.locator('#rtProbeRun').click();check('Source check required',page.evaluate('calls')==0)
 page.evaluate('window.rtLoggedIn=false');run();check('Guest cannot invoke',page.evaluate('calls')==0)
 setup();page.evaluate('()=>{rtAuth.getSession=async()=>({data:{session:null}})}');run();check('Frontend logged-in flag alone insufficient',page.evaluate('calls')==0)
 setup();run();check('Real session API and fixed empty request',page.evaluate("calls===1&&args.name==='happyboxSecurityProbe'&&Object.keys(args.data).length===0"))
 check('Success displays verified fields', '事务读取：本次读取成功' in text() and 'fixture-own' in text())
 check('Unknown response fields never displayed','SECRET_FIXTURE' not in text() and 'PRIVATE_PHOTO' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=async()=>({result:{ok:true,identityVerified:true,uid:'other-user',environment:'randomtoolbox-d5gg1p6rg1d2287eb',code:'READ_PREFLIGHT_COMPLETE'}})}");run();check('Mismatched UID rejected','不一致' in text() and 'other-user' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=async()=>({result:{ok:false,code:'PROBE_NOT_AUTHORIZED',token:'SECRET_FIXTURE'}})}");run();check('Server refusal sanitized','PROBE_NOT_AUTHORIZED' in text() and 'SECRET_FIXTURE' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=async()=>{throw Error('SECRET_FIXTURE')}}");run();check('Transport errors sanitized','调用失败' in text() and 'SECRET_FIXTURE' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=()=>{calls++;return new Promise(r=>window.finishProbe=r)}}");page.locator('#rtProbeSourceChecked').check();page.locator('#rtProbeRun').click();page.evaluate("document.getElementById('rtProbeRun').click()");check('Repeated clicks coalesced',page.evaluate('calls')==1)
 page.evaluate("window.rtLoggedIn=false;finishProbe({result:{ok:true,identityVerified:true,uid:'fixture-own',environment:'randomtoolbox-d5gg1p6rg1d2287eb',code:'READ_PREFLIGHT_COMPLETE'}})");page.wait_for_timeout(40);check('Logout discards stale identity','丢弃' in text() and 'fixture-own' not in text())
 setup();page.evaluate("()=>{window.realTimeout=window.setTimeout;window.setTimeout=(fn,ms)=>realTimeout(fn,ms===10000?20:ms);rtCloudApp.callFunction=()=>new Promise(()=>{})}");run();check('Timeout releases UI','超时' in text() and page.locator('#rtProbeRun').is_enabled())
 browser.close()
print(f'{len(checks)} offline probe-entry checks passed; no CloudBase or APK build.')
