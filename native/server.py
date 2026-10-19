"""Loopback-only structured archive, with an explicitly opened expiring LAN handoff."""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import argparse,json,secrets,threading,urllib.parse,time,os,shutil,datetime,ipaddress,socket,socketserver
APP='starcase-archive';MAX=32*1024*1024
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def valid(data):
 if not isinstance(data,dict) or data.get('app')!=APP or data.get('schemaVersion')!=1:raise ValueError('资料格式或版本不兼容')
 for key,limit in [('entries',15000),('projects',500),('media',3000)]:
  rows=data.get(key,[])
  if not isinstance(rows,list) or len(rows)>limit:raise ValueError('资料结构或数量不正确')
  ids=[r.get('id') for r in rows if isinstance(r,dict)]
  if len(ids)!=len(rows) or any(not isinstance(i,str) or len(i)>120 or not i or not all(c.isascii() and (c.isalnum() or c in '_-') for c in i) for i in ids) or len(set(ids))!=len(ids):raise ValueError('标识重复或不正确')
 for e in data['entries']:
  if not isinstance(e.get('title'),str) or not e['title'].strip() or not isinstance(e.get('fields'),dict) or e.get('area') not in ('ideas','world','modules','rules') or e.get('system') not in ('dnd','coc','any'):raise ValueError('条目字段不完整')
 return data
def package(text):
 if not isinstance(text,str) or len(text.encode('utf8'))>MAX:raise ValueError('资料包超过32 MB')
 try:p=json.loads(text)
 except ValueError:raise ValueError('资料包格式不正确')
 if p.get('format')!=APP or p.get('packageVersion')!=1:raise ValueError('这不是星匣资料包')
 valid(p.get('data'));return p
class LANServer(ThreadingHTTPServer):
 def server_bind(self):socketserver.TCPServer.server_bind(self);self.server_name='starcase-lan';self.server_port=self.server_address[1]
