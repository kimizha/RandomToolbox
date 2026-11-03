"""Offline browser regression: local export, credential exclusion and paused sync. No APK/cloud."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import functools, json, os, shutil, subprocess, tempfile, threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
checks = []

def check(name, value):
    assert value, name
    checks.append(name)
    print('PASS ' + name)

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

with tempfile.TemporaryDirectory(prefix='happybox-backup-test-') as tmp:
    preview = Path(tmp)
    for name in ['app', 'scripts']:
        shutil.copytree(ROOT / name, preview / name)
    subprocess.run(['python3', 'scripts/inject_auth.py'], cwd=preview,
                   env={**os.environ, 'CLOUDBASE_PUBLISHABLE_KEY': 'eyJ-offline-fixture-only', 'HAPPYBOX_SECURITY_PROBE_TEST': '0'},
                   check=True, capture_output=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(preview / 'app/src/main/assets')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 390, 'height': 844}, accept_downloads=True)
            errors, external = [], []
            page.on('pageerror', lambda err: errors.append(str(err)))
            def route(request):
                if request.request.url.startswith('http://127.0.0.1:'):
                    if request.request.url.endswith('/cloudbase-sdk.js'):
                        request.fulfill(body='', content_type='application/javascript')
                    else:
                        request.continue_()
                else:
                    external.append(request.request.url)
                    request.abort()
            page.route('**/*', route)
            page.add_init_script('''
              window.cloudCalls=0;
              window.RTCloudbaseSDK={init:()=>({
                auth:()=>({getSession:async()=>({data:{session:{user:{uid:'fixture-a'}}}}),onAuthStateChange:()=>{}}),
                database:()=>{cloudCalls++;throw Error('Cloud access forbidden in offline test')}
              })};
            ''')
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.wait_for_timeout(400)
            profile = json.dumps({'name': '本机昵称', 'avatar': 'fox', 'photo': 'data:image/jpeg;base64,LOCAL_ONLY_PHOTO'}, ensure_ascii=False)
            own = {'rt_settings': '{"dark":false,"vibe":true}', 'rt_wheelItems': '["火锅","米饭"]', 'rt_drawItems': '["小甲","小乙"]',
                   'rt_favorites': '["wheel","coin"]', 'rt_profile_fixture-a': profile,
                   'rt_profile_fixture-b': '{"name":"另一账号本机修改"}', 'rt_sync_active_uid': 'fixture-a',
                   'rt_sync_guest_cache': '{"values":{"rt_wheelItems":"[\\"游客甲\\",\\"游客乙\\"]"}}',
                   'rt_sync_cache_fixture-a': json.dumps({'values': {'rt_profile_fixture-a': profile}, 'baseline': {}}),
                   'hb_party_local_v1': '{"version":1,"boards":[{"name":"本机流水","amount":565}]}',
                   'rt_history': 'legacy damaged JSON kept byte-for-byte', 'hb_start_page': 'games'}
            excluded = {'cloudbase-session': 'SDK_SESSION_SENTINEL', 'access_token': 'ACCESS_SENTINEL',
                        'refresh_token': 'REFRESH_SENTINEL', 'rt_auth_token': 'AUTH_SENTINEL', 'unknown-key': 'OTHER_SENTINEL'}
            page.evaluate('data=>{localStorage.clear();for(const [k,v] of Object.entries(data))localStorage.setItem(k,v);go("settings")}', {**own, **excluded})
            before = page.evaluate('JSON.stringify(Object.fromEntries(Object.entries(localStorage).sort()))')
            exported = json.loads(page.evaluate('rtBuildLocalBackup()'))
            check('Backup preserves schema:2 contract and every allowed raw value', exported['accountBackupSchema'] == 2 and exported['storage'] == own)
            check('User photo, all retained UID caches and legacy favorite order remain intact', exported['storage']['rt_profile_fixture-a'] == profile and exported['storage']['rt_favorites'] == '["wheel","coin"]')
            check('Credentials and unknown storage excluded', all(key not in exported['storage'] for key in excluded) and not any(value in json.dumps(exported) for value in excluded.values()))
            check('Generating export does not mutate local data', page.evaluate('JSON.stringify(Object.fromEntries(Object.entries(localStorage).sort()))') == before)
            with page.expect_download() as download_info:
                page.locator('.rt-local-backup button').click()
            download = download_info.value
            target = preview / 'saved-backup.json'
            download.save_as(target)
            check('Browser downloads a real parseable UTF-8 JSON backup', json.loads(target.read_text())['storage'] == own and download.suggested_filename.endswith('.json'))
            check('Browser does not falsely claim file-save completion', '请求下载' in page.locator('#toast').inner_text())
            page.evaluate('''window.nativeCalls=[];window.RandomToolboxNative={exportLocalBackup:(json,id)=>nativeCalls.push({json,id})};rtExportLocalBackup();rtExportLocalBackup()''')
            check('Native save requested once; repeated taps blocked and data unchanged', page.evaluate('nativeCalls.length') == 1 and json.loads(page.evaluate('nativeCalls[0].json'))['storage'] == own)
            check('Native save button disabled pending actual file result', page.locator('.rt-local-backup button').is_disabled())
            page.evaluate('rtBackupExportFinished("unrelated-request", "SAVED")')
            check('Unrelated callback cannot claim success', page.locator('.rt-local-backup button').is_disabled())
            page.evaluate('rtBackupExportFinished(nativeCalls[0].id,"CANCELLED")')
            check('Cancel releases controls and preserves all original data', not page.locator('.rt-local-backup button').is_disabled() and '取消' in page.locator('#toast').inner_text() and page.evaluate('JSON.stringify(Object.fromEntries(Object.entries(localStorage).sort()))') == before)
            page.evaluate('rtExportLocalBackup();rtBackupExportFinished(nativeCalls.at(-1).id,"FAILED")')
            check('Write failure reports failure, never saved', '未保存' in page.locator('#toast').inner_text())
            page.evaluate('rtExportLocalBackup();rtBackupExportFinished(nativeCalls.at(-1).id,"SAVED")')
            check('Only successful native completion reports saved', '已保存' in page.locator('#toast').inner_text())
            page.evaluate('window.RandomToolboxNative={};rtExportLocalBackup()')
            check('Older APK without SAF bridge is clearly identified', '当前 APK 暂不支持' in page.locator('#toast').inner_text())
            page.evaluate('''window.RandomToolboxNative={exportLocalBackup:()=>{throw Error('fixture')}};rtExportLocalBackup()''')
            check('Bridge exception clears pending state safely', page.evaluate('rtBackupPending===null') and '未保存' in page.locator('#toast').inner_text())
            page.evaluate('window.rtLoggedIn=false;rtUser=null;rtStatus()')
            check('Backup remains available without login', page.locator('.rt-local-backup button').is_visible() and page.evaluate('JSON.parse(rtBuildLocalBackup()).storage["rt_profile_fixture-a"]') == profile)
            page.evaluate('window.rtLoggedIn=true;rtUser={uid:"fixture-a"};rtSyncAccountChanged();rtSyncPanel()')
            check('Sync panel blocks cloud writes and offers local backup', page.locator('#rtSyncRetry').is_disabled() and page.locator('#rtSyncBackup').is_visible() and '暂时暂停' in page.locator('.rt-sync-modal').inner_text())
            page.locator('#rtSyncClose').click()
            for width in [320, 390, 768]:
                page.set_viewport_size({'width': width, 'height': 844})
                for dark in [True, False]:
                    page.evaluate('dark=>setSetting("dark",dark)', dark)
                    check(f'{width}px dark={dark}: no overflow', page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            check('All startup, edit, foreground and export operations leave cloud untouched', page.evaluate('cloudCalls') == 0 and not external)
            # Read exceptions and oversize backups must not silently export incomplete data.
            page.evaluate('''window.backupReadFailed=false;const saved=Storage.prototype.getItem;
              Storage.prototype.getItem=function(){throw Error('fixture')};
              try{rtBuildLocalBackup()}catch(_){backupReadFailed=true}finally{Storage.prototype.getItem=saved}''')
            check('Storage read failure aborts export', page.evaluate('backupReadFailed'))
            page.evaluate('''window.backupLimitFailed=false;const saved=Storage.prototype.getItem;
              Storage.prototype.getItem=function(k){return k==='rt_wheelItems'?'界'.repeat(6*1024*1024):saved.call(this,k)};
              try{rtBuildLocalBackup()}catch(_){backupLimitFailed=true}finally{Storage.prototype.getItem=saved}''')
            check('Backup limit counts UTF-8 bytes and fails without altering storage', page.evaluate('backupLimitFailed'))
            check('No browser runtime errors', not errors)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
print(f'{len(checks)} offline local-backup checks passed; no CloudBase calls or APK build.')
