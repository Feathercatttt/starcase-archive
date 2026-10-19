"""GitHub-hosted assembly of manual packages. No application signing keys or private data needed."""
from pathlib import Path
import argparse,base64,copy,hashlib,json,os,re,subprocess,urllib.request,zipfile
parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True);args=parser.parse_args()
assert re.fullmatch(r'v\d+\.\d+\.\d+',args.tag)
R=Path(__file__).resolve().parent.parent;plan=json.loads((R/'.github'/('assembly-'+args.tag+'.json')).read_text(encoding='utf8'));repo=os.environ['GH_REPO'];work=R/'work-assembly';work.mkdir(exist_ok=True)
def gh(*a):return subprocess.run(['gh',*a],check=True,capture_output=True,text=True,encoding='utf8').stdout
def meta(p):return {'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
releases=json.loads(gh('api','repos/'+repo+'/releases?per_page=100'))
release=next(x for x in releases if x['tag_name']==args.tag);assert release['draft'],'Only assemble unpublished draft releases'
asset=next(x for x in release['assets'] if x['name']=='Starcase-Windows-Update.zip' and x['state']=='uploaded')
update=work/'Starcase-Windows-Update.zip'
with update.open('wb') as out:subprocess.run(['gh','api','repos/'+repo+'/releases/assets/'+str(asset['id']),'-H','Accept: application/octet-stream'],stdout=out,check=True)
assert meta(update)['sha256']==plan['updateSha256']
installer=work/'MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
with urllib.request.urlopen(plan['installerSource'],timeout=120) as response,installer.open('wb') as out:
    for block in iter(lambda:response.read(1024*1024),b''):out.write(block)
command="$s=Get-AuthenticodeSignature -LiteralPath '"+str(installer).replace("'","''")+"'; [pscustomobject]@{status=$s.Status.ToString();subject=$s.SignerCertificate.Subject}|ConvertTo-Json"
auth=json.loads(subprocess.run(['powershell','-NoProfile','-Command',command],check=True,capture_output=True,text=True,encoding='utf8').stdout)
assert auth['status']=='Valid' and 'O=Microsoft Corporation' in auth['subject'],'Runtime is not signed by Microsoft'
with zipfile.ZipFile(update) as source:
    entries={}
    for old in source.infolist():
        assert old.filename.startswith('Starcase-Update/') and '..' not in old.filename.split('/')
        info=copy.copy(old);info.filename='星匣-Windows/'+old.filename[len('Starcase-Update/'):];entries[info.filename]=(info,source.read(old))
    for full,name in [(False,'Starcase-Windows-Light.zip'),(True,'Starcase-Windows-Full.zip')]:
        items=dict(entries)
        if full:
            item=plan['installerInfo'];info=zipfile.ZipInfo('星匣-Windows/MicrosoftEdgeWebView2RuntimeInstallerX64.exe',tuple(item['date_time']))
            for key in ['create_system','create_version','extract_version','reserved','volume','internal_attr','external_attr']:setattr(info,key,item[key])
            info.compress_type=zipfile.ZIP_DEFLATED;items[info.filename]=(info,installer.read_bytes())
        with zipfile.ZipFile(work/name,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for key in sorted(items,key=lambda n:tuple(n.casefold().split('/'))):
                info,data=items[key];z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
        if not full:assert meta(work/name)['sha256']==plan['lightSha256'],'Light package differs from tested local artifact'
report={'tag':args.tag,'update':meta(update),'light':meta(work/'Starcase-Windows-Light.zip'),'full':meta(work/'Starcase-Windows-Full.zip'),'microsoftRuntime':{**meta(installer),**auth},'privateSigningKeysUsed':False}
(work/'assembly-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for name in ['Starcase-Windows-Light.zip','Starcase-Windows-Full.zip','assembly-report.json']:gh('release','upload',args.tag,str(work/name),'--repo',repo,'--clobber')
print(json.dumps(report,ensure_ascii=False,indent=2))