class Handoff:
 def __init__(self,port):self.port=port;self.lock=threading.RLock();self.server=None;self.timer=None;self.clear()
 def clear(self):self.token='';self.payload='';self.incoming=None;self.expires=0;self.addresses=[]
 def start(self,payload):
  package(payload);self.stop();owner=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def send(self,status,body,kind='text/plain; charset=utf-8'):
    body=body.encode('utf8') if isinstance(body,str) else body;self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff');self.end_headers()
    try:self.wfile.write(body)
    except (ConnectionError,OSError):pass
   def route(self):
    with owner.lock:
     path=urllib.parse.urlparse(self.path).path;prefix='/a/'+owner.token+'/'
     return path[len(prefix):] if owner.token and time.time()<owner.expires and path.startswith(prefix) else None
   def do_GET(self):
    route=self.route()
    if route=='':self.send(200,'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>星匣资料互通</title><body style="font:16px/1.9 sans-serif;padding:30px;background:#f0e8d9;color:#302937"><h1>星匣资料互通</h1><p>使用星匣 APK 内的“扫描电脑二维码”可以直接接收和发送资料。</p><a href="download" download="星匣-资料.starcase.json">下载本次资料包</a></body>','text/html; charset=utf-8')
    elif route=='download':
     with owner.lock:self.send(200,owner.payload,'application/json; charset=utf-8')
    else:self.send(404,'互通已结束或二维码无效，请重新开启')
   def do_POST(self):
    if self.route()!='upload':self.send(404,'互通已失效');return
    origin=self.headers.get('Origin');expected='http://'+self.headers.get('Host','')
    if origin and origin!=expected:self.send(403,'请使用扫码打开的页面');return
    try:
     size=int(self.headers.get('Content-Length','0'))
     if not 1<size<=MAX:raise ValueError('资料包大小不正确')
     self.connection.settimeout(25);text=self.rfile.read(size).decode('utf-8-sig');package(text)
     with owner.lock:
      if self.route()!='upload':raise ValueError('互通已结束')
      if owner.incoming:raise ValueError('请先在电脑处理已收到的资料')
      owner.incoming={'id':secrets.token_hex(16),'payload':text,'createdAt':now()}
     self.send(200,'已发送到电脑，等待电脑预览并确认收纳。')
    except (ValueError,UnicodeError,TimeoutError) as ex:self.send(400,str(ex))
  try:server=LANServer(('0.0.0.0',self.port),Handler);server.daemon_threads=True
  except OSError:raise ValueError('互通端口被占用，请关闭旧版星匣互通后重试')
  addresses=[]
  try:
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.connect(('192.0.2.1',9));addresses.append(s.getsockname()[0])
  except OSError:pass
  try:addresses.extend(x[4][0] for x in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET))
  except OSError:pass
  with self.lock:self.server=server;self.token=secrets.token_urlsafe(24);self.payload=payload;self.expires=time.time()+1200;self.addresses=list(dict.fromkeys(a for a in addresses if ipaddress.ip_address(a).is_private and not ipaddress.ip_address(a).is_loopback))
  threading.Thread(target=server.serve_forever,daemon=True).start();self.timer=threading.Timer(1200,self.stop);self.timer.daemon=True;self.timer.start();return self.status()
 def status(self):
  with self.lock:return {'active':bool(self.token and time.time()<self.expires),'expires':self.expires,'urls':['http://'+a+':'+str(self.port)+'/a/'+self.token+'/' for a in self.addresses] if self.token else [],'pending':{'id':self.incoming['id']} if self.incoming else None}
 def stop(self):
  with self.lock:
   if self.timer:self.timer.cancel();self.timer=None
   server=self.server;self.server=None;self.clear()
  if server:server.shutdown();server.server_close()
  return {'ok':True}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=17652);parser.add_argument('--data-dir',type=Path,required=True);a=parser.parse_args()
 root=Path(__file__).resolve().parent;app=root.parent;data_dir=a.data_dir.resolve();data_dir.mkdir(parents=True,exist_ok=True);archive=data_dir/'library.json';backup_dir=data_dir/'backups';backup_dir.mkdir(exist_ok=True);version=json.loads((root/'version.json').read_text(encoding='utf8'))['version'];secret=secrets.token_urlsafe(32);lock=threading.RLock();handoff=Handoff(a.port+1);db={'revision':0,'data':None,'updatedAt':''}
 if archive.exists():
  try:
   saved=json.loads(archive.read_text(encoding='utf8'));valid(saved['data']);db=saved
  except (OSError,ValueError,KeyError) as ex:raise RuntimeError('本机资料文件无法读取，原文件已保留，请使用恢复点：'+str(ex))
 def persist(next_db):
  temp=archive.with_suffix('.tmp')
  with temp.open('w',encoding='utf8',newline='\n') as f:json.dump(next_db,f,ensure_ascii=False,separators=(',',':'));f.flush();os.fsync(f.fileno())
  if archive.exists():shutil.copyfile(archive,backup_dir/('archive-'+str(db['revision']).zfill(10)+'.json'))
  temp.replace(archive)
  for p in sorted(backup_dir.glob('archive-*.json'),reverse=True)[10:]:
   if p.resolve().parent==backup_dir.resolve():p.unlink()
 def save(new,expected):
  nonlocal db
  if expected!=db['revision']:raise RuntimeError('REVISION_CONFLICT')
  next_db={'revision':db['revision']+1,'data':valid(new),'updatedAt':now()};persist(next_db);db=next_db;return {'revision':db['revision'],'updatedAt':db['updatedAt']}
 base='http://localhost:'+str(a.port);allowed={'null',base,'http://127.0.0.1:'+str(a.port)}
 guide={'app':APP,'version':version,'schemaVersion':1,'read':[{'method':'GET','path':'/api/templates','note':'self-described standard templates'},{'method':'GET','path':'/api/schema','note':'portable package JSON Schema'},{'method':'GET','path':'/api/archive','note':'revision and full data; ?since=N omits unchanged data'},{'method':'GET','path':'/api/entry/ID','note':'entry by stable ID'}],'write':[{'method':'POST','path':'/api/entries/upsert','body':{'revision':'last read revision','entries':'array of partial or complete entries'},'note':'retains unknown fields; merges supplied fields; does not delete unrelated entries; review imported rules before marking checked'}],'authentication':'X-Starcase-Token from local connection.json; never print it','dataContract':'Stable IDs, templateId, typed fields, customFields with types, relations.targetId, source.raw verbatim. Blank is unknown, not zero.','limits':{'archiveBytes':MAX,'entries':15000}}
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def origin_ok(self):return not self.headers.get('Origin') or self.headers.get('Origin') in allowed
  def send(self,status,payload,kind='application/json; charset=utf-8'):
   body=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf8');self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');origin=self.headers.get('Origin')
   if origin in allowed:self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
   self.send_header('Access-Control-Allow-Private-Network','true');self.end_headers()
   try:self.wfile.write(body)
   except (ConnectionError,OSError):pass
  def auth(self):
   if not self.origin_ok() or not secrets.compare_digest(self.headers.get('X-Starcase-Token',''),secret):self.send(403,{'error':'本机连接未授权'});return False
   return True
  def do_OPTIONS(self):
   if not self.origin_ok():self.send(403,{'error':'来源不允许'});return
   self.send_response(204);self.send_header('Access-Control-Allow-Origin',self.headers.get('Origin',''));self.send_header('Access-Control-Allow-Headers','Content-Type,X-Starcase-Token');self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS');self.send_header('Access-Control-Allow-Private-Network','true');self.end_headers()
  def do_GET(self):
   u=urllib.parse.urlparse(self.path);p=u.path;q=urllib.parse.parse_qs(u.query)
   if p=='/api/session':
    if not self.origin_ok():self.send(403,{'error':'来源不允许'});return
    self.send(200,{'app':APP,'version':version,'token':secret,'schemaVersion':1});return
   if p in ('/','/index.html','/星匣.html'):self.send(200,(app/'星匣.html').read_bytes(),'text/html; charset=utf-8');return
   if not self.auth():return
   with lock:
    if p=='/api/guide':self.send(200,guide)
    elif p in ('/api/templates','/api/schema'):
     file=app/('标准模板.json' if p=='/api/templates' else '资料包-schema.json')
     self.send(200,file.read_bytes()) if file.exists() else self.send(404,{'error':'模板说明文件尚未放入应用目录'})
    elif p=='/api/archive':
     since=q.get('since',['-1'])[0];self.send(200,{**db,'data':None if since==str(db['revision']) else db['data']})
    elif p.startswith('/api/entry/'):
     entry=next((r for r in (db.get('data') or {}).get('entries',[]) if r['id']==p[11:]),None);self.send(200,{'revision':db['revision'],'entry':entry}) if entry else self.send(404,{'error':'条目不存在'})
    elif p=='/api/handoff/status':self.send(200,handoff.status())
    elif p=='/api/handoff/receive':self.send(200,handoff.incoming or {})
    else:self.send(404,{'error':'接口不存在'})
  def do_POST(self):
   if not self.auth():return
   try:
    size=int(self.headers.get('Content-Length','0'))
    if not 0<size<=MAX:raise ValueError('资料大小超过限制')
    self.connection.settimeout(30);x=json.loads(self.rfile.read(size).decode('utf8'))
    if not isinstance(x,dict):raise ValueError('请求格式不正确')
    p=urllib.parse.urlparse(self.path).path
    with lock:
     if p=='/api/archive':self.send(200,save(x.get('data'),x.get('revision')))
     elif p=='/api/entries/upsert':
      if not db['data']:raise ValueError('先在应用中建立资料库')
      incoming=x.get('entries',[])
      if not isinstance(incoming,list) or len(incoming)>2000:raise ValueError('批量条目不正确')
      doc=json.loads(json.dumps(db['data']));rows={r['id']:r for r in doc['entries']};ids=[]
      for r in incoming:
       if not isinstance(r,dict) or not r.get('id'):raise ValueError('每条更新都需要稳定标识')
       old=rows.get(r['id'],{});merged={**old,**r,'fields':{**old.get('fields',{}),**r.get('fields',{})},'source':{**old.get('source',{}),**r.get('source',{})},'updatedAt':now()};rows[r['id']]=merged;ids.append(r['id'])
      doc['entries']=list(rows.values());doc['updatedAt']=now();self.send(200,{**save(doc,x.get('revision')),'ids':ids})
     elif p=='/api/handoff/start':self.send(200,handoff.start(x.get('payload')))
     elif p=='/api/handoff/stop':self.send(200,handoff.stop())
     elif p=='/api/handoff/ack':
      with handoff.lock:
       if handoff.incoming and handoff.incoming['id']==x.get('id'):handoff.incoming=None
      self.send(200,{'ok':True})
     else:self.send(404,{'error':'接口不存在'})
   except RuntimeError as ex:self.send(409 if str(ex)=='REVISION_CONFLICT' else 500,{'error':'本机资料已有修改，请先读取最新版本' if str(ex)=='REVISION_CONFLICT' else str(ex),'revision':db['revision']})
   except (ValueError,TypeError,KeyError,UnicodeError) as ex:self.send(400,{'error':str(ex)})
   except OSError:self.send(500,{'error':'本机资料无法保存，请检查磁盘空间与写入权限'})
 server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);(data_dir/'connection.json').write_text(json.dumps({'app':APP,'version':version,'url':base,'token':secret,'pid':os.getpid()},ensure_ascii=False),encoding='utf8');print('Starcase local archive: '+base,flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:handoff.stop();server.server_close()
if __name__=='__main__':main()
