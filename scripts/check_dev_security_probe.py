"""Offline test-only UI and packaging checks. No SDK/network/Android build."""
from pathlib import Path
import os, tempfile, shutil, subprocess, zipfile
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
from security_probe_manifest import create_manifest
manifest=create_manifest(ROOT)
checks=[]
def check(name, value):
 assert value,name
 checks.append(name)
# Generate HTML only in disposable directories; never alter the shared app HTML.
for enabled in ('0','1'):
 with tempfile.TemporaryDirectory() as directory:
  p=Path(directory);(p/'app/src/main/assets').mkdir(parents=True);shutil.copy(ROOT/'app/src/main/assets/index.html',p/'app/src/main/assets/index.html');shutil.copytree(ROOT/'scripts',p/'scripts');shutil.copytree(ROOT/'cloudfunctions',p/'cloudfunctions');shutil.copytree(ROOT/'deployment',p/'deployment')
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
with tempfile.TemporaryDirectory() as directory:
 target=Path(directory);shutil.copytree(ROOT/'cloudfunctions',target/'cloudfunctions');shutil.copytree(ROOT/'deployment',target/'deployment')
 changed=target/'cloudfunctions/happyboxSecurityProbeComparison/probe.cjs';changed.write_text(changed.read_text()+'\n// stale package fixture')
 rejected=False
 try:create_manifest(target)
 except ValueError:rejected=True
 check('Local package/source mismatch prevents manifest generation',rejected)
