from playwright.sync_api import sync_playwright
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading,functools,json,tempfile,shutil,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
preview=Path(tempfile.mkdtemp(prefix="happybox-ui-"))
for name in ["app","scripts"]:shutil.copytree(ROOT/name,preview/name)
subprocess.run(["python3","scripts/inject_auth.py"],cwd=preview,env={**os.environ,"CLOUDBASE_PUBLISHABLE_KEY":"eyJ-ui-offline-validation"},check=True)
OUT=ROOT/"docs/ui-preview"
OUT.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8766),functools.partial(Quiet,directory=str(preview/'app/src/main/assets')));threading.Thread(target=server.serve_forever,daemon=True).start()
results=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8766');page.wait_for_timeout(300)
 def check(label,test):
  assert test,label
  results.append(label)
 page.evaluate("localStorage.clear();setSetting('speed','fast');setSetting('sound',false);toggleFav('coin');toggleFav('wheel');toggleFav('dice');toggleFav('draw');go('home')")
 page.wait_for_timeout(100);page.screenshot(path=str(OUT/'home.png'),full_page=True)
 check('Four favorites rendered',page.locator('#favArea button').count()==4)
 page.reload();page.wait_for_timeout(100);check('Favorites survive reload',page.locator('#favArea button').count()==4)
 page.evaluate("go('catalog')");check('Six tool cards',page.locator('.hb-tool-card').count()==6)
 page.evaluate("setSetting('dark',true)");page.wait_for_timeout(100);page.screenshot(path=str(OUT/'tools-dark.png'),full_page=True)
 check('Dark mode applied',page.locator('body').evaluate("el=>el.classList.contains('dark')"))
 for w in [320,360,390,430]:
  page.set_viewport_size({'width':w,'height':844})
  for route in ['home','catalog','games','settings','manage']:
   page.evaluate(f"go('{route}')");page.wait_for_timeout(35)
   check(f'{w}px {route}: no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
 page.set_viewport_size({'width':390,'height':844});page.evaluate("setSetting('dark',false)")
 for tool,action,result in [('coin','flipCoin','coinResult'),('number','genNumber','numResult'),('wheel','spinWheel','wheelResult'),('dice','rollDice','diceResult'),('rps','playRps','rpsResult'),('draw','drawOne','drawResult')]:
  page.evaluate(f"openTool('{tool}');{action}()")
  page.wait_for_function('!busy',timeout=10000)
  check(tool+' completes with result',bool(page.locator('#'+result).inner_text()))
  check(tool+' no overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
 page.screenshot(path=str(OUT/'tool.png'),full_page=True)
 page.evaluate("go('settings');rtShowLogin()")
 check('Login visible',page.locator('#rtIdentifier').is_visible());page.screenshot(path=str(OUT/'login.png'),full_page=True)
 for route in ['choose','register','otpLogin','verify','forgot','security']:
  page.evaluate(f"rtRender('{route}')");check('Account screen '+route,page.locator('.rt-head h1').is_visible())
 page.evaluate("rtClose();window.rtLoggedIn=true;rtUser={uid:'ui-test-only',email:'preview@example.com'};rtSessionKnown=true;rtStatus();rtShowProfile()")
 check('Nine original animal avatars',page.locator('.rt-avatar-choice').count()==9)
 page.screenshot(path=str(OUT/'profile.png'),full_page=True)
 page.locator('#rtProfileName').fill('开心测试');page.evaluate("rtProfileChoose('fox');rtProfileCommit();rtShowProfile()")
 check('Profile edits persist per UID',page.locator('#rtProfileName').input_value()=='开心测试')
 check('No uncaught JS errors',not errors)
 b.close()
server.shutdown();shutil.rmtree(preview);print(json.dumps({'passed':len(results),'checks':results,'errors':errors},ensure_ascii=False,indent=2))
