from pathlib import Path
import shutil,json,subprocess
R=Path(__file__).resolve().parent.parent
src=R/'src';out=R/'outputs';out.mkdir(exist_ok=True)
html=(src/'index.html').read_text(encoding='utf8')
js='\n'.join((src/name).read_text(encoding='utf8') for name in ['model.js','app.js','native.js','transfer.js'])
for needle,value in [('/* APP_CSS */',(src/'style.css').read_text(encoding='utf8')),('/* APP_TEMPLATES */',(src/'templates.js').read_text(encoding='utf8')),('/* APP_QR */',(src/'vendor/qrcodegen.js').read_text(encoding='utf8')),('/* APP_JS */',js)]:
 assert needle in html;html=html.replace(needle,value)
(out/'星匣.html').write_text(html,encoding='utf8',newline='\n')
shutil.copyfile(src/'vendor/LICENSE-qrcodegen.txt',out/'qrcodegen-LICENSE.txt')
contract={'app':'starcase-archive','schemaVersion':1,'entryKeys':['id','templateId','kind','area','system','title','summary','tags','aliases','projectId','status','favorite','fields','customFields','relations','source','coverId','attachments','createdAt','updatedAt'],'attachmentKeys':['mediaId','name','sourceToken'],'sourceKeys':['kind','title','url','revision','retrievedAt','raw','review'],'customFieldKeys':['id','key','label','type','value'],'relationKeys':['id','targetId','type'],'blank':'Not provided. Never infer zero. Preserve the literal — for explicitly absent values.','rules':['Keep stable IDs across export/import','Retain source.raw verbatim','Never replace a private rule with a guessed original rule','Retain unknown fields','Preserve explicit review/pending status']}
(out/'数据结构说明.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf8')
print('Built offline prototype',len(html.encode('utf8')),'bytes')

subprocess.run(['node',str(R/'tools/export-contract.cjs')],check=True)

contract_dir=R/'schema/v1';contract_dir.mkdir(parents=True,exist_ok=True)
for source,target in [('标准模板.json','templates.json'),('资料包-schema.json','package.schema.json'),('数据结构说明.json','data-contract.json')]:shutil.copyfile(out/source,contract_dir/target)
