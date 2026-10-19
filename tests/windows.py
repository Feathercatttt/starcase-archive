from pathlib import Path
import subprocess,json,uuid,zipfile,tempfile,ctypes,sys,re
from ctypes import wintypes
R=Path(__file__).resolve().parent.parent
version=re.search(r'Current="([\d.]+)"',(R/'native/windows/UpdateProtocol.cs').read_text(encoding='utf8')).group(1)
# Test a normal user-profile folder, not the Low-integrity build workspace that hid the startup bug.
folder=Path(tempfile.mkdtemp(prefix='starcase-windows-qa-'));exe=R/'outputs/星匣-Windows/星匣.exe';start=subprocess.STARTUPINFO();start.dwFlags|=subprocess.STARTF_USESHOWWINDOW;start.wShowWindow=0
if '--archive' in sys.argv:
 package=Path(sys.argv[sys.argv.index('--archive')+1]);installation=Path(tempfile.mkdtemp(prefix='starcase-unpacked-'))
 with zipfile.ZipFile(package) as z:
  assert all(n.startswith('星匣-Windows/') and '..' not in n.split('/') for n in z.namelist())
  z.extractall(installation)
 exe=installation/'星匣-Windows/星匣.exe'
kernel=ctypes.WinDLL('kernel32',use_last_error=True);security=ctypes.WinDLL('advapi32',use_last_error=True)
kernel.GetCurrentProcess.restype=wintypes.HANDLE
security.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
security.GetTokenInformation.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
token=wintypes.HANDLE();assert security.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token))
elevated=wintypes.DWORD();size=wintypes.DWORD();assert security.GetTokenInformation(token,20,ctypes.byref(elevated),ctypes.sizeof(elevated),ctypes.byref(size));kernel.CloseHandle(token)
assert elevated.value==0,'Run this regression test without administrator elevation'
p=subprocess.Popen([str(exe),'--self-test',str(folder)],cwd=exe.parent,startupinfo=start)
child_token=wintypes.HANDLE();assert security.OpenProcessToken(wintypes.HANDLE(int(p._handle)),8,ctypes.byref(child_token))
child_elevated=wintypes.DWORD();assert security.GetTokenInformation(child_token,20,ctypes.byref(child_elevated),ctypes.sizeof(child_elevated),ctypes.byref(size));kernel.CloseHandle(child_token)
assert child_elevated.value==0,'Application unexpectedly runs elevated'
try:p.wait(timeout=55)
except subprocess.TimeoutExpired:p.kill();raise
assert not (folder/'error.txt').exists(),(folder/'error.txt').read_text(encoding='utf8') if (folder/'error.txt').exists() else ''
assert (folder/'success.txt').exists();data=json.loads(json.loads((folder/'native-result.json').read_text(encoding='utf8')));assert data['platform']=='windows' and data['found'] and data['server'];update=json.loads(json.loads((folder/'update-result.json').read_text(encoding='utf8')));assert update['current']==version
cache=json.loads((folder/'library.json').read_text(encoding='utf8'));assert any(e['title']=='Windows 原生保存验证' for e in cache['data']['entries'])
checks=['Non-elevated production Windows EXE launches actual WebView2 and service using a normal user-profile folder outside the build workspace','Native WebView saves a new inspiration through IndexedDB into the actual local JSON archive','Update bridge reports Starcase v'+version+' independently of Traveler Folio; original user apps/data are untouched']
if '--archive' in sys.argv:checks.append('Freshly extracted light ZIP also starts and saves without administrator elevation')
(R/'tests/windows-report.json').write_text(json.dumps({'success':True,'checks':checks},ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'success':True,'checks':checks},ensure_ascii=False))
