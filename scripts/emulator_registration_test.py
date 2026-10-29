import json, time, urllib.request
from pathlib import Path
import websocket

def targets():
    return json.load(urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=5))
def eval_js(ws, expr, request_id):
    ws.send(json.dumps({'id':request_id,'method':'Runtime.evaluate','params':{'expression':expr,'returnByValue':True}}))
    while True:
        response=json.loads(ws.recv())
        if response.get('id')==request_id:
            return response
try:
    page=next(x for x in targets() if x.get('type')=='page')
    ws=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=10,suppress_origin=True)
    eval_js(ws,"go('settings')",1)
    time.sleep(2)
    eval_js(ws,"document.getElementById('rtLoginButton')?.click()",2)
    time.sleep(2)
    eval_js(ws,"rtRender('choose')",3)
    time.sleep(2)
    eval_js(ws,"rtMode='email';rtRender('register')",4)
    time.sleep(2)
    result=eval_js(ws,"({page:rtPage,visible:!document.getElementById('rtAuthRoot')?.hidden,contact:!!document.getElementById('rtContact')})",5)
    Path('emulator-results/registration-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    # Check that all registration inputs exist and validate locally.
    checks = eval_js(ws, """(() => {
      const ids = ['rtContact', 'rtNewPassword', 'rtConfirmPassword'];
      const fields = ids.map(id => !!document.getElementById(id));
      const button = !!document.querySelector('[onclick="rtRegister()"]');
      return {fields, button, page: rtPage};
    })()""", 6)
    state = checks.get('result', {}).get('result', {}).get('value', {})
    Path('emulator-results/registration-form-check.json').write_text(
        json.dumps(state, ensure_ascii=False, indent=2))
    if state.get('page') != 'register' or not all(state.get('fields', [])) or not state.get('button'):
        raise AssertionError('Registration form is incomplete: ' + str(state))
    ws.close()
except Exception as error:
    Path('emulator-results/registration-automation-error.txt').write_text(str(error))
    raise
