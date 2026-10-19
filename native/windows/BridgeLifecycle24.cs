using System;
using System.Diagnostics;
using System.IO;
using System.Management;

internal static class BridgeLifecycle24 {
 // Called only after /api/session identifies an older Folio service. Never stop another folder's service.
 internal static bool TryStopSameFolder(string baseDir,string port) {
  string server=Path.GetFullPath(Path.Combine(baseDir,"service","server.py"));bool stopped=false;
  try {
   using(var search=new ManagementObjectSearcher("SELECT ProcessId,CommandLine FROM Win32_Process WHERE Name='python.exe' OR Name='pythonw.exe'"))
   using(var rows=search.Get()) foreach(ManagementObject row in rows) {
    string command=Convert.ToString(row["CommandLine"]);
    if(command.IndexOf("\""+server+"\"",StringComparison.OrdinalIgnoreCase)<0||command.IndexOf("--port "+port,StringComparison.OrdinalIgnoreCase)<0)continue;
    int id=Convert.ToInt32(row["ProcessId"]);using(var process=Process.GetProcessById(id)){process.Kill();process.WaitForExit(5000);stopped=true;}
   }
  }catch{return false;}
  return stopped;
 }
}
