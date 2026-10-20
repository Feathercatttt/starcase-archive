"""Exercise the actual Windows native update engine against the public release; no install."""
from pathlib import Path
import argparse,json,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);parser.add_argument('--download',action='store_true');args=parser.parse_args()
source=args.baseline or R/'native/windows';stage=R/'.build/online-windows';stage.mkdir(exist_ok=True)
data=Path(tempfile.mkdtemp(prefix='starcase-online-update-'))
(stage/'Probe.cs').write_text('''using System;using System.IO;using System.Threading;using System.Collections.Generic;
internal static class Program{internal static string DataDir,BaseDir;}
internal static class Probe{
 static Dictionary<string,object> State(Updates u){return UpdateProtocol.Serializer().Deserialize<Dictionary<string,object>>(u.Request(new Dictionary<string,object>{{"action","state"}}));}
 static string Phase(Dictionary<string,object> s){return UpdateProtocol.Text(s,"phase");}
 static Dictionary<string,object> Wait(Updates u){var deadline=DateTime.UtcNow.AddSeconds(300);while(DateTime.UtcNow<deadline){Thread.Sleep(200);var s=State(u);string phase=Phase(s);if(phase=="error")throw new Exception(UpdateProtocol.Text(s,"message"));if(phase=="available"||phase=="latest"||phase=="ready")return s;}throw new Exception("Native online update timeout");}
 static int Main(string[] a){try{Program.DataDir=a[0];Program.BaseDir=a[0];var u=new Updates(raw=>{});u.Request(new Dictionary<string,object>{{"action","settings"},{"automatic",true},{"custom",""},{"preferred","https://gh-proxy.org/"}});u.Request(new Dictionary<string,object>{{"action","check"}});var s=Wait(u);if(a.Length>1&&a[1]=="download"){if(Phase(s)!="available")throw new Exception("Use an older baseline to test the download");u.Request(new Dictionary<string,object>{{"action","download"}});s=Wait(u);if(Phase(s)!="ready")throw new Exception("Native package was not verified ready");}Console.WriteLine(UpdateProtocol.Serializer().Serialize(s));return 0;}catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}}
}
''',encoding='utf8')
exe=stage/'Probe.exe'
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/target:exe','/out:'+str(exe),'/reference:System.dll','/reference:System.Core.dll','/reference:System.Web.Extensions.dll','/reference:System.Windows.Forms.dll',str(stage/'Probe.cs'),*[str(source/name) for name in ['Updates.cs','UpdateProtocol.cs','UpdateKey.cs']]],check=True,capture_output=True)
subprocess.run(['icacls',str(exe),'/setintegritylevel','M'],check=True,capture_output=True)
result=subprocess.run([str(exe),str(data),*(['download'] if args.download else [])],capture_output=True,text=True,encoding='utf8',timeout=650)
assert result.returncode==0,result.stderr
state=json.loads(result.stdout);assert state['phase']==('ready' if args.download else 'latest'),state
report={'success':True,'current':state['current'],'latest':state['latest'],'phase':state['phase'],'route':state.get('route'),'nativeDownloadVerified':args.download,'scope':'Actual C# Updates engine; no installation or personal-data modification'}
(R/'tests'/('online-windows-download-report.json' if args.download else 'online-windows-report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
