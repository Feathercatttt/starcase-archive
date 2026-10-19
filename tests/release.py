"""Check local release bytes and actual Windows verifier; does not publish or install."""
from pathlib import Path
import base64, hashlib, json, re, subprocess, zipfile
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

R = Path(__file__).resolve().parent.parent
version = re.search(r'Current="([\d.]+)"', (R / 'native/windows/UpdateProtocol.cs').read_text(encoding='utf8')).group(1)
release = R / 'outputs' / ('release-v' + version)
checks = []
envelope = json.loads((release / 'stable.candidate.json').read_text(encoding='utf8'))
raw = base64.b64decode(envelope['payload'])
payload = json.loads(raw)
public = json.loads((R / 'outputs/更新公钥.json').read_text(encoding='utf8'))
key = serialization.load_der_public_key(base64.b64decode(public['spki']))
key.verify(base64.b64decode(envelope['signature']), raw, padding.PKCS1v15(), hashes.SHA256())
assert payload['app'] == 'starcase-archive' and payload['version'] == version
for platform, name in [('windows', 'Starcase-Windows-Update.zip'), ('android', 'Starcase-Android.apk')]:
    data = (release / name).read_bytes()
    assert len(data) == payload[platform]['size']
    assert hashlib.sha256(data).hexdigest() == payload[platform]['sha256']
    assert payload[platform]['url'].endswith('/releases/download/v' + version + '/' + name)
checks.append('Signed candidate validates with shipped public key; both attachment sizes, hashes, versions and fixed names match')

stage = R / '.build/release-verifier'
stage.mkdir(exist_ok=True)
source = stage / 'Check.cs'
source.write_text('''using System;
internal static class Check {static int Main(string[] a){try{var p=UpdateProtocol.Verify(System.IO.File.ReadAllText(a[0]),"windows");UpdateProtocol.VerifyFile(a[1],UpdateProtocol.Object(p,"windows"));Console.WriteLine(UpdateProtocol.Text(p,"version"));return 0;}catch{Console.WriteLine("Rejected");return 2;}}}
''', encoding='utf8')
exe = stage / 'Check.exe'
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe', '/nologo', '/target:exe', '/out:' + str(exe), '/reference:System.dll', '/reference:System.Core.dll', '/reference:System.Web.Extensions.dll', str(source), str(R / 'native/windows/UpdateProtocol.cs'), str(R / 'native/windows/UpdateKey.cs')], check=True, capture_output=True)
valid = subprocess.run([str(exe), str(release / 'stable.candidate.json'), str(release / 'Starcase-Windows-Update.zip')], capture_output=True, text=True)
assert valid.returncode == 0 and version in valid.stdout
tampered = dict(envelope)
tampered['payload'] = base64.b64encode(raw.replace(b'"schema":1', b'"schema":2')).decode()
(stage / 'tampered.json').write_text(json.dumps(tampered), encoding='utf8')
assert subprocess.run([str(exe), str(stage / 'tampered.json'), str(release / 'Starcase-Windows-Update.zip')], capture_output=True).returncode == 2
checks.append('Actual C# update protocol accepts candidate and artifact, rejects modified signed payload')

with zipfile.ZipFile(release / 'Starcase-Windows-Update.zip') as z:
    names = set(z.namelist())
    assert {'Starcase-Update/星匣.exe', 'Starcase-Update/星匣.html', 'Starcase-Update/service/server.py', 'Starcase-Update/标准模板.json'} <= names
    assert all(n.startswith('Starcase-Update/') and '..' not in n.split('/') for n in names)
    assert not any(n.endswith(('connection.json', 'library.json', 'MicrosoftEdgeWebView2RuntimeInstallerX64.exe')) for n in names)
with zipfile.ZipFile(R / 'outputs' / ('Starcase-Source-v' + version + '.zip')) as z:
    for name in z.namelist():
        assert not {'private', '.build', '.git', 'outputs', '__pycache__'} & set(name.split('/'))
        assert not name.endswith(('.p12', '.pem', '.keystore', '.apk'))
    assert 'starcase-archive/maintenance/starcase-maintenance/SKILL.md' in z.namelist()
checks.append('Update ZIP has required root and no data/runtime installer; source ZIP contains maintenance skill and excludes private keys, samples and builds')

tools = Path('C:/Users/PC/Documents/Codex/2026-10-13/new-chat/work/android-sdk/build-tools/36.0.0')
badging = subprocess.run([str(tools / 'aapt2.exe'), 'dump', 'badging', str(release / 'Starcase-Android.apk')], check=True, capture_output=True).stdout.decode('utf8')
assert "name='com.starcase.archive'" in badging and ("versionName='" + version + "'") in badging
assert 'application-debuggable' not in badging
checks.append('Release attachment is independent production Android package, not debuggable QA build')
(R / 'tests/release-report.json').write_text(json.dumps({'success': True, 'checks': checks, 'limits': ['Local artifacts only; no public release or online installer test']}, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({'success': True, 'checks': checks}, ensure_ascii=False, indent=2))
