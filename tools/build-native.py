from pathlib import Path
import os,sys,shutil,subprocess,zipfile,json,secrets,hashlib,re
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent.parent;OLD=Path(os.environ.get('STARCASE_BUILD_TOOLS','C:/Users/PC/Documents/Codex/2026-10-13/new-chat'));N=R/'native';O=R/'outputs';B=R/'.build';B.mkdir(exist_ok=True)
def run(args,env=None):
 p=subprocess.run([str(x) for x in args],cwd=R,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
 if p.returncode:print(p.stdout);print(p.stderr);raise RuntimeError('Build failed: '+str(args[0]))
 if p.stdout.strip():print(p.stdout.strip())
def icon():
 image=Image.new('RGBA',(1024,1024),(0,0,0,0));d=ImageDraw.Draw(image);d.rounded_rectangle((12,12,1012,1012),radius=210,fill='#302937');d.rounded_rectangle((220,265,802,820),radius=24,outline='#e6c68b',width=28);d.rectangle((199,227,823,327),fill='#302937',outline='#e6c68b',width=28);d.rectangle((296,709,724,729),fill='#d3b079');d.polygon([(512,389),(548,481),(641,517),(548,553),(512,645),(476,553),(383,517),(476,481)],fill='#e6c68b');image=image.resize((256,256),Image.Resampling.LANCZOS);image.save(N/'icon.png');image.save(N/'windows/starcase.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]);shutil.copyfile(N/'icon.png',N/'android/res/drawable/folio_icon.png')
def windows():
 out=O/'星匣-Windows';out.mkdir(exist_ok=True);deps=OLD/'work/windows-deps';src=N/'windows';shutil.copyfile(O/'星匣.html',out/'星匣.html');shutil.copyfile(src/'starcase.ico',out/'starcase.ico');shutil.copytree(deps/'python',out/'runtime',dirs_exist_ok=True);(out/'service').mkdir(exist_ok=True);shutil.copyfile(N/'server.py',out/'service/server.py');(out/'service/version.json').write_text(json.dumps({'app':'starcase-archive','version':'0.1.1','schemaVersion':1}),encoding='utf8')
 for name in ['标准模板.json','资料包-schema.json','数据结构说明.json','qrcodegen-LICENSE.txt']:shutil.copyfile(O/name,out/name)
 for name in ['Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll']:shutil.copyfile(deps/'lib/net462'/name,out/name)
 shutil.copyfile(deps/'build/native/x64/WebView2Loader.dll',out/'WebView2Loader.dll')
 for p in deps.rglob('*'):
  if p.is_file() and 'LICENSE' in p.name.upper():shutil.copyfile(p,out/('WebView2-'+p.name))
 # Keep the application's own asInvoker / DPI manifest; do not overwrite it from the old project.
 assert 'level="asInvoker"' in (src/'app.manifest').read_text(encoding='utf8')
 version=re.search(r'Current="([\d.]+)"',(src/'UpdateProtocol.cs').read_text(encoding='utf8')).group(1)
 (src/'VersionInfo.cs').write_text('using System.Reflection;[assembly:AssemblyVersion("'+version+'.0")][assembly:AssemblyFileVersion("'+version+'.0")][assembly:AssemblyInformationalVersion("'+version+'")]\n',encoding='utf8')
 compiler=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe');common=[compiler,'/nologo','/target:winexe','/platform:x64','/optimize+','/codepage:65001','/win32manifest:'+str(src/'app.manifest'),'/win32icon:'+str(src/'starcase.ico')]
 refs=['System.dll','System.Core.dll','System.Management.dll','System.Drawing.dll','System.Windows.Forms.dll','System.Web.Extensions.dll'];run([*common,'/out:'+str(out/'星匣.exe'),*['/reference:'+r for r in refs],'/reference:'+str(out/'Microsoft.Web.WebView2.Core.dll'),'/reference:'+str(out/'Microsoft.Web.WebView2.WinForms.dll'),*[src/n for n in ['Program.cs','BridgeLifecycle24.cs','Updates.cs','UpdateProtocol.cs','UpdateKey.cs','VersionInfo.cs']]])
 run([*common,'/out:'+str(out/'StarcaseUpdater.exe'),*['/reference:'+r for r in refs+['System.IO.Compression.dll','System.IO.Compression.FileSystem.dll']],*[src/n for n in ['Updater.cs','UpdateProtocol.cs','UpdateKey.cs','VersionInfo.cs']]])
 info=json.loads((OLD/'work/v16-runtime-info.json').read_text(encoding='utf8'));installer=OLD/'work/windows-deps/WebView2Installer/MicrosoftEdgeWebView2RuntimeInstallerX64-complete.exe'
 assert hashlib.sha256(installer.read_bytes()).hexdigest()==info['sha256'];shutil.copyfile(installer,out/'MicrosoftEdgeWebView2RuntimeInstallerX64.exe')
 # This workspace inherits Low integrity. A Low-labelled image also launches at Low
 # and cannot save in the normal Medium-integrity user profile, even when its ACL allows it.
 # Set only delivered executable images to the normal desktop level; no elevation or data ACL change.
 for executable in sorted(out.rglob('*.exe')):run(['icacls.exe',executable,'/setintegritylevel','M'])
 print('Built Windows app',out/'星匣.exe')
def android():
 original=N/'android';ascii_root=OLD/'work/starcase-build-0.1';src=ascii_root/'project';ascii_root.mkdir(exist_ok=True);shutil.copytree(original,src,dirs_exist_ok=True);sdk=OLD/'work/android-sdk';tools=sdk/'build-tools/36.0.0';platform=sdk/'platforms/android-36/android.jar';build=ascii_root/'build';build.mkdir(exist_ok=True);java=Path('C:/Program Files/Microsoft/jdk-21.0.10.7-hotspot');env=os.environ.copy();env['JAVA_HOME']=str(java);signing=R/'private/signing';credentials=signing/'android-credentials.json'
 if not credentials.exists():credentials.write_text(json.dumps({'password':secrets.token_urlsafe(28)}),encoding='utf8')
 env['STARCASE_KS_PASSWORD']=json.loads(credentials.read_text(encoding='utf8'))['password'];key=signing/'starcase-release.p12'
 if not key.exists():run([java/'bin/keytool.exe','-genkeypair','-keystore',key,'-storetype','PKCS12','-storepass:env','STARCASE_KS_PASSWORD','-alias','starcase','-keyalg','RSA','-keysize','3072','-validity','10950','-dname','CN=Starcase Archive, O=Personal Software, C=CN'],env)
 shutil.copyfile(O/'星匣.html',src/'assets/index.html');shutil.copyfile(OLD/'work/android-deps/zxing-LICENSE.txt',src/'assets/zxing-LICENSE.txt');shutil.copyfile(O/'qrcodegen-LICENSE.txt',src/'assets/qrcodegen-LICENSE.txt')
 run([tools/'aapt2.exe','compile','--dir',src/'res','-o',build/'resources.zip'],env);link_args=[tools/'aapt2.exe','link','-o',build/'resources.apk','-I',platform,'--manifest',src/'AndroidManifest.xml','-A',src/'assets',build/'resources.zip','--min-sdk-version','26','--target-sdk-version','36'];link_args+=['--debug-mode'] if '--qa' in sys.argv else [];run(link_args,env)
 classes=build/'classes';classes.mkdir(exist_ok=True);dex=build/'dex';dex.mkdir(exist_ok=True);zxing=OLD/'work/android-deps/zxing-core-3.5.3.jar'
 run([java/'bin/javac.exe','-J-Duser.language=en','-J-Duser.country=US','-encoding','UTF-8','-source','8','-target','8','-classpath',str(platform)+os.pathsep+str(zxing),'-d',classes,*sorted((src/'src').rglob('*.java'))],env);run([tools/'d8.bat','--lib',platform,'--min-api','26','--output',dex,*sorted(classes.rglob('*.class')),zxing],env)
 shutil.copyfile(build/'resources.apk',build/'unsigned.apk')
 with zipfile.ZipFile(build/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:z.write(dex/'classes.dex','classes.dex')
 run([tools/'zipalign.exe','-f','-P','16','4',build/'unsigned.apk',build/'aligned.apk'],env);run([tools/'apksigner.bat','sign','--ks',key,'--ks-key-alias','starcase','--ks-pass','env:STARCASE_KS_PASSWORD','--out',build/'Starcase-Android.apk',build/'aligned.apk'],env);run([tools/'apksigner.bat','verify','--verbose',build/'Starcase-Android.apk'],env);shutil.copyfile(build/'Starcase-Android.apk',B/'Starcase-QA.apk' if '--qa' in sys.argv else O/'星匣-Android.apk');print('Built Android app',O/'星匣-Android.apk')
if __name__=='__main__':
 icon()
 if len(sys.argv)<2 or sys.argv[1]=='windows':windows()
 if len(sys.argv)<2 or sys.argv[1]=='android':android()
