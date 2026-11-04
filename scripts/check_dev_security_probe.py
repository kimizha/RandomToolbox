"""Offline integration of the actual auth initializer, attached SDK and diagnostic UI."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import functools, json, os, shutil, subprocess, tempfile, threading
from playwright.sync_api import sync_playwright
from security_probe_manifest import create_manifest

ROOT=Path(__file__).resolve().parents[1]
manifest=create_manifest(ROOT)
checks=[]
def check(name,value):
 assert value,name
 checks.append(name)
 print('PASS '+name)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

FIXTURE=r'''
window.fixture={uid:'PRIVATE_UID_SENTINEL',debug:true,calls:0,init:0,db:0,login:0,sessionError:false,throwCall:false,callError:null,pending:false,sessionReads:0};
fixture.result={ok:true,identityVerified:true,environment:'randomtoolbox-d5gg1p6rg1d2287eb',probeRevision:'readonly-comparison-v3',code:'READ_PREFLIGHT_COMPLETE',transactionReadVerified:true,ordinaryRead:{readVerified:true,diagnosticCode:'DOCUMENT_PRESENT',documentFound:true,stageCode:null},transaction:{transactionReadVerified:true,code:'READ_PREFLIGHT_COMPLETE',phase:'COMPLETE',diagnosticCode:'DOCUMENT_PRESENT',documentFound:true},comparisonCode:'BOTH_READS_VERIFIED',token:'TOKEN_SENTINEL',photo:'PHOTO_SENTINEL'};
window.RandomToolboxNative={isSecurityProbeTestBuild:()=>fixture.debug};
window.RTCloudbaseSDK={init:config=>{
 fixture.init++;fixture.config=config;
 const auth={getSession:async()=>{fixture.sessionReads++;if(fixture.sessionError)throw Error('TOKEN_SENTINEL');return {data:{session:fixture.uid?{user:{uid:fixture.uid}}:null}}},onAuthStateChange:()=>{},signInWithPassword:()=>{fixture.login++;throw Error('must not log in')}};
 fixture.sdk={auth:()=>auth,database:()=>{fixture.db++;throw Error('business DB access forbidden')},callFunction:async args=>{fixture.calls++;fixture.args=args;if(fixture.throwCall)throw Object.assign(Error('TOKEN_SENTINEL'),{code:fixture.callError});if(fixture.pending)return new Promise(resolve=>fixture.finish=resolve);return {result:fixture.result}}};
 return fixture.sdk;
}};
'''

with tempfile.TemporaryDirectory(prefix='happybox-probe-ui-') as directory:
 root=Path(directory)
 for mode in ['normal','probe']:
  target=root/mode
  for name in ['app','scripts','cloudfunctions','deployment']:shutil.copytree(ROOT/name,target/name)
  subprocess.run(['python3','scripts/inject_auth.py'],cwd=target,env={**os.environ,'CLOUDBASE_PUBLISHABLE_KEY':'eyJ-offline-fixture-only','HAPPYBOX_SECURITY_PROBE_TEST':'1' if mode=='probe' else '0','HAPPYBOX_DATA_PROTECTION_TEST':'0'},capture_output=True,check=True)
  html=(target/'app/src/main/assets/index.html').read_text()
  check(mode+' opt-in packages adapter and UI together',('window.hbAttachProbeContext({app,auth:rtAuth,' in html)==(mode=='probe') and ('HAPPYBOX_SECURITY_PROBE_TEST_ONLY' in html)==(mode=='probe'))
 # This verifies source/archive agreement without executing any deployment package.
 check('Local reviewed package manifest remains V3',manifest['revision']=='readonly-comparison-v3')
 changed=root/'probe/cloudfunctions/happyboxSecurityProbeComparison/probe.cjs'
 original=changed.read_text();changed.write_text(original+'\n// mismatch fixture')
 rejected=False
 try:create_manifest(root/'probe')
 except ValueError:rejected=True
 changed.write_text(original)
 check('Changed function source cannot pass local manifest',rejected)
 server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as pw:
   executable=os.environ.get('HAPPYBOX_TEST_BROWSER') or shutil.which('chromium') or shutil.which('google-chrome')
   browser=pw.chromium.launch(executable_path=executable,args=['--no-sandbox'])
   page=browser.new_page(viewport={'width':390,'height':844});errors=[];external=[]
   page.on('pageerror',lambda error:errors.append(str(error)))
   def route(r):
    if r.request.url.startswith('http://127.0.0.1:'):
     if r.request.url.endswith('cloudbase-sdk.js'):r.fulfill(body='',content_type='application/javascript')
     else:r.continue_()
    else:external.append(r.request.url);r.abort()
   page.route('**/*',route);page.add_init_script(FIXTURE)
   def setup(code='',mode='probe'):
    page.goto(f'http://127.0.0.1:{server.server_port}/{mode}/app/src/main/assets/index.html')
    page.wait_for_timeout(350)
    if code:page.evaluate('async()=>{'+code+'}')
    page.evaluate("go('settings')")
   def run():page.locator('#rtProbeRun').click();page.wait_for_timeout(40)
   def text():return page.locator('#rtProbeResult').inner_text()
   def conclusion():return page.locator('.hb-probe-conclusion strong').inner_text()
   def change(code):page.evaluate('()=>{const r=fixture.result;'+code+'}')
   def tx_failure(phase='START',diagnostic='COLLECTION_NOT_FOUND',comparison='ORDINARY_VERIFIED_TRANSACTION_FAILED'):
    change("Object.assign(r,{code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,comparisonCode:"+json.dumps(comparison)+"});r.transaction={code:'TRANSACTION_READ_NOT_VERIFIED',transactionReadVerified:false,phase:"+json.dumps(phase)+",diagnosticCode:"+json.dumps(diagnostic)+",stageCode:"+json.dumps(phase+'_'+diagnostic)+"}")
   setup(mode='normal');check('Normal build contains neither test entry nor adapter',page.locator('#rtDevSecurityProbe').count()==0 and page.evaluate('typeof window.hbAttachProbeContext')=='undefined')
   setup('fixture.debug=false');page.reload();page.wait_for_timeout(350)
   # The native build guard is also tested without trusting a frontend marker.
   page.evaluate("document.getElementById('rtDevSecurityProbe').remove();fixture.debug=false")
   page.add_script_tag(content=(ROOT/'scripts/dev-security-probe.js').read_text())
   check('Non-Debug runtime does not create entry',page.locator('#rtDevSecurityProbe').count()==0)
   setup();check('One original SDK initialization, no automatic probe or business read',page.evaluate('fixture.init===1&&fixture.calls===0&&fixture.db===0&&fixture.login===0'))
   check('Original environment and region reused',page.evaluate("fixture.config.env==='randomtoolbox-d5gg1p6rg1d2287eb'&&fixture.config.region==='ap-shanghai'"))
   check('One-click button, no manual source checkbox',page.locator('#rtProbeRun').inner_text()=='数据库连接测试（只读）' and page.locator('#rtProbeSourceChecked').count()==0)
   check('Remote source remains explicitly unverified','线上源码摘要尚未核实' in page.locator('#rtProbeDeployment').text_content())
   run();check('SDK call uses fixed function and exact empty data',page.evaluate("fixture.calls===1&&fixture.args.name==='happyboxSecurityProbe'&&Object.keys(fixture.args.data).length===0"))
   check('Actual attached instance succeeds without re-login',conclusion()=='BOTH_READS_VERIFIED' and page.evaluate('fixture.init===1&&fixture.login===0&&fixture.sessionReads>=3'))
   check('Three separate result cards',page.locator('.hb-probe-part').count()==3)
   page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async value=>window.copied=value}})")
   page.locator('#rtProbeCopy').click();page.wait_for_timeout(30)
   check('Copied summary contains no UID, credentials or arbitrary response fields',page.evaluate("copied.includes('BOTH_READS_VERIFIED')&&!/PRIVATE_UID_SENTINEL|TOKEN_SENTINEL|PHOTO_SENTINEL/.test(copied)"))
   check('Display excludes UID and unknown response fields',not any(s in text() for s in ['PRIVATE_UID_SENTINEL','TOKEN_SENTINEL','PHOTO_SENTINEL']))
   setup('fixture.uid=null;await rtSession()');run();check('Logged-out session is rejected without function call',conclusion()=='PROBE_NOT_AUTHORIZED' and page.evaluate('fixture.calls')==0)
   setup('fixture.uid=null;window.rtLoggedIn=true');run();check('Frontend login flag cannot replace SDK session',page.evaluate('fixture.calls')==0 and '无有效会话' in text())
   setup('fixture.sessionError=true');run();check('Session error sanitized, no function call',conclusion()=='SESSION_CHECK_FAILED' and 'TOKEN_SENTINEL' not in text() and page.evaluate('fixture.calls')==0)
   setup('hbAttachProbeContext({})');run();check('Uninitialized SDK reports not ready',conclusion()=='SDK_NOT_READY' and page.evaluate('fixture.calls')==0)
   setup("hbAttachProbeContext({app:fixture.sdk,auth:fixture.sdk.auth(),currentUser:()=>rtUser,syncPaused:()=>false})");run();check('Sync pause is a precondition, never changed',conclusion()=='SYNC_NOT_PAUSED' and page.evaluate('fixture.calls')==0)
   setup('fixture.throwCall=true');run();check('Network/function error safely reported',conclusion()=='PROBE_CALL_FAILED' and 'TOKEN_SENTINEL' not in text())
   setup("fixture.throwCall=true;fixture.callError='FUNCTION_NOT_FOUND'");run();check('Missing function halts without fallback deployment',conclusion()=='PROBE_FUNCTION_NOT_FOUND' and page.locator('#rtProbeRun').is_disabled())
   setup();change("r.probeRevision='readonly-tx-null-v2'");run();check('V2 revision stops with explicit mismatch',conclusion()=='PROBE_REVISION_MISMATCH' and page.locator('#rtProbeRun').is_disabled() and '本次成功' not in text())
   setup();change('delete r.probeRevision');run();check('Missing revision cannot succeed',conclusion()=='PROBE_REVISION_MISMATCH')
   setup();change("r.ok=false;r.identityVerified=false;r.code='PROBE_NOT_AUTHORIZED'");run();check('Server whitelist refusal respected',conclusion()=='PROBE_NOT_AUTHORIZED' and '本次成功' not in text())
   setup();change("r.uid='OTHER_PRIVATE_UID'");run();check('Unexpected UID mismatch rejected without display',conclusion()=='PROBE_NOT_AUTHORIZED' and 'OTHER_PRIVATE_UID' not in text())
   setup();change("r.environment='wrong'");run();check('Environment mismatch is not success',conclusion()=='BOTH_UNVERIFIED' and '本次成功' not in text())
   setup();change("for(const x of [r.ordinaryRead,r.transaction]){x.diagnosticCode='DOCUMENT_ABSENT';x.documentFound=false}");run();check('Empty collection absence verifies both reads',conclusion()=='BOTH_READS_VERIFIED' and text().count('不存在（正常空结果）')==2)
   setup();change("r.ordinaryRead={readVerified:false,diagnosticCode:'PERMISSION_DENIED',stageCode:'ORDINARY_PERMISSION_DENIED'};r.comparisonCode='ORDINARY_FAILED_TRANSACTION_VERIFIED'");run();check('Ordinary failure is independent of verified transaction',conclusion()=='ORDINARY_READ_FAILED' and 'ORDINARY_PERMISSION_DENIED' in text())
   for phase in ['START','READ','COMMIT']:
    setup();tx_failure(phase);run();check(phase+' transaction failure preserves ordinary success',conclusion()=='TRANSACTION_READ_FAILED' and phase+'_COLLECTION_NOT_FOUND' in text())
    states=page.locator('.hb-probe-part').nth(2).inner_text()
    check(phase+' transaction stages reported accurately',('未执行' in states) if phase in ['START','READ'] else ('已完成' in states and '未通过' in states))
   setup();tx_failure(comparison='BOTH_UNVERIFIED');change("r.ordinaryRead={readVerified:false,diagnosticCode:'COLLECTION_NOT_FOUND',stageCode:'ORDINARY_COLLECTION_NOT_FOUND'}");run();check('Both failures never masquerade as empty success',conclusion()=='BOTH_UNVERIFIED' and '本次成功' not in text())
   setup();tx_failure('UNKNOWN','PROBE_BUDGET_EXCEEDED','PROBE_BUDGET_EXCEEDED');run();check('Budget timeout does not invent transaction stages',conclusion()=='TRANSACTION_READ_FAILED' and '尚未核实' in page.locator('.hb-probe-part').nth(2).inner_text())
   setup();change("r.comparisonCode='BOTH_UNVERIFIED'");run();check('Contradictory overall result cannot pass',conclusion()=='BOTH_UNVERIFIED')
   setup();change('r.transaction.documentFound=false');run();check('Inconsistent presence cannot pass',conclusion()!='BOTH_READS_VERIFIED')
   setup();change("r.transaction.diagnosticCode='TOKEN_SENTINEL';r.transaction.stageCode='PHOTO_SENTINEL'");run();check('Unrecognized diagnostic fields suppressed',not any(s in text() for s in ['TOKEN_SENTINEL','PHOTO_SENTINEL']) and conclusion()!='BOTH_READS_VERIFIED')
   setup();change('delete r.transaction');run();check('Missing transaction evidence is not success',conclusion()=='TRANSACTION_READ_FAILED')
   setup('fixture.pending=true');run();page.evaluate("document.getElementById('rtProbeRun').click()")
   check('Spinner and duplicate-click protection active',page.locator('#rtProbeSpinner').is_visible() and page.locator('#rtProbeRun').is_disabled() and page.evaluate('fixture.calls')==1)
   page.evaluate('async()=>{fixture.uid=null;await rtSession();fixture.finish({result:fixture.result})}');page.wait_for_timeout(50)
   check('Logout discards an in-flight result',conclusion()=='ACCOUNT_CHANGED' and '本次成功' not in text())
   setup('fixture.pending=true');run();page.evaluate("fixture.uid='OTHER_PRIVATE_UID';fixture.finish({result:fixture.result})");page.wait_for_timeout(50)
   check('Post-call SDK identity change rejects stale result',conclusion()=='ACCOUNT_CHANGED' and 'OTHER_PRIVATE_UID' not in text())
   setup("fixture.pending=true;const original=setTimeout;window.setTimeout=(fn,ms)=>original(fn,ms===12000?20:ms)");run()
   check('UI timeout does not allow overlapping SDK request',conclusion()=='PROBE_TIMEOUT' and page.locator('#rtProbeRun').is_disabled())
   page.evaluate('fixture.finish({result:fixture.result})');page.wait_for_timeout(50)
   check('Late success cannot overwrite timeout; retry waits for settlement',conclusion()=='PROBE_TIMEOUT' and page.locator('#rtProbeRun').is_enabled() and page.evaluate('fixture.calls')==1)
   setup();page.evaluate("localStorage.setItem('rt_profile_PRIVATE_UID_SENTINEL',JSON.stringify({name:'保留昵称',avatar:'cat'}));save('wheelItems',['保留甲','保留乙']);save('favorites',['wheel']);window.snapshot=JSON.stringify(Object.fromEntries(Object.entries(localStorage).sort()))")
   run();check('Probe never changes local preferences, backup or synchronization state',page.evaluate("snapshot===JSON.stringify(Object.fromEntries(Object.entries(localStorage).sort()))&&RT_SYNC_CLOUD_PAUSED===true&&fixture.db===0"))
   check('Backup entry is retained',page.locator('.rt-local-backup button').is_visible())
   for width in [320,390,768]:
    page.set_viewport_size({'width':width,'height':844})
    for dark in [True,False]:
     page.evaluate('dark=>setSetting("dark",dark)',dark)
     check(f'{width}px dark={dark}: no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
   page.set_viewport_size({'width':390,'height':844});page.locator('#rtDevSecurityProbe').scroll_into_view_if_needed()
   screenshot=os.environ.get('HAPPYBOX_PROBE_SCREENSHOT')
   if screenshot:page.screenshot(path=screenshot,full_page=True)
   check('No external network or runtime errors',not external and not errors)
   browser.close()
 finally:server.shutdown();server.server_close()
print(f'{len(checks)} offline probe-entry integration checks passed; no real CloudBase calls or writes.')
