"""Custom Android select replacement, remaining percentages and soup taxonomy UI."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
from ui_test_helpers import choose
import threading,functools,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/ui-preview'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8790),functools.partial(Quiet,directory=str(ROOT/'app/src/main/assets')));threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda err:errors.append(str(err)));page.goto('http://127.0.0.1:8790/');page.evaluate("setSetting('sound',false)")
 def check(label,value):
  assert value,label
  checks.append(label)
 def open_game(kind):
  page.evaluate("document.querySelector('#rtModalShade')?.remove();HBChoice.close();if(HBParty.active)HBParty.active.stage='end';party.stage='end';go('games')");page.evaluate("openGame('"+kind+"')");page.wait_for_timeout(80)
 def snap(name):page.wait_for_timeout(260);page.evaluate("document.querySelector('#toast').classList.remove('show')");page.wait_for_timeout(260);page.screenshot(path=str(OUT/name),full_page=False)
 open_game('spy');check('Native selector hidden and custom button visible',not page.locator('#spyCount').is_visible() and page.locator('#spyCount + .hb-choice-trigger').is_visible())
 page.locator('#spyCount + .hb-choice-trigger').click();check('Spy uses themed sheet with three choices',page.locator('#hbChoiceShade [role=option]').count()==3 and page.locator('[aria-selected=true]').inner_text()=='1人')
 snap('spy-choice-sheet.png');page.evaluate('appBack()');check('Android Back closes only selector',page.locator('#hbChoiceShade').count()==0 and page.locator('#partyCount').is_visible() and page.locator('#spyCount').input_value()=='1' and not page.locator('body').evaluate("el=>el.classList.contains('hb-choice-open')"))
 choose(page,'#spyCount','2');check('Choice applies native source value and visible label',page.locator('#spyCount').input_value()=='2' and page.locator('#spyCount + .hb-choice-trigger strong').inner_text()=='2人')
 page.evaluate('gameSetup()');check('Selected count is consumed by existing spy rules',page.evaluate('party.spy.length===2'))
 page.evaluate("party.stage='end';go('settings')");choose(page,'#speedSelect','slow');check('Settings choice dispatches original save handler',page.evaluate("settings.speed==='slow'&&JSON.parse(localStorage.getItem('rt_settings')).speed==='slow'"))
 open_game('score');page.evaluate('HBScore.create()');page.locator('#hsTitle').fill('夜场测试');page.wait_for_timeout(70)
 page.locator('#hsUnit + .hb-choice-trigger').click();snap('ledger-unit-sheet.png');page.evaluate('appBack()');check('Back preserves parent form and text',page.locator('#rtModalShade').count()==1 and page.locator('#hsTitle').input_value()=='夜场测试')
 choose(page,'#hsUnit','分');page.locator('#rtAccept').click();check('Nested choice saves correct points unit',page.evaluate("HBParty.data.boards[0].unit==='分'&&HBParty.data.boards[0].title==='夜场测试'"))
 page.evaluate('HBScore.transfer(HBParty.data.boards[0].players[0].id)');page.wait_for_timeout(60);choose(page,'#hsTo',page.evaluate('HBParty.data.boards[0].players[0].id'));page.locator('#rtAccept').click();check('Original transfer validation still rejects self transfer',page.locator('#rtModalShade').count()==1 and page.evaluate('HBParty.data.boards[0].entries.length===0'));page.locator('#rtCancel').click()
 open_game('truth');page.evaluate('gameSetup()');check('Both remaining decks start at 100 percent',page.locator('.hb-truth-percent strong').all_text_contents()==['100%','100%'])
 page.evaluate("gamePrompt('truth')");check('Truth percentage uses its own expanded bank',page.locator('.hb-truth-percent strong').first.inner_text()=='99.5%')
 page.evaluate("gamePrompt('dare')");check('Dare percentage uses its own expanded bank',page.locator('.hb-truth-percent strong').nth(1).inner_text()=='99.4%')
 check('No raw remaining counts shown',page.locator('.hb-truth-count').count()==0 and '条' not in ''.join(page.locator('.hb-truth-percent').all_text_contents()))
 snap('truth-percentages.png');page.evaluate("party.truthUsed=[...HBParty.truthBank('truth',truthQuestions)];renderGame()");check('Exhausted deck displays 0 percent',page.locator('.hb-truth-percent strong').first.inner_text()=='0%')
 page.evaluate('clearTruthQuestions();renderGame()');check('Reset restores 100 percent',page.locator('.hb-truth-percent strong').all_text_contents()==['100%','100%'])
 open_game('soup');page.locator('.hb-soup-type-guide summary').click();check('Setup explains all six soup terms',page.locator('.hb-soup-type-guide section').count()==6);snap('soup-type-guide.png')
 choose(page,'#soupDifficulty','hard');page.evaluate('startSoupGame()');check('Custom difficulty selection filters actual cases',page.evaluate("soupCurrent().difficulty==='hard'"))
 check('Title has two clickable colored type badges',page.locator('.hb-soup-type-tags button').count()==2)
 solution=page.evaluate('soupCurrent().solution');page.locator('.hb-soup-type-tags button').first.click();check('Type explanation shows only this soup classifications',page.locator('.hb-soup-type-dialog section').count()==2 and solution not in page.locator('.hb-soup-type-dialog').inner_text())
 page.evaluate('appBack()');check('Type explanation Back preserves current case',page.locator('#rtModalShade').count()==0 and page.evaluate("party.stage==='play'"))
 for t in ['white','red','black','spicy','realistic','supernatural']:
  page.evaluate("t=>{const item=soupCases().find(s=>s.types.includes(t));party.soupId=item.id;party.soupHints=0;party.soupAnswerVisible=false;renderGame()}",t)
  check('Classified case '+t+' has correct badge',page.locator('.hb-soup-type-tags .type-'+t).count()==1)
  page.locator('.hb-soup-type-tags button').first.click();labels=page.locator('.hb-soup-type-dialog .hb-soup-type').all_text_contents();expected=page.evaluate('soupCurrent().types.map(t=>SOUP_TYPES[t].label)');check('Explanation limited to '+t+' case tags',labels==expected);page.locator('#soupTypesClose').click()
 page.evaluate("party.soupId=soupCases().find(s=>s.types.includes('red')&&s.types.includes('supernatural')).id;renderGame()");snap('soup-colored-tags.png')
 for width,height in [(320,568),(390,844),(844,390)]:
  for dark in [False,True]:
   page.set_viewport_size({'width':width,'height':height});page.evaluate(f"setSetting('dark',{str(dark).lower()})");open_game('spy');page.locator('#spyCount + .hb-choice-trigger').click();page.wait_for_timeout(260)
   check(f'Choice sheet fits {width}x{height} dark={dark}',page.locator('.hb-choice-sheet').evaluate('el=>el.getBoundingClientRect().top>=0&&el.getBoundingClientRect().bottom<=innerHeight&&el.scrollWidth<=el.clientWidth'))
   page.keyboard.press('Tab');check(f'Keyboard focus stays in sheet {width} dark={dark}',page.evaluate("!!document.activeElement.closest('#hbChoiceShade')"));page.keyboard.press('Escape');check(f'Escape cancels choice {width} dark={dark}',page.locator('#hbChoiceShade').count()==0)
 check('No uncaught JS errors',not errors)
 print(json.dumps({'passed':len(checks),'checks':checks,'errors':errors},ensure_ascii=False,indent=2));browser.close()
server.shutdown()
