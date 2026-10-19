"""Publish reviewed local Starcase artifacts. Requires explicit --publish; never reads browser credentials."""
from pathlib import Path
import argparse, base64, hashlib, json, os, re, shutil, subprocess, time, urllib.request

R=Path(__file__).resolve().parent.parent
GH=Path(os.environ.get('STARCASE_GH','C:/Users/PC/Documents/Codex/2026-10-13/new-chat/work/github-tools/gh.exe'))
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--publish',action='store_true')
parser.add_argument('--assembly-run',type=int,help='Reuse a GitHub package-assembly run and avoid uploading the large runtime locally')
parser.add_argument('--essential-only',action='store_true',help='Publish native update/manual ZIP, APK, HTML and source; no dependency on Actions or full offline runtime')
args=parser.parse_args()
protocol=(R/'native/windows/UpdateProtocol.cs').read_text(encoding='utf8')
version=re.search(r'Current="([\d.]+)"',protocol).group(1)
repo=re.search(r'Repo="https://github.com/([^\"]+)/"',protocol).group(1)
tag='v'+version
release_dir=R/'outputs'/('release-'+tag)
verify_dir=R/'.build'/('published-'+tag);verify_dir.mkdir(exist_ok=True)
assets=['Starcase-Windows-Update.zip','Starcase-Windows-Light.zip','Starcase-Windows-Full.zip','Starcase-Android.apk','Starcase.html','Starcase-Source.zip','checksums.json']
if args.essential_only:assets=[name for name in assets if name not in ('Starcase-Windows-Light.zip','Starcase-Windows-Full.zip')]
roots=['.gitignore','AGENTS.md','README.md','DESIGN.md','src','native','tools','tests','maintenance','schema','docs']
def call(command,optional=False):
    env=os.environ.copy()
    if str(command[0])==str(GH):env['GODEBUG']=','.join([x for x in env.get('GODEBUG','').split(',') if x and not x.startswith('http2client=')]+['http2client=0'])
    p=subprocess.run([str(a) for a in command],cwd=R,capture_output=True,text=True,encoding='utf8',errors='replace',env=env,timeout=1200)
    if p.returncode:
        if optional:return None
        raise RuntimeError('Command failed: '+str(command[0])+'\n'+p.stderr[-2500:])
    return p.stdout.strip()
def gh(*words,optional=False):return call([GH,*words],optional)
def git(*words,optional=False):return call(['git',*words],optional)
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
def metadata(file):return {'size':file.stat().st_size,'sha256':sha(file)}
def find_release():
    # /releases/tags/:tag omits drafts; the owner-visible list includes them.
    pages=json.loads(gh('api','repos/'+repo+'/releases?per_page=100','--paginate','--slurp'))
    return next((item for page in pages for item in page if item['tag_name']==tag),None)

assert 'UPDATE_PUBLISHED=true' in (R/'src/native.js').read_text(encoding='utf8')
assert all((release_dir/name).is_file() for name in assets)
checksums={name:metadata(release_dir/name) for name in assets if name!='checksums.json'}
(release_dir/'checksums.json').write_text(json.dumps(checksums,ensure_ascii=False,indent=2),encoding='utf8')
identity=json.loads(gh('api','user'))
assert identity['login'].lower()==repo.split('/')[0].lower(),'Active GitHub account does not own the release repository'
print('Release plan:',repo,tag,len(assets),'public program/source attachments; no personal archive',flush=True)
if not args.publish:
    print('Local preflight only. Use --publish for an authorized publication.');raise SystemExit(0)
assert (release_dir/'stable.candidate.json').is_file()
if not (R/'.git').exists():git('init','-b','main')
if not git('config','user.name',optional=True):git('config','user.name',identity['login'])
if not git('config','user.email',optional=True):git('config','user.email',str(identity['id'])+'+'+identity['login']+'@users.noreply.github.com')
git('add','--',*roots)
staged=git('diff','--cached','--name-only','-z').split('\0')
secret=re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})')
for name in filter(None,staged):
    rel=Path(name)
    assert not {'private','.build','outputs','__pycache__','.git'} & set(rel.parts),'Private or generated path staged: '+name
    assert rel.suffix.lower() not in ('.pem','.p12','.keystore','.apk','.zip'), 'Binary package/key staged: '+name
    assert not secret.search((R/rel).read_bytes()),'Credential-shaped content detected: '+name
if staged and staged!=['']:git('commit','-m','Release Starcase '+tag+' with Windows and Android online updates')
commit=git('rev-parse','HEAD')
remote=git('remote','get-url','origin',optional=True)
if remote is None:
    if gh('repo','view',repo,'--json','nameWithOwner',optional=True) is None:
        gh('repo','create',repo,'--public','--description','星匣 · AI 辅助编写的 DND 世界观、COC 模组、规则与灵感个人资料库；Windows / Android / 离线 HTML')
    git('remote','add','origin','https://github.com/'+repo+'.git')
