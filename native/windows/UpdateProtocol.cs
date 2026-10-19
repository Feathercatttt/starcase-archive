using System;using System.IO;using System.Text;using System.Net;using System.Collections.Generic;using System.Web.Script.Serialization;using System.Security.Cryptography;using System.Threading;

// This file is compiled into both the application and the independent installer.
internal static class UpdateProtocol {
 internal const string Current="0.1.1", Repo="https://github.com/Feathercatttt/starcase-archive/", ManifestUrl="https://raw.githubusercontent.com/Feathercatttt/starcase-archive/main/updates/stable.json";
 internal static readonly string[] Mirrors={"https://gh-proxy.org/","https://ghfast.top/","https://ghproxy.net/",""};
 internal static JavaScriptSerializer Serializer(){return new JavaScriptSerializer{MaxJsonLength=512*1024};}
 internal static string Text(Dictionary<string,object> x,string k){object v;return x.TryGetValue(k,out v)?Convert.ToString(v):"";}
 internal static Dictionary<string,object> Object(Dictionary<string,object> x,string k){object v;if(!x.TryGetValue(k,out v)||!(v is Dictionary<string,object>))throw new Exception("更新信息缺少 "+k);return (Dictionary<string,object>)v;}
 internal static Version VersionOf(string s){if(!System.Text.RegularExpressions.Regex.IsMatch(s??"",@"^\d{1,4}\.\d{1,4}\.\d{1,4}$"))throw new Exception("更新版本格式无效");return new Version(s);}
 internal static Dictionary<string,object> Verify(string envelope,string platform){
  if(envelope.Length>350000)throw new Exception("更新信息过大");var x=Serializer().Deserialize<Dictionary<string,object>>(envelope);byte[] raw=Convert.FromBase64String(Text(x,"payload")),sig=Convert.FromBase64String(Text(x,"signature"));
  using(var rsa=new RSACryptoServiceProvider()){rsa.PersistKeyInCsp=false;rsa.FromXmlString(UpdateKey.Xml);if(!rsa.VerifyData(raw,CryptoConfig.MapNameToOID("SHA256"),sig))throw new Exception("更新签名不正确，已拒绝此线路");}
  var p=Serializer().Deserialize<Dictionary<string,object>>(new UTF8Encoding(false,true).GetString(raw));
  if(Text(p,"app")!="starcase-archive"||Text(p,"schema")!="1")throw new Exception("不兼容的更新信息");VersionOf(Text(p,"version"));
  var a=Object(p,platform);long size=Convert.ToInt64(a["size"]);if(size<1024||size>128L*1024*1024||!System.Text.RegularExpressions.Regex.IsMatch(Text(a,"sha256"),"^[a-f0-9]{64}$"))throw new Exception("安装包校验信息无效");
  string expected=Repo+"releases/download/v"+Text(p,"version")+"/"+(platform=="windows"?"Starcase-Windows-Update.zip":"Starcase-Android.apk");if(Text(a,"url")!=expected)throw new Exception("安装包地址不属于星匣官方发布");return p;
 }
 internal static string Hash(string path){using(var sha=SHA256.Create())using(var f=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
 internal static void VerifyFile(string path,Dictionary<string,object> a){if(new FileInfo(path).Length!=Convert.ToInt64(a["size"])||Hash(path)!=Text(a,"sha256"))throw new Exception("安装包不完整或校验不通过，请重新下载");}
 internal static string Prefix(string s){s=(s??"").Trim();if(s=="")return "";Uri u;if(s.Length>200||!Uri.TryCreate(s,UriKind.Absolute,out u)||u.Scheme!="https"||u.UserInfo!=""||u.Query!=""||u.Fragment!="")throw new Exception("自定义镜像需填写 HTTPS 地址前缀，不含账号、查询参数或文件地址");return s.TrimEnd('/')+"/";}
 internal static HttpWebResponse Open(string url,CancellationToken token){
  ServicePointManager.SecurityProtocol|=SecurityProtocolType.Tls12;
  for(int i=0;i<6;i++){token.ThrowIfCancellationRequested();Uri uri=new Uri(url);if(uri.Scheme!="https")throw new Exception("更新线路必须使用 HTTPS");var req=(HttpWebRequest)WebRequest.Create(uri);req.UserAgent="Starcase/"+Current;req.Timeout=10000;req.ReadWriteTimeout=12000;req.AllowAutoRedirect=false;req.AutomaticDecompression=DecompressionMethods.GZip|DecompressionMethods.Deflate;
   HttpWebResponse r;using(token.Register(()=>req.Abort())){r=(HttpWebResponse)req.GetResponse();}int code=(int)r.StatusCode;if(code>=300&&code<400){string next=r.Headers["Location"];r.Dispose();url=new Uri(uri,next).AbsoluteUri;continue;}if(code!=200){r.Dispose();throw new Exception("线路返回 HTTP "+code);}return r;
  }throw new Exception("更新线路重定向过多");
 }
 internal static string ReadText(string url,CancellationToken token){using(var r=Open(url,token))using(var input=r.GetResponseStream())using(var bytes=new MemoryStream()){byte[] b=new byte[8192];for(int n;(n=input.Read(b,0,b.Length))>0;){token.ThrowIfCancellationRequested();bytes.Write(b,0,n);if(bytes.Length>350000)throw new Exception("更新信息格式错误");}return new UTF8Encoding(false,true).GetString(bytes.ToArray());}}
 internal static void Download(string url,string path,long size,CancellationToken token,Action<long> progress){
  using(var r=Open(url,token)){if(r.ContentLength>0&&r.ContentLength!=size)throw new Exception("线路返回的安装包大小不正确");using(var input=r.GetResponseStream())using(var output=new FileStream(path,FileMode.Create,FileAccess.Write,FileShare.None)){byte[] b=new byte[65536];long total=0;using(token.Register(()=>{try{r.Close();}catch{}})){for(int n;(n=input.Read(b,0,b.Length))>0;){token.ThrowIfCancellationRequested();total+=n;if(total>size)throw new Exception("安装包超过声明大小");output.Write(b,0,n);progress(total);}token.ThrowIfCancellationRequested();if(total!=size)throw new Exception("安装包下载中断");}}}
 }
}
