"""Build local delivery artifacts and, optionally, a signed update candidate. Never uploads."""
from pathlib import Path
import argparse, base64, hashlib, json, re, shutil, zipfile, ctypes
from ctypes import wintypes

R = Path(__file__).resolve().parent.parent
O = R / 'outputs'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sign', action='store_true', help='Sign a local manifest candidate using the existing private key')
parser.add_argument('--windows-dir',type=Path,help='Use a separate Windows build folder when the old EXE is running')
parser.add_argument('--full', action='store_true', help='Also package the Microsoft offline WebView2 installer')
parser.add_argument('--notes-file', type=Path, help='UTF-8 release notes to embed in the signed manifest')
args = parser.parse_args()
protocol = (R / 'native/windows/UpdateProtocol.cs').read_text(encoding='utf8')
version = re.search(r'Current="([\d.]+)"', protocol).group(1)
repo = re.search(r'Repo="(https://github.com/[^\"]+/)"', protocol).group(1)
android = (R / 'native/android/AndroidManifest.xml').read_text(encoding='utf8')
code = int(re.search(r'versionCode="(\d+)"', android).group(1))
assert 'versionName="' + version + '"' in android, 'Windows / Android version mismatch'
assert 'VERSION=\'' + version + '\'' in (R / 'src/model.js').read_text(encoding='utf8'), 'Web version mismatch'
assert 'CURRENT="' + version + '"' in (R / 'native/android/src/com/starcase/archive/UpdateProtocol.java').read_text(encoding='utf8'), 'Android update version mismatch'
win = (args.windows_dir or O / '星匣-Windows').resolve()
version_api=ctypes.WinDLL('version',use_last_error=True)
version_api.GetFileVersionInfoSizeW.argtypes=[wintypes.LPCWSTR,ctypes.POINTER(wintypes.DWORD)]
version_api.GetFileVersionInfoW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p]
version_api.VerQueryValueW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(wintypes.UINT)]
for executable in [win/'星匣.exe',win/'StarcaseUpdater.exe']:
    length=version_api.GetFileVersionInfoSizeW(str(executable),None)
    assert length, 'Rebuild Windows: executable has no version metadata'
    buf=ctypes.create_string_buffer(length)
    assert version_api.GetFileVersionInfoW(str(executable),0,length,buf)
    fixed=ctypes.c_void_p();size=wintypes.UINT()
    assert version_api.VerQueryValueW(buf,'\\',ctypes.byref(fixed),ctypes.byref(size))
    values=ctypes.cast(fixed,ctypes.POINTER(wintypes.DWORD))
    assert (values[2]>>16,values[2]&65535,values[3]>>16)==tuple(map(int,version.split('.'))), 'Compiled Windows executable version mismatch'
assert json.loads((win / 'service/version.json').read_text(encoding='utf8'))['version'] == version
assert (win / '星匣.html').read_bytes() == (O / '星匣.html').read_bytes(), 'Rebuild Windows after web changes'
assert (win / 'service/server.py').read_bytes() == (R / 'native/server.py').read_bytes(), 'Rebuild Windows after service changes'
with zipfile.ZipFile(O / '星匣-Android.apk') as apk:
    assert apk.read('assets/index.html') == (O / '星匣.html').read_bytes(), 'Rebuild Android after web changes'
    assert 'classes.dex' in apk.namelist()
shutil.copyfile(R / 'README.md', O / '使用说明.md')
shutil.copyfile(R / 'README.md', win / '使用说明.md')
release = O / ('release-v' + version)
release.mkdir(exist_ok=True)
installer = 'MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
blocked = {'private', '.build', '.git', '__pycache__', 'backups', 'user-data', 'userdata'}

def appzip(target, top, full=False):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for file in sorted(win.rglob('*')):
            rel = file.relative_to(win)
            if not file.is_file() or any(p.lower() in blocked for p in rel.parts) or file.suffix == '.pyc':
                continue
            assert file.name not in ('library.json', 'connection.json'), 'User data found inside build output'
            if not full and file.name == installer:
                continue
            z.write(file, top + '/' + rel.as_posix())

