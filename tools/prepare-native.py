"""Reuse the tested transport/update engines, with independent identity and signing keys."""
from pathlib import Path
import shutil,json,re,base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
R=Path(__file__).resolve().parent.parent;OLD=Path('C:/Users/PC/Documents/Codex/2026-10-13/new-chat');N=R/'native';WIN=N/'windows';JAVA=N/'android/src/com/starcase/archive';WIN.mkdir(parents=True,exist_ok=True);JAVA.mkdir(parents=True,exist_ok=True)
def adapt(s):
 for a,b in [('FolioUpdater.exe','StarcaseUpdater.exe'),('角色数据','创作资料'),('com.traveler.folio','com.starcase.archive'),('traveler-folio','starcase-archive'),('TravelerFolio','Starcase'),('旅人手札','星匣'),('手札','星匣'),('角色卡','资料库'),('角色与卡库','创作资料'),('FolioNative','ArchiveNative'),('folio.local','starcase.local'),('0.29.1','0.1.0')]:s=s.replace(a,b)
 return s
for name in ['UpdateProtocol.cs','Updates.cs','Updater.cs','BridgeLifecycle24.cs']:
 s=adapt((OLD/'work/windows-app'/name).read_text(encoding='utf8'))
 if name=='BridgeLifecycle24.cs':s=s.replace('"owlbear"','"service"')
 if name=='Updater.cs':
  s=s.replace('RetireLegacyDocs28(target,jobDir);','')
  s=re.sub(r' internal static void RetireLegacyDocs28\(.*?\}\r?\n','',s)
  start=s.index('string pluginFile=');end=s.index('foreach(string file in Directory.GetFiles',start)
  s=s[:start]+'string versionFile=Path.Combine(source,"service","version.json");if(!File.Exists(versionFile)||UpdateProtocol.Text(UpdateProtocol.Serializer().Deserialize<Dictionary<string,object>>(File.ReadAllText(versionFile)),"version")!=UpdateProtocol.Text(p,"version"))throw new Exception("更新包版本不匹配");progress("正在备份并替换应用…");'+s[end:]
  s=s.replace('"owlbear","server.py"','"service","server.py"')
 (WIN/name).write_text(s,encoding='utf8',newline='\n')
for p in (OLD/'work/android-app/src/com/traveler/folio').glob('*.java'):
 if p.name=='UpdateKey.java':continue
 s=adapt(p.read_text(encoding='utf8'))
 if p.name=='MainActivity.java':s=s.replace('return text.substring(offset,Math.min(text.length(),offset+48000));','int end=Math.min(text.length(),offset+48000);if(end<text.length()&&Character.isHighSurrogate(text.charAt(end-1)))end--;return text.substring(offset,end);').replace('Color.rgb(245,236,218)','Color.rgb(240,232,217)').replace('"FolioWeb"','"StarcaseWeb"')
 if p.name=='LanTransfer16.java':
  s=s.replace('/t/','/a/').replace('u.getPort()<1024||u.getPort()>65535','u.getPort()!=17653')
  s=s.replace('!(body.startsWith("LS13.G.")||body.startsWith("LS16.L."))','!validPackage(body)').replace('!(text.startsWith("LS13.G.")||text.startsWith("LS16.L."))','!validPackage(text)')
  s=s.replace('final class LanTransfer16 {','final class LanTransfer16 {\n static boolean validPackage(String text){try{org.json.JSONObject p=new org.json.JSONObject(text);return "starcase-archive".equals(p.optString("format"))&&p.optInt("packageVersion")==1;}catch(Exception e){return false;}}')
 (JAVA/p.name).write_text(s,encoding='utf8',newline='\n')
manifest=adapt((OLD/'work/android-app/AndroidManifest.xml').read_text(encoding='utf8')).replace('versionCode="36"','versionCode="1"')
(N/'android/AndroidManifest.xml').write_text(manifest,encoding='utf8')
(N/'android/res/values').mkdir(parents=True,exist_ok=True);(N/'android/res/drawable').mkdir(exist_ok=True);(N/'android/assets').mkdir(exist_ok=True)
styles=(OLD/'work/android-app/res/values/styles.xml').read_text(encoding='utf8').replace('#e8dcc4','#f0e8d9').replace('#f5ecda','#f0e8d9').replace('#9b6d30','#88642e')
(N/'android/res/values/styles.xml').write_text(styles,encoding='utf8')
key_path=R/'private/signing/update.pem';key_path.parent.mkdir(exist_ok=True)
if not key_path.exists():
 key=rsa.generate_private_key(public_exponent=65537,key_size=3072);key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
key=serialization.load_pem_private_key(key_path.read_bytes(),None);nums=key.public_key().public_numbers();enc=lambda n:base64.b64encode(n.to_bytes((n.bit_length()+7)//8,'big')).decode();xml='<RSAKeyValue><Modulus>'+enc(nums.n)+'</Modulus><Exponent>'+enc(nums.e)+'</Exponent></RSAKeyValue>';spki=base64.b64encode(key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
(WIN/'UpdateKey.cs').write_text('internal static class UpdateKey {internal const string Xml='+json.dumps(xml)+';}\n',encoding='utf8')
(JAVA/'UpdateKey.java').write_text('package com.starcase.archive;final class UpdateKey {static final String SPKI='+json.dumps(spki)+';}\n',encoding='utf8')
(R/'outputs/更新公钥.json').write_text(json.dumps({'algorithm':'RSA-SHA256','xml':xml,'spki':spki},indent=2),encoding='utf8')
print('Prepared independent Windows/Android identities and public update keys')
