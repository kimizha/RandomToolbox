"""Browser integration checks for offline party games; no real users or cloud data."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
import threading,functools,json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/ui-preview';OUT.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',8788),functools.partial(Quiet,directory=str(ROOT/'app/src/main/assets')))
threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':390,'height':844},has_touch=True)
 context.route('**/*',lambda route:route.continue_() if route.request.url.startswith('http://127.0.0.1:8788/') else route.abort())
 page=context.new_page();errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
 page.goto('http://127.0.0.1:8788/');page.evaluate("localStorage.clear();setSetting('sound',false);go('games')")
 def check(label,value):
  assert value,label
  checks.append(label)
 def act(js):
  page.wait_for_timeout(290);return page.evaluate(js)
 def accept():page.locator('#rtAccept').click()
 def clean_open(game):
  page.evaluate("document.querySelector('#rtModalShade')?.remove();if(HBParty.active)HBParty.active.stage='end';party.stage='end';go('games')")
  act("HBParty.open('"+game+"')")
 def store():return page.evaluate('HBParty.data')
 check('Four existing games retained',all(page.locator('#games').get_by_text(t,exact=True).count()==1 for t in ['狼人杀','真心话大冒险','谁是卧底','海龟汤']))
 check('Four new games listed once',page.locator('.hp-menu-row').count()==4)
 for width,height in [(320,568),(360,640),(390,844)]:
  page.set_viewport_size({'width':width,'height':height})
  for dark in [False,True]:
   page.evaluate(f"setSetting('dark',{str(dark).lower()})")
   for game in ['bomb','charades','taboo','score']:
    clean_open(game)
    check(f'{game} setup {width}px dark={dark} no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.set_viewport_size({'width':390,'height':844});page.evaluate("setSetting('dark',false)")
 clean_open('bomb');page.locator('#hpMin').fill('');act('HBParty.bombStart()');check('Empty bomb boundary rejected',page.locator('#hpMin').count()==1)
 page.locator('#hpMin').fill('1');page.locator('#hpMax').fill('1');act('HBParty.bombStart()');check('One-number range rejected',page.locator('#hpMin').count()==1)
 page.locator('#hpMax').fill('100');act('HBParty.bombStart()');page.evaluate('HBParty.active.bomb.secret=57')
 check('Secret never rendered before explosion','57' not in page.locator('#gameBody').inner_text())
 page.locator('#hpGuess').fill('30');act('HBParty.bombGuess()');check('Bomb low bound advances to 31',page.evaluate('HBParty.active.bomb.low===31'))
 page.locator('#hpGuess').fill('80');act('HBParty.bombGuess()');check('Bomb high bound drops to 79',page.evaluate('HBParty.active.bomb.high===79'))
 page.locator('#hpGuess').fill('20');act('HBParty.bombGuess()');check('Out of range guess cannot enter history',page.evaluate('HBParty.active.bomb.history.length===2'))
 page.evaluate('appBack()');check('Android Back asks before leaving bomb',page.locator('#rtModalShade').count()==1);page.locator('#rtCancel').click()
 page.locator('#hpGuess').fill('57');act('HBParty.bombGuess()');check('Explosion ends bomb and exposes challenge buttons',page.evaluate("HBParty.active.stage==='end'") and page.locator('.hp-explode').count()==1)
 act("HBParty.challenge('dare')");check('Bomb links directly into existing dare draw',page.evaluate("party.type==='truth'&&party.stage==='play'&&party.mode==='dare'&&!!party.prompt"))
 check('Challenge shows bomb source','数字炸弹' in page.locator('.hp-source').inner_text())
 page.evaluate('appBack()');accept();check('Back restores completed bomb with guesses',page.evaluate("HBParty.active.type==='bomb'&&HBParty.active.bomb.history.length===3"))
 act("HBParty.challenge('truth')");check('Linked bank remembers prior dare',page.evaluate('party.dareUsed.length===1&&party.truthUsed.length===1'))
 act('HBParty.returnChallenge()');page.screenshot(path=str(OUT/'party-bomb.png'),full_page=True)
 clean_open('charades');act('HBParty.editWords()');page.locator('#hpCustomWords').fill('大猩猩\n刷牙\n大猩猩\n摄影师');accept()
 check('Custom charades words normalized and persisted',store()['custom']['charades']==['大猩猩','刷牙','摄影师'])
 act('HBParty.charadesReady()');check('Ready transition hides the first answer',page.locator('.hp-word').count()==0 and page.locator('.hp-private').count()==1)
 act('HBParty.charadesBegin()');check('Charades word and timer visible',page.locator('.hp-word').count()==1 and page.locator('#hpClock').count()==1)
 for width,height in [(320,568),(360,640)]:
  page.set_viewport_size({'width':width,'height':height});check(f'Charades play {width}px no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.set_viewport_size({'width':390,'height':844})
 before_count=page.evaluate('HBParty.active.i');act('HBParty.charadesAnswer(true);HBParty.charadesAnswer(true)');check('Repeated charades tap scores only once',page.evaluate('HBParty.active.i')==before_count+1)
 # Restart the setup to keep the following three-word round independent.
 act('HBParty.charadesEnd()');accept();act('HBParty.charadesReset()');act('HBParty.charadesReady()');act('HBParty.charadesBegin()')
 page.evaluate('HBParty.commit(d=>d.results=[])')
 first=page.locator('.hp-word').inner_text();act('HBParty.charadesAnswer(true)');check('Correct answer advances without repeating',first!=page.locator('.hp-word').inner_text() and page.evaluate('HBParty.active.right.length===1'))
 act('HBParty.pause()');left=page.evaluate('HBParty.active.left');page.wait_for_timeout(350);check('Paused clock frozen and word hidden',page.evaluate('HBParty.active.left')==left and page.locator('.hp-word').count()==0)
 act('HBParty.charadesBegin()');act('HBParty.background()');check('Native background hook pauses and hides answer',page.evaluate("HBParty.active.stage==='paused'") and page.locator('.hp-word').count()==0)
 act('HBParty.charadesBegin()');act('HBParty.charadesAnswer(false)');act('HBParty.charadesAnswer(true)')
 check('Deck exhaustion ends once and saves results',page.evaluate("HBParty.active.stage==='end'") and len(store()['results'])==1)
 check('Result counts correct and skip independently',store()['results'][0]['right'].__len__()==2 and len(store()['results'][0]['skipped'])==1)
 page.screenshot(path=str(OUT/'party-charades-result.png'),full_page=True)
 act('HBParty.charadesReset()');page.evaluate('HBParty.active.seconds=1');act('HBParty.charadesReady()');act('HBParty.charadesBegin()');page.wait_for_timeout(1250)
 check('Deadline ends round exactly once',page.evaluate("HBParty.active.stage==='end'") and len(store()['results'])==2)
 act('HBParty.charadesReset()');act('HBParty.charadesReady()');act('HBParty.charadesBegin()');page.evaluate("go('games')");check('Navigation pauses before exit confirmation',page.evaluate("HBParty.active.stage==='paused'") and page.locator('#rtModalShade').count()==1);accept();page.wait_for_timeout(1100);check('Exited timer cannot save a phantom result',len(store()['results'])==2)
 clean_open('taboo');page.evaluate("window.orientationCalls=[];window.RandomToolboxNative={setPartyOrientation:m=>orientationCalls.push(m),vibrate:()=>{}}")
 page.locator('#hpTabooN').fill('4');page.locator('#hpTabooN').dispatch_event('change');act('HBParty.tabooStart()');task=page.evaluate('HBParty.active.tasks[0]')
 check('Tasks assigned uniquely and hidden in DOM',page.evaluate('new Set(HBParty.active.tasks).size===4') and task not in page.locator('#gameBody').inner_text())
 act('HBParty.tabooShow()');check('Reveal requires other-player confirmation',page.locator('#rtModalShade').count()==1 and task not in page.locator('#gameBody').inner_text());accept()
 check('Task reveal shows assigned content',page.locator('.hp-task-screen strong').inner_text()==task)
 page.set_viewport_size({'width':320,'height':568});check('Portrait task fits smallest screen',page.locator('.hp-task-screen').evaluate('el=>el.scrollWidth<=el.clientWidth&&el.scrollHeight<=el.clientHeight'))
 page.set_viewport_size({'width':390,'height':844})
 act('HBParty.tabooDirection()');page.set_viewport_size({'width':844,'height':390})
 check('Landscape requested through native bridge',page.evaluate("orientationCalls.includes('landscape')"))
 check('Landscape content stays within viewport',page.locator('.hp-task-screen').evaluate('el=>el.scrollWidth<=el.clientWidth&&el.scrollHeight<=el.clientHeight'))
 page.screenshot(path=str(OUT/'party-taboo-landscape.png'),full_page=True)
 act('HBParty.background()');check('Background hides taboo task and releases orientation',page.locator('.hp-task-screen').count()==0 and page.evaluate("orientationCalls.at(-1)==='auto'"))
 page.set_viewport_size({'width':390,'height':844});act('HBParty.tabooShow()');accept();act('HBParty.tabooSuccess()');accept();check('Success hides task and offers challenge',page.evaluate("HBParty.active.stage==='success'&&!HBParty.active.visible"))
 act("HBParty.challenge('truth')");check('Taboo challenge retains target player source','1 号玩家' in page.locator('.hp-source').inner_text());act('HBParty.returnChallenge()')
 act('HBParty.tabooNext()');check('Phone handoff advances and hides next task',page.evaluate('HBParty.active.index===1&&!HBParty.active.visible'))
 for _ in range(3):act('HBParty.tabooSkip()');accept()
 check('New round assigns fresh nonrepeating tasks',page.evaluate('HBParty.active.round===2&&HBParty.active.used.length===8&&new Set(HBParty.active.used).size===8'))
 clean_open('score');act('HBScore.create()');page.locator('#hsPlayers').fill('小开心\n小幸运\n小月亮');accept();check('Score board creates players',len(store()['boards'][0]['players'])==3)
 for width,height in [(320,568),(360,640)]:
  page.set_viewport_size({'width':width,'height':height});check(f'Score board {width}px no overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
 page.set_viewport_size({'width':390,'height':844})
 boardid=store()['boards'][0]['id'];a,b,c=[p['id'] for p in store()['boards'][0]['players']]
 def add(player,value,to=None):
  act('HBScore.amountDialog('+json.dumps(player)+',1)');page.locator('#hsAmount').fill(str(value))
  if to:page.locator('#hsTo').select_option(to)
  accept()
 add(a,100);add(a,-30)
 check('Independent score totals +70',page.evaluate('HBPartyCore.totals(HBParty.data.boards[0])['+json.dumps(a)+']')==7000)
 page.reload();page.wait_for_timeout(100);clean_open('score');act('HBScore.select('+json.dumps(boardid)+')');check('Reload retains board and both records',len(store()['boards'][0]['entries'])==2)
 act('HBScore.ledger()');entry=store()['boards'][0]['entries'][1]['id'];act('HBScore.editEntry('+json.dumps(entry)+')');page.locator('#hsAmount').fill('-20');accept();check('Editing recalculates saved balance',page.evaluate('HBPartyCore.totals(HBParty.data.boards[0])['+json.dumps(a)+']')==8000)
 act('HBScore.deleteEntry('+json.dumps(entry)+')');accept();check('Delete entry recalculates balance',len(store()['boards'][0]['entries'])==1)
 act('HBScore.undo()');accept();check('Undo restores deleted record',len(store()['boards'][0]['entries'])==2)
 page.evaluate('appBack()');check('Ledger Back returns to same score board',page.evaluate("HBParty.active.page==='board'"))
 act('HBScore.clear()');accept();check('Clear requires second confirmation',page.locator('#rtModalShade h3').inner_text()=='再次确认清空');page.locator('#rtCancel').click();check('Cancel clear retains records',len(store()['boards'][0]['entries'])==2)
 act('HBScore.clear()');accept();accept();check('Confirmed clear empties only this board',len(store()['boards'][0]['entries'])==0)
 act('HBScore.undo()');accept();check('Clear can be undone once',len(store()['boards'][0]['entries'])==2)
 act('HBScore.removePlayer('+json.dumps(c)+')');accept();check('Removing player preserves historical identity',store()['boards'][0]['players'][2]['archived'])
 act('HBScore.addPlayer()');page.locator('#hsName').fill('新朋友');accept();check('Player can be added mid-session',len(store()['boards'][0]['players'])==4)
 act('HBScore.editPlayer('+json.dumps(a)+')');page.locator('#hsName').fill('开心队长');accept();check('Player rename persisted',store()['boards'][0]['players'][0]['name']=='开心队长')
 act('HBScore.close()');accept();check('Finish archives session',store()['boards'][0]['closed'])
 act('HBScore.create()');page.locator('#hsTitle').fill('平衡记分测试');page.locator('#hsMode').select_option('transfer');accept();newid=store()['boards'][0]['id'];a,b=[p['id'] for p in store()['boards'][0]['players']]
 act('HBScore.amountDialog('+json.dumps(a)+',-1)');check('Transfer minus button starts positive amount',page.locator('#hsAmount').input_value()=='10');page.locator('#hsAmount').fill('100');accept()
 check('Transfer stores a single balanced transaction',len(store()['boards'][0]['entries'])==1 and sum(l['amount'] for l in store()['boards'][0]['entries'][0]['legs'])==0)
 act('HBScore.ledger()');entry=store()['boards'][0]['entries'][0]['id'];act('HBScore.editEntry('+json.dumps(entry)+')');page.locator('#hsAmount').fill('0.29');accept();check('Transfer edits both legs atomically',sorted(l['amount'] for l in store()['boards'][0]['entries'][0]['legs'])==[-29,29])
 act('HBScore.showBoard()');page.screenshot(path=str(OUT/'party-score.png'),full_page=True)
 # A same-player transfer must not become an unbalanced entry.
 before=store();act('HBScore.amountDialog('+json.dumps(a)+',1)');page.locator('#hsTo').select_option(a);accept();check('UI rejects transfer to same player',store()==before and page.locator('#rtModalShade').count()==1);page.locator('#rtCancel').click()
 before=store();page.evaluate("()=>{window.originalSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw Error('quota test')}}")
 add(a,5,b);check('Storage failure never applies unsaved balances',store()==before);page.evaluate('()=>{Storage.prototype.setItem=originalSet}');page.locator('#rtCancel').click()
 act('HBScore.ledger()');act('HBScore.deleteEntry('+json.dumps(entry)+')');accept();check('Transfer deletion removes both sides',store()['boards'][0]['entries']==[])
 page.reload();page.wait_for_timeout(100);clean_open('score');check('Two sessions persist independently',len(store()['boards'])==2 and store()['boards'][1]['closed'])
 act('HBScore.select('+json.dumps(newid)+')');page.evaluate('appBack()');check('Score board Back returns to saved session list',page.evaluate("HBParty.active.page==='list'"))
 # Local custom truth deck is appended to the existing bank, not a second truth implementation.
 page.evaluate("party.stage='end';go('games');openGame('truth');gameSetup()");act('HBParty.editTruth()');page.locator('#hpCustomTruth').fill('我的自定义真心话');page.locator('#hpCustomDare').fill('做一个自定义动作');accept()
 check('Custom truth prompt stored locally and included',store()['custom']['truth']==['我的自定义真心话'] and page.evaluate("truthRemaining('truth').includes('我的自定义真心话')"))
 # Fully deleting scores needs two confirmations and leaves other local games intact.
 page.evaluate("party.stage='end';go('games')");clean_open('score');act('HBScore.clearAll()');accept();check('Delete all scores requests second confirmation',page.locator('#rtModalShade h3').inner_text()=='再次确认永久删除');accept()
 check('Manual score clear preserves custom truth and charades',store()['boards']==[] and len(store()['results'])==2 and store()['custom']['truth']==['我的自定义真心话'])
 # An unreadable ledger is not silently overwritten by a new board.
 page.evaluate("localStorage.setItem('hb_party_local_v1','{broken-json')");page.reload();page.wait_for_timeout(100);clean_open('score');check('Corrupt local store shows a recoverable error',page.locator('.hp-error').count()==1)
 act('HBScore.create()');accept();check('Corrupt raw data protected from overwrite',page.evaluate("localStorage.getItem('hb_party_local_v1')==='{broken-json'"));page.locator('#rtCancel').click()
 check('No uncaught browser errors',not errors)
 print(json.dumps({'passed':len(checks),'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
 browser.close()
server.shutdown()
