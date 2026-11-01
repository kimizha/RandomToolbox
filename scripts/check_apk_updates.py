"""Compile and run the production APK policy/session against offline JVM fixtures.
Uses the Android platform org.json API; the standalone test implementation is test-only.
"""
from pathlib import Path
import hashlib,os,shutil,subprocess,tempfile,urllib.request
ROOT=Path(__file__).resolve().parents[1]
URL='https://repo.maven.apache.org/maven2/org/json/json/20240303/json-20240303.jar'
SHA='3cf6cd6892e32e2b4c1c39e0f52f5248a2f5b37646fdfbb79a66b46b618414ed'
cache=Path(os.environ.get('RT_TEST_CACHE',tempfile.gettempdir()))/'happybox-test-deps';cache.mkdir(exist_ok=True)
jar=cache/'json-20240303.jar'
if not jar.exists() or hashlib.sha256(jar.read_bytes()).hexdigest()!=SHA:
 with urllib.request.urlopen(URL,timeout=30) as response:raw=response.read(1024*1024)
 if hashlib.sha256(raw).hexdigest()!=SHA:raise SystemExit('Test dependency digest mismatch')
 jar.write_bytes(raw)
with tempfile.TemporaryDirectory(prefix='happybox-update-tests-') as tmp:
 sources=[ROOT/'app/src/main/java/com/randomtoolbox/app/ApkUpdatePolicy.java',ROOT/'tests/java/com/randomtoolbox/app/ApkUpdatePolicyTest.java']
 compiler=[shutil.which('javac')] if shutil.which('javac') else ['java','-m','jdk.compiler/com.sun.tools.javac.Main']
 subprocess.run(compiler+['-encoding','UTF-8','-cp',str(jar),'-d',tmp]+list(map(str,sources)),check=True)
 subprocess.run(['java','-cp',str(jar)+os.pathsep+tmp,'com.randomtoolbox.app.ApkUpdatePolicyTest',str(ROOT/'updates/version.json')],check=True)
