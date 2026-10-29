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

    # Use a stub auth client: no real emails, OTPs, or account creation.
    test_js = r"""(async () => {
      const savedAuth = rtAuth;
      const savedBusy = rtBusy;
      let calls = [];
      let cases = [];
      const assertCase = (name, ok, detail) => {
        cases.push({name, passed: !!ok, detail});
        if (!ok) throw Error(name + ': ' + JSON.stringify(detail));
      };
      try {
        rtAuth = {
          signUp: async args => {
            calls.push({email:args.email, passwordLength:args.password?.length});
            return {data:{verifyOtp: async () => ({data:{}})}};
          },
          getSession: async () => ({data:{session:null}})
        };
        rtBusy = false;
        const fill = (email, pass, confirm) => {
          rtMode='email';
          rtRender('register');
          document.getElementById('rtContact').value=email;
          document.getElementById('rtNewPassword').value=pass;
          document.getElementById('rtConfirmPassword').value=confirm;
        };
        for (const [name,email,pass,confirm,expected] of [
          ['invalid email','not-an-email','abcdefgh','abcdefgh','请输入正确的邮箱'],
          ['short password','test@example.invalid','short','short','密码至少需要 8 位'],
          ['password mismatch','test@example.invalid','abcdefgh','different','两次输入的密码不一致']
        ]) {
          fill(email,pass,confirm);
          await rtRegister();
          const message=document.getElementById('rtMsg').textContent;
          assertCase(name, message.includes(expected) && calls.length===0, {message, calls:calls.length});
        }
        fill('test@example.invalid','abcdefgh','abcdefgh');
        await rtRegister();
        assertCase('mock signup and OTP page',
          calls.length===1 && calls[0].email==='test@example.invalid' &&
          rtPage==='verify' && !!document.getElementById('rtOtp'),
          {calls, page:rtPage});
        rtRender('login');
        assertCase('login inputs',
          !!document.getElementById('rtIdentifier') && !!document.getElementById('rtPassword'),
          {page:rtPage});
        return {passed:true,cases,mode:'mocked CloudBase, no real signup'};
      } finally {
        rtAuth=savedAuth;
        rtBusy=savedBusy;
      }
    })()"""
    response = eval_js(ws, test_js, 7)
    Path('emulator-results/registration-validation-raw.json').write_text(
        json.dumps(response, ensure_ascii=False, indent=2))
    if response.get('result', {}).get('exceptionDetails'):
        raise AssertionError('Registration validation JS failed: ' +
                             json.dumps(response['result']['exceptionDetails'], ensure_ascii=False))
    validation = response.get('result', {}).get('result', {}).get('value')
    Path('emulator-results/registration-validation.json').write_text(
        json.dumps(validation, ensure_ascii=False, indent=2))
    if not validation or not validation.get('passed'):
        raise AssertionError('Registration validation tests did not pass')
    ws.close()
except Exception as error:
    Path('emulator-results/registration-automation-error.txt').write_text(str(error))
    raise
