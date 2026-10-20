const fs=require('fs'),vm=require('vm'),assert=require('assert/strict'),crypto=require('crypto');
const context=vm.createContext({crypto:crypto.webcrypto,TextEncoder,console,location:{protocol:'file:',hostname:'',origin:'null'}});
vm.runInContext(fs.readFileSync('src/templates.js','utf8')+'\n'+fs.readFileSync('src/model.js','utf8'),context);
vm.runInContext(`
const image=(id,pixel)=>({id,name:id+'.png',mime:'image/png',dataUrl:'data:image/png;base64,'+pixel});
const entry=freshEntry('monster',{title:'Synthetic specimen',coverId:'portrait',attachments:[{mediaId:'trait-image',name:'Trait icon'}]});
const lib={...initialLibrary(),entries:[entry],media:[image('portrait','YQ=='),image('trait-image','Yg=='),image('unattached','Yw==')]};
const chosen=collectionPackage(lib,[entry.id]);
if(chosen.data.media.length!==2||!chosen.data.media.some(m=>m.id==='trait-image'))throw Error('Selected export dropped an attached image');
if(collectionPackage(lib).data.media.length!==3)throw Error('Full backup dropped unreferenced images');
const other={...initialLibrary(),entries:[],media:[image('trait-image','ZA==')]};
const merged=mergePackage(other,chosen,'overwrite'),copied=merged.entries.find(e=>e.id===entry.id);
const icon=merged.media.find(m=>m.id===copied.attachments[0].mediaId);
if(icon.dataUrl!==image('trait-image','Yg==').dataUrl)throw Error('Media ID collision remapped the cover but not attachments');
if(merged.media.find(m=>m.id==='trait-image').dataUrl!==image('trait-image','ZA==').dataUrl)throw Error('Existing media was overwritten');
const roundtrip=parsePackage(JSON.stringify(collectionPackage(merged,[copied.id])));
if(roundtrip.data.media.length!==2||roundtrip.data.entries[0].attachments.length!==1)throw Error('Attachment round trip failed');
`,context);
console.log('Attachment export, full backup, collision remapping and round trip passed with synthetic records.');
