#!/usr/bin/env python3
"""Explicitly refresh the live Sefaria inventory and German Mandelstamm snapshots."""
import concurrent.futures,hashlib,json,pathlib,subprocess
from urllib.parse import quote
root=pathlib.Path(__file__).resolve().parents[1];out=root/'sources/sefaria';out.mkdir(parents=True,exist_ok=True)
index_raw=subprocess.check_output(['curl','-fsSL','--retry','2','--max-time','60','https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json']);index=json.loads(index_raw);books=[b for b in index['books'] if b['title'].startswith('Mishneh Torah')];titles=sorted(set(b['title'] for b in books))
def get(url):return subprocess.check_output(['curl','-fsSL','--retry','2','--retry-delay','1','--max-time','35',url])
def task(title):
 url='https://www.sefaria.org/api/texts/versions/'+quote(title.replace(' ','_'))
 data=json.loads(get(url));assert isinstance(data,list),(title,data)
 selected=[v for v in data if 'mandelstam' in v.get('versionTitle','').casefold() and 'deepl' not in v.get('versionTitle','').casefold() and v.get('actualLanguage')=='de']
 excluded=[{'title':title,'versionTitle':v['versionTitle'],'reason':'Not the German Mandelstamm edition (machine translation or another actualLanguage)'} for v in data if 'mandelstam' in v.get('versionTitle','').casefold() and v not in selected]
 return title,selected,excluded
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for result in pool.map(task,titles):results.append(result)
selected=[];excluded=[]
for title,vs,ex in results:
 excluded+=ex
 for v in vs:
  matches=[b for b in books if b['title']==title and b['versionTitle']==v['versionTitle']]
  assert len(matches)==1,('Selected live version missing/ambiguous in export index',title,v['versionTitle'])
  b=matches[0];dest=out/(title.replace(' ','_').replace(',','')+'.json');raw=get(b['json_url']);d=json.loads(raw)
  assert d['title']==title and d['versionTitle']==v['versionTitle']
  dest.write_bytes(raw)
  selected.append({'title':title,'file':str(dest.relative_to(root)),'url':b['json_url'],'version_metadata':v,'export_index_entry':b,'sha256':hashlib.sha256(raw).hexdigest()})
manifest={'retrieved':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).date().isoformat(),'index_url':'https://raw.githubusercontent.com/Sefaria/Sefaria-Export/master/books.json','index_sha256':hashlib.sha256(index_raw).hexdigest(),'index_generated_at':index.get('generated_at'),'checked_titles':titles,'selection':'Version title contains Mandelstam, actualLanguage is de, excluding DeepL; all Mishneh Torah titles in export index checked against live version lists.','items':selected,'excluded_versions':excluded}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print('Checked',len(titles),'titles; downloaded',len(selected),'German Mandelstamm editions; excluded',len(excluded))
print('\n'.join(x['title'] for x in selected))
