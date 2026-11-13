"""Offline browser regression against the actual packaged HTML; never inject accounts."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading,functools,json,shutil,re
from playwright.sync_api import sync_playwright
from ui_test_helpers import choose
ROOT=Path(__file__).resolve().parents[1];assets=ROOT/'app/src/main/assets';checks=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(assets)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox']);context=browser.new_context();page=context.new_page();errors=[];external=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 origin=f'http://127.0.0.1:{server.server_port}'
 def route(r):
  if r.request.url.startswith(origin):r.continue_()
  else:external.append(r.request.url);r.abort()
 context.route('**/*',route)
 seed={'rt_favorites':'["wheel","coin","draw"]','rt_wheelItems':'["旧配置甲","旧配置乙"]','rt_drawItems':'["甲","乙"]','rt_history':'[{"type":"coin","value":"正面"}]','rt_settings':'{"dark":true,"sound":false,"vibe":false,"volume":55,"speed":"fast"}','rt_sync_active_uid':'legacy-owner','rt_profile_legacy-owner':'{"nickname":"保留原始数据"}','rt_sync_cache_legacy-owner':'{"values":{"rt_wheelItems":"[\"缓存甲\",\"缓存乙\"]"}}'}
 context.add_init_script('if(!localStorage.getItem("fixture")){const data='+json.dumps(seed)+';Object.entries(data).forEach(([k,v])=>localStorage.setItem(k,v));localStorage.setItem("fixture","1")}')
 page.goto(origin);page.wait_for_timeout(200)
 check('Startup preserves all legacy keys byte-for-byte',page.evaluate('data=>Object.entries(data).every(([k,v])=>localStorage.getItem(k)===v)',seed))
 check('Favorites preserve historical order',page.evaluate('JSON.stringify(favorites)')==seed['rt_favorites'])
 check('No SDK or authentication globals',page.evaluate('typeof RTCloudbaseSDK==="undefined"&&typeof rtAuth==="undefined"&&typeof rtLoggedIn==="undefined"'))
 for tab in ['home','catalog','games','settings','manage']:
  page.evaluate('id=>go(id)',tab);check(tab+' navigates',page.locator('#'+tab).is_visible())
 page.evaluate("go('settings')")
 check('No account entry or guest prompts',not re.search('登录|注册|游客|云端同步|个人资料|玩家 ID',page.locator('body').inner_text()))
 check('Local backup retains original data',json.loads(page.evaluate('rtBuildLocalBackup()'))['storage']['rt_profile_legacy-owner']==seed['rt_profile_legacy-owner'])
 check('Backup has no network dependency',page.locator('[data-rt-backup-export]').count()==1)
 page.evaluate("moveFav('draw',-1)");check('Favorite reorder persisted',page.evaluate('localStorage.rt_favorites')=='["wheel","draw","coin"]')
 page.reload();check('Reorder survives restart',page.evaluate('JSON.stringify(favorites)')=='["wheel","draw","coin"]')
 page.evaluate("openTool('wheel');openToolConfig('wheel')");page.locator('#wheelInput').fill('新选项甲\n新选项乙');page.evaluate('saveToolConfig()');page.reload();check('Wheel saved across restart',page.evaluate('JSON.stringify(wheelItems)')=='["新选项甲","新选项乙"]')
 for tool in ['coin','number','wheel','dice','rps','draw','score']:
  page.evaluate('id=>openTool(id)',tool);check(tool+' tool opens',page.locator('#tool' if tool!='score' else '#game').is_visible())
  page.evaluate("if(window.HBParty?.active)HBParty.active.stage='end';party.stage='end';go('home')")
 for game in ['wolf','spy','truth','soup']:
  page.evaluate('id=>openGame(id)',game);check(game+' game accessible',page.locator('#game').is_visible());page.evaluate("party.stage='end';go('home')")
 for game in ['bomb','charades','taboo']:
  page.evaluate('id=>HBParty.open(id)',game);check(game+' offline game accessible',page.locator('#game').is_visible());page.evaluate("HBParty.active.stage='end';party.stage='end';go('home')")
 page.evaluate("setSetting('dark',false)");page.reload();check('Theme persists',not page.locator('body').evaluate("e=>e.classList.contains('dark')"))
 page.evaluate("go('settings')");check('Music files load locally',page.locator('#offlineMusic').evaluate('e=>e.src.includes("/music/")') and page.locator('#offlineTrack option').count()==6)
 choose(page,'#offlineTrack','1');page.locator('#musicVolume').evaluate("e=>e.value='40'");page.locator('#musicVolume').dispatch_event('input');page.reload();check('Music controls persist',page.locator('#offlineTrack').input_value()=='1' and page.locator('#offlineMusic').evaluate('e=>e.volume')==.4)
 page.evaluate("openTool('coin');appBack()");check('Android Back returns to tools',page.locator('#catalog').is_visible())
 check('No external requests',not external);check('No runtime errors',not errors)
 browser.close()
server.shutdown()
print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=False,indent=2))
