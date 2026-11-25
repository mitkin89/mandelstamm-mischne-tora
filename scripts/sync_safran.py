#!/usr/bin/env python3
"""Combine Mandelstamm editions; Safran takes precedence for every overlapping title."""
import hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '../Safran').resolve()
if (SOURCE/'app/bundled/manifest.json').exists():SOURCE=SOURCE/'app'
GIT_ROOT=pathlib.Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=SOURCE,text=True).strip())
SOURCE_SUBDIRECTORY=SOURCE.relative_to(GIT_ROOT).as_posix()
inputs={};outputs={}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def write(name,raw):
 p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);outputs[name]=digest(raw)
def copy(name,dest):
 raw=(SOURCE/name).read_bytes();inputs[name]=digest(raw);write(dest,raw);return raw
def flat(x,p=()):
 if isinstance(x,str):return {':'.join(map(str,p)):x}
 assert isinstance(x,list)
 out={}
 for i,v in enumerate(x,1):out.update(flat(v,p+(i,)))
 return out
m=json.loads((SOURCE/'bundled/manifest.json').read_text())
items=[i for i in m['items'] if i['title'].startswith('Mishneh Torah') and 'mandelstam' in i['versionTitle'].casefold()]
assert len({i['title'] for i in items})==len(items),'Ambiguous local editions'
external=json.loads((ROOT/'sources/sefaria/manifest.json').read_text());remote={}
for item in external['items']:
 raw=(ROOT/item['file']).read_bytes();assert digest(raw)==item['sha256'];d=json.loads(raw)
 assert d['versionTitle']==item['version_metadata']['versionTitle'];assert item['version_metadata']['actualLanguage']=='de'
 assert 'deepl' not in d['versionTitle'].casefold();assert d['title'] not in remote
 remote[d['title']]=(item,d,raw)
works=[];comparisons=[]
for item in sorted(items,key=lambda x:x['title']):
 title=item['title'];file='data/'+title.replace(' ','_').replace(',','')+'.json'
 raw=copy('bundled/'+item['rel'],file);d=json.loads(raw);text=flat(d['text']);links=[]
 for p in sorted((SOURCE/'bundled/links').glob('*.tsv')):
  if p.stem==title or p.stem.startswith(title+', '):
   dest='links/'+p.name;copy(str(p.relative_to(SOURCE)),dest);links.append(dest)
 outline='outlines/'+title+'.json'
 if (SOURCE/outline).exists():copy(outline,outline)
 else:outline=None
 w={'title':title,'file':file,'selected_source':'Safran','source':'bundled/'+item['rel'],'source_manifest_entry':item,'text_language':'de','chapters':len(d['text']),'segments':len(text),'nonempty_segments':sum(bool(s.strip()) for s in text.values()),'footnotes':sum(s.count('class="footnote"') for s in text.values()),'links':links,'outline':outline}
 if title in remote:
  ext,rd,rr=remote[title];other=flat(rd['text'])
  differing=[{'ref':ref,'safran_sha256':digest(text[ref].encode()),'sefaria_sha256':digest(other[ref].encode())} for ref in sorted(text.keys()&other.keys(),key=lambda r:tuple(map(int,r.split(':')))) if text[ref]!=other[ref]]
  only_remote=[ref for ref,t in other.items() if t.strip() and not text.get(ref,'').strip()]
  comparisons.append({'title':title,'selected_source':'Safran','sefaria_file':ext['file'],'different_segments':differing,'sefaria_only_nonempty_refs':only_remote,'safran_only_nonempty_refs':[ref for ref,t in text.items() if t.strip() and not other.get(ref,'').strip()]})
  assert not only_remote,('Sefaria has additional text; review before taking a whole Safran book',title,only_remote)
  w['sefaria_snapshot']=ext['file']
 works.append(w)
for title,(item,d,raw) in sorted(remote.items()):
 if any(w['title']==title for w in works):continue
 file='data/'+title.replace(' ','_').replace(',','')+'.json';write(file,raw);text=flat(d['text'])
 works.append({'title':title,'file':file,'selected_source':'Sefaria','source':item['file'],'text_language':'de','chapters':len(d['text']),'segments':len(text),'nonempty_segments':sum(bool(s.strip()) for s in text.values()),'footnotes':sum(s.count('class="footnote"') for s in text.values()),'links':[],'outline':None})
works.sort(key=lambda x:x['title'])
write('comparison/safran-sefaria.json',(json.dumps(comparisons,ensure_ascii=False,indent=2)+'\n').encode())
copy('portraits/mandelstamm.jpg','portraits/mandelstamm.jpg')
copy('tools/mandelstamm/kings-and-wars-corrections.json','corrections/kings-and-wars.json')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()
assert not subprocess.check_output(['git','diff','HEAD','--name-only','--',*inputs],cwd=SOURCE,text=True).strip(),'Commit source edits first'
manifest={'source_repository':'https://github.com/mitkin89/Safran','source_commit':commit,'source_subdirectory':SOURCE_SUBDIRECTORY,'priority':'Safran over Sefaria for overlapping titles; complete-title selection, no silent mixed editions','works':works,'overlap_titles':len(comparisons),'different_segment_pairs':sum(len(c['different_segments']) for c in comparisons),'source_sha256':inputs,'exported_sha256':outputs}
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(len(works),'works;',len(comparisons),'overlaps;',manifest['different_segment_pairs'],'differing segment pairs; all overlaps use Safran.')
