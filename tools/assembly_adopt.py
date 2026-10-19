"""Adopt GitHub-assembled manual archives after checking the native files and runtime signature."""
from pathlib import Path
import hashlib,json,shutil,subprocess,zipfile

def adopt(root,release_dir,repo,run_id,gh):
    tag=release_dir.name.removeprefix('release-')
    gh('run','watch',str(run_id),'--repo',repo,'--exit-status')
    temp=root/'.build'/('assembly-'+tag);temp.mkdir(exist_ok=True)
    for name in ['assembly-report.json','Starcase-Windows-Full.zip']:
        print('Reading back GitHub-assembled',name,flush=True)
        gh('release','download',tag,'--repo',repo,'--pattern',name,'--dir',str(temp),'--clobber')
    report=json.loads((temp/'assembly-report.json').read_text(encoding='utf8'))
    hash_file=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert report['tag']==tag and report['privateSigningKeysUsed'] is False
    assert report['update']['sha256']==hash_file(release_dir/'Starcase-Windows-Update.zip')
    assert report['light']['sha256']==hash_file(release_dir/'Starcase-Windows-Light.zip')
    assert report['full']['sha256']==hash_file(temp/'Starcase-Windows-Full.zip')
    assert report['microsoftRuntime']['status']=='Valid' and 'O=Microsoft Corporation' in report['microsoftRuntime']['subject']
    with zipfile.ZipFile(release_dir/'Starcase-Windows-Update.zip') as src,zipfile.ZipFile(temp/'Starcase-Windows-Full.zip') as full:
        expected={'星匣-Windows/'+name[len('Starcase-Update/'):]:name for name in src.namelist()}
        installer='星匣-Windows/MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
        assert set(full.namelist())==set(expected)|{installer}
        for target,old in expected.items():assert full.read(target)==src.read(old),'Assembled native file changed: '+target
        raw=full.read(installer);assert hashlib.sha256(raw).hexdigest()==report['microsoftRuntime']['sha256']
        runtime=temp/'MicrosoftEdgeWebView2RuntimeInstallerX64.exe';runtime.write_bytes(raw)
    cmd="$s=Get-AuthenticodeSignature -LiteralPath '"+str(runtime).replace("'","''")+"';[pscustomobject]@{status=$s.Status.ToString();subject=$s.SignerCertificate.Subject}|ConvertTo-Json"
    auth=json.loads(subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,encoding='utf8',check=True).stdout)
    assert auth['status']=='Valid' and 'O=Microsoft Corporation' in auth['subject']
    shutil.copyfile(temp/'Starcase-Windows-Full.zip',release_dir/'Starcase-Windows-Full.zip')
    shutil.copyfile(temp/'Starcase-Windows-Full.zip',root/'outputs'/('星匣-Windows-完整-'+tag+'.zip'))
    (temp/'adoption-report.json').write_text(json.dumps({'success':True,'tag':tag,'run':run_id,'full':report['full'],'allNativeFilesMatch':True,'microsoftAuthenticodeRechecked':True},indent=2),encoding='utf8')
    return report