else:assert remote.rstrip('/').removesuffix('.git')=='https://github.com/'+repo,'Unexpected origin; refusing to change it'
credentials=['-c','credential.helper=','-c','credential.helper=!'+GH.as_posix()+' auth git-credential']
git(*credentials,'push','-u','origin','main')
existing_tag=git('rev-parse',tag+'^{commit}',optional=True)
if existing_tag is None:git('tag','-a',tag,'-m','Starcase '+tag,commit)
else:
    assert not git('diff','--name-only',existing_tag,commit,'--','src','native'),'Existing release tag has different application sources; bump the version'
    commit=existing_tag
git(*credentials,'push','origin',tag)
release=find_release()
if release is None:
    gh('release','create',tag,'--repo',repo,'--verify-tag','--draft','--title','星匣 '+tag,'--notes-file',R/'docs/releases'/(tag+'.md'))
    release=find_release();assert release is not None
if release['draft']:
    # Discard only incomplete uploads in this owned draft, never completed assets.
    for a in release['assets']:
        if a.get('state')=='starter':gh('api','--method','DELETE','repos/'+repo+'/releases/assets/'+str(a['id']))
    if args.assembly_run:
        from assembly_adopt import adopt
        adopt(R,release_dir,repo,args.assembly_run,gh)
        checksums={name:metadata(release_dir/name) for name in assets if name!='checksums.json'}
        (release_dir/'checksums.json').write_text(json.dumps(checksums,ensure_ascii=False,indent=2),encoding='utf8')
        release=find_release()
    present={a['name']:a for a in release['assets']}
    for name in assets:
        existing=present.get(name)
        if existing and existing.get('state')=='uploaded' and existing.get('digest')=='sha256:'+sha(release_dir/name):
            print('Already verified in draft',name,flush=True);continue
        print('Uploading',name,metadata(release_dir/name)['size'],'bytes',flush=True)
        gh('release','upload',tag,release_dir/name,'--repo',repo,'--clobber')
    gh('release','edit',tag,'--repo',repo,'--draft=false','--latest')
release=json.loads(gh('api','repos/'+repo+'/releases/tags/'+tag))
assert not release['draft']
remote_assets={a['name']:a for a in release['assets']}
for name in assets:
    a=remote_assets[name]
    assert a['size']==(release_dir/name).stat().st_size,'Remote size mismatch: '+name
    if a.get('digest'):assert a['digest']=='sha256:'+sha(release_dir/name),'Remote digest mismatch: '+name
for name in ['Starcase-Windows-Update.zip','Starcase-Android.apk','Starcase.html']:
    print('Reading back public attachment',name,flush=True)
    last=None
    for prefix in ['', 'https://gh-proxy.org/','https://ghfast.top/','https://ghproxy.net/']:
        try:
            request=urllib.request.Request(prefix+remote_assets[name]['browser_download_url'],headers={'User-Agent':'Starcase-Publish/'+version,'Accept-Encoding':'identity'})
            with urllib.request.urlopen(request,timeout=20) as response,(verify_dir/name).open('wb') as out:
                for chunk in iter(lambda:response.read(65536),b''):out.write(chunk)
            assert sha(verify_dir/name)==sha(release_dir/name),'Downloaded attachment mismatch: '+name
            last=None;break
        except Exception as e:last=e
    if last is not None:raise last
# Switch the live pointer only after the public native attachments have been read back.
updates=R/'updates';updates.mkdir(exist_ok=True)
shutil.copyfile(release_dir/'stable.candidate.json',updates/'stable.json')
git('add','--','updates/stable.json')
if git('diff','--cached','--name-only'):git('commit','-m','Publish verified signed update manifest for '+tag);git(*credentials,'push','origin','main')
remote=gh('api','repos/'+repo+'/contents/updates/stable.json')
blob=json.loads(remote);assert base64.b64decode(blob['content'])==(updates/'stable.json').read_bytes()
result={'repo':'https://github.com/'+repo,'release':release['html_url'],'version':version,'sourceCommit':commit,'manifestCommit':git('rev-parse','HEAD'),'assets':{name:{'size':a['size'],'digest':a.get('digest'),'url':a['browser_download_url']} for name,a in remote_assets.items()},'nativeAttachmentsDownloadedAndMatched':True,'signedManifestReadBack':True}
(verify_dir/'publish-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:result[k] for k in ['repo','release','version','nativeAttachmentsDownloadedAndMatched','signedManifestReadBack']},ensure_ascii=False),flush=True)