appzip(O / ('星匣-Windows-轻量-v' + version + '.zip'), '星匣-Windows')
if args.full:
    appzip(O / ('星匣-Windows-完整-v' + version + '.zip'), '星匣-Windows', True)
update = release / 'Starcase-Windows-Update.zip'
appzip(update, 'Starcase-Update')
assert update.stat().st_size <= 128 * 1024 * 1024, 'Update download exceeds client limit'
with zipfile.ZipFile(update) as z:
    assert sum(x.file_size for x in z.infolist()) <= 240 * 1024 * 1024
shutil.copyfile(O / '星匣-Android.apk', release / 'Starcase-Android.apk')
shutil.copyfile(O / '星匣.html', release / 'Starcase.html')
shutil.copyfile(O / '使用说明.md', release / '使用说明.md')
for name in ['标准模板.json', '资料包-schema.json', '数据结构说明.json']:
    shutil.copyfile(O / name, release / name)
shutil.copyfile(O / ('星匣-Windows-轻量-v' + version + '.zip'), release / 'Starcase-Windows-Light.zip')
if args.full:
    shutil.copyfile(O / ('星匣-Windows-完整-v' + version + '.zip'), release / 'Starcase-Windows-Full.zip')

# An explicit source allowlist keeps caches, private samples, signing keys, and QA builds out.
with zipfile.ZipFile(O / ('Starcase-Source-v' + version + '.zip'), 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ['README.md', 'DESIGN.md', '.gitignore', 'AGENTS.md']:
        if (R / name).exists():
            z.write(R / name, 'starcase-archive/' + name)
    for directory in ['src', 'native', 'tools', 'tests', 'maintenance', 'schema', 'docs']:
        for file in sorted((R / directory).rglob('*')):
            rel = file.relative_to(R)
            if not file.is_file() or any(p.lower() in blocked for p in rel.parts):
                continue
            if file.suffix in ('.pyc', '.pem', '.p12', '.keystore') or file.name.endswith(('-failure.json', '-report.json')):
                continue
            if file == R / 'native/android/assets/index.html':
                continue
            z.write(file, 'starcase-archive/' + rel.as_posix())
shutil.copyfile(O / ('Starcase-Source-v' + version + '.zip'), release / 'Starcase-Source.zip')

def record(file):
    return {'size': file.stat().st_size, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}

payload = {
    'app': 'starcase-archive', 'schema': 1, 'version': version,
    'notes': args.notes_file.read_text(encoding='utf-8-sig') if args.notes_file else '本地模板预览版：灵感、世界观、COC 模组、规则与资料。',
    'windows': {'url': repo + 'releases/download/v' + version + '/Starcase-Windows-Update.zip', **record(update)},
    'android': {'url': repo + 'releases/download/v' + version + '/Starcase-Android.apk',
                'package': 'com.starcase.archive', 'versionCode': code, **record(release / 'Starcase-Android.apk')}
}
(release / 'payload-preview.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
if args.sign:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    keyfile = R / 'private/signing/update.pem'
    key = serialization.load_pem_private_key(keyfile.read_bytes(), None)
    public = json.loads((O / '更新公钥.json').read_text(encoding='utf8'))
    expected = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    assert base64.b64decode(public['spki']) == expected, 'Signing key differs from the shipped public key'
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf8')
    signature = key.sign(raw, padding.PKCS1v15(), hashes.SHA256())
    key.public_key().verify(signature, raw, padding.PKCS1v15(), hashes.SHA256())
    envelope = {'payload': base64.b64encode(raw).decode(), 'signature': base64.b64encode(signature).decode()}
    (release / 'stable.candidate.json').write_text(json.dumps(envelope, indent=2), encoding='utf8')
    print('Signed LOCAL candidate; no GitHub upload or online update activation was performed.')
else:
    (release / 'stable.candidate.json').unlink(missing_ok=True)
files = {f.name: record(f) for f in sorted(release.iterdir()) if f.is_file() and f.name != 'checksums.json'}
(release / 'checksums.json').write_text(json.dumps(files, ensure_ascii=False, indent=2), encoding='utf8')
print('Prepared local release', version, 'in', release)