source=(ROOT/'scripts/dev-security-probe.js').read_text()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page();page.route('**/*',lambda r:r.abort())
 def setup(debug=True,expected=None):
  page.set_content('<main id="settings"></main>')
  page.evaluate('''debug=>{window.RandomToolboxNative={isSecurityProbeTestBuild:()=>debug};window.rtLoggedIn=true;window.rtUser={uid:'fixture-own'};window.calls=0;window.rtAuth={getSession:async()=>({data:{session:{user:{uid:'fixture-own'}}}})};window.rtCloudApp={callFunction:async args=>{window.args=args;calls++;return {result:{ok:true,identityVerified:true,environment:'randomtoolbox-d5gg1p6rg1d2287eb',transactionReadVerified:true,code:'READ_PREFLIGHT_COMPLETE',probeRevision:'readonly-comparison-v3',ordinaryRead:{readVerified:true,diagnosticCode:'DOCUMENT_PRESENT',documentFound:true,stageCode:null},transaction:{transactionReadVerified:true,code:'READ_PREFLIGHT_COMPLETE',phase:'COMPLETE',diagnosticCode:'DOCUMENT_PRESENT',documentFound:true},comparisonCode:'BOTH_READS_VERIFIED',token:'SECRET_FIXTURE_NOT_FOR_DISPLAY',photo:'PRIVATE_PHOTO_FIXTURE'}}}}}''',debug)
  page.evaluate('(value)=>{window.hbProbeExpected=value}',manifest if expected is None else expected)
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
 check('Success displays verified fields', '普通读取结果：本次成功' in text() and '事务读取结果：本次成功' in text() and '对照判读：BOTH_READS_VERIFIED' in text())
 check('Unknown response fields never displayed','SECRET_FIXTURE' not in text() and 'PRIVATE_PHOTO' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=async()=>({result:{ok:true,identityVerified:true,uid:'other-user',environment:'randomtoolbox-d5gg1p6rg1d2287eb',code:'READ_PREFLIGHT_COMPLETE',probeRevision:'readonly-comparison-v3'}})}");run();check('Unexpected mismatching UID cannot pass','本次成功' not in text() and 'other-user' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=async()=>({result:{ok:false,code:'PROBE_NOT_AUTHORIZED',token:'SECRET_FIXTURE'}})}");run();check('Server refusal sanitized','PROBE_NOT_AUTHORIZED' in text() and 'SECRET_FIXTURE' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=async()=>{throw Error('SECRET_FIXTURE')}}");run();check('Transport errors sanitized','调用失败' in text() and 'SECRET_FIXTURE' not in text())
 setup();page.evaluate("()=>{rtCloudApp.callFunction=()=>{calls++;return new Promise(r=>window.finishProbe=r)}}");page.locator('#rtProbeSourceChecked').check();page.locator('#rtProbeRun').click();page.evaluate("document.getElementById('rtProbeRun').click()");check('Repeated clicks coalesced',page.evaluate('calls')==1)
 page.evaluate("window.rtLoggedIn=false;finishProbe({result:{ok:true,identityVerified:true,environment:'randomtoolbox-d5gg1p6rg1d2287eb',code:'READ_PREFLIGHT_COMPLETE',probeRevision:'readonly-tx-null-v2'}})");page.wait_for_timeout(40);check('Logout discards stale identity','丢弃' in text() and 'fixture-own' not in text())
 setup();page.evaluate("()=>{window.realTimeout=window.setTimeout;window.setTimeout=(fn,ms)=>realTimeout(fn,ms===10000?20:ms);rtCloudApp.callFunction=()=>new Promise(()=>{})}");run();check('Timeout releases UI','超时' in text() and page.locator('#rtProbeRun').is_enabled())
 setup();check('Fresh confirmation is unchecked',not page.locator('#rtProbeSourceChecked').is_checked())
 check('Remote source status explicitly unknown','线上版本尚未核实' in page.locator('#rtProbeDeployment').inner_text())
 check('Actual archive SHA is displayed',manifest['packageSha256'] in page.locator('#rtProbeManifest').text_content())
 check('Old commit declaration removed','813c2f5' not in page.locator('#rtDevSecurityProbe').inner_text())
 def response_update(js):
  page.evaluate("()=>{const original=rtCloudApp.callFunction;rtCloudApp.callFunction=async args=>{const response=await original(args);"+js+";return response;}}")
 setup();response_update("Object.assign(response.result.ordinaryRead,{diagnosticCode:'DOCUMENT_ABSENT',documentFound:false});Object.assign(response.result.transaction,{diagnosticCode:'DOCUMENT_ABSENT',documentFound:false});delete response.result.uid");run()
 check('Both absent are successful without a returned UID','对照判读：BOTH_READS_VERIFIED' in text() and 'DOCUMENT_ABSENT' in text() and '不存在（正常空结果）' in text())
 setup();response_update("Object.assign(response.result,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,comparisonCode:'ORDINARY_VERIFIED_TRANSACTION_FAILED'});Object.assign(response.result.transaction,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,phase:'START',diagnosticCode:'COLLECTION_NOT_FOUND',stageCode:'START_COLLECTION_NOT_FOUND'});delete response.result.transaction.documentFound");run()
 check('Actual START failure remains independent of ordinary success','普通读取结果：本次成功' in text() and '事务读取结果：未通过' in text() and 'START_COLLECTION_NOT_FOUND' in text() and '读取：未执行' in text())
 setup();response_update("Object.assign(response.result,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,comparisonCode:'ORDINARY_VERIFIED_TRANSACTION_FAILED'});Object.assign(response.result.transaction,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,phase:'COMMIT',diagnosticCode:'PERMISSION_DENIED',stageCode:'COMMIT_PERMISSION_DENIED'});delete response.result.transaction.documentFound");run()
 check('Commit failure cannot become transaction success','事务读取结果：未通过' in text() and 'COMMIT_PERMISSION_DENIED' in text() and '读取：已完成；提交：未通过' in text())
 setup();response_update("delete response.result.probeRevision");run();check('Missing revision cannot claim read success','本次成功' not in text() and '线上版本尚未核实' in page.locator('#rtProbeDeployment').inner_text())
 setup();response_update("response.result.probeRevision='readonly-tx-null-v2'");run();check('Old V2 revision rejected','本次成功' not in text())
 setup();response_update("delete response.result.transaction");run();check('Missing transaction block cannot claim success','事务读取结果：本次成功' not in text())
 setup();response_update("delete response.result.transaction.diagnosticCode");run();check('Missing transaction diagnosis rejected','事务读取结果：本次成功' not in text())
 setup();response_update("response.result.transaction.stageCode='TOKEN_SECRET_FIXTURE';response.result.transaction.diagnosticCode='PRIVATE_PHOTO_FIXTURE';response.result.probeRevision='TOKEN_SECRET_FIXTURE'");run()
 check('Untrusted diagnostics never displayed','TOKEN_SECRET' not in text() and 'PRIVATE_PHOTO' not in text())
 setup();response_update("response.result.transaction.documentFound=false");run();check('Inconsistent presence is not success','事务读取结果：本次成功' not in text())
 setup();response_update("response.result.comparisonCode='BOTH_UNVERIFIED'");run();check('Contradictory overall result not confirmed','对照判读：BOTH_READS_VERIFIED' not in text() and '对照判读：尚未核实' in text())
 setup();response_update("response.result.ordinaryRead={readVerified:false,diagnosticCode:'PERMISSION_DENIED',stageCode:'ORDINARY_PERMISSION_DENIED',documentFound:null};response.result.comparisonCode='ORDINARY_FAILED_TRANSACTION_VERIFIED'");run();check('Ordinary refusal does not hide transaction success','普通读取结果：未通过' in text() and '事务读取结果：本次成功' in text() and '对照判读：ORDINARY_FAILED_TRANSACTION_VERIFIED' in text())
 setup();response_update("Object.assign(response.result,{ok:false,identityVerified:false,code:'PROBE_NOT_AUTHORIZED'});delete response.result.ordinaryRead;delete response.result.transaction");run();check('Matching revision with refusal never means database success','本次成功' not in text() and 'PROBE_NOT_AUTHORIZED' in text())
 setup();response_update("Object.assign(response.result,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,comparisonCode:'ORDINARY_VERIFIED_TRANSACTION_FAILED'});Object.assign(response.result.transaction,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,phase:'READ',diagnosticCode:'TRANSPORT_ERROR',stageCode:'READ_TRANSPORT_ERROR'})");run();check('Read-stage failure leaves commit unexecuted','启动：已完成；读取：未通过；提交：未执行' in text())
 setup();response_update("Object.assign(response.result,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,comparisonCode:'PROBE_BUDGET_EXCEEDED'});Object.assign(response.result.transaction,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,phase:'UNKNOWN',diagnosticCode:'PROBE_BUDGET_EXCEEDED',stageCode:'UNKNOWN_PROBE_BUDGET_EXCEEDED'})");run();check('Budget preserves known ordinary read without faking transaction stages','普通读取结果：本次成功' in text() and '对照判读：PROBE_BUDGET_EXCEEDED' in text() and '启动：未核实' in text())
 setup(expected={});check('Invalid build evidence disables invocation',page.locator('#rtProbeRun').is_disabled() and page.evaluate('calls')==0)
 browser.close()
print(f'{len(checks)} offline probe-entry checks passed; no CloudBase or APK build.')
