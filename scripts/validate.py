#!/usr/bin/env python3
"""Validate union completeness, source priority, hashes and correction history."""
import collections,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read(name):return json.loads((ROOT/name).read_text())
def flat(x,p=()):
 if isinstance(x,str):return {':'.join(map(str,p)):x}
 assert isinstance(x,list)
 out={}
 for i,v in enumerate(x,1):out.update(flat(v,p+(i,)))
 return out
m=read('manifest.json');external=read('sources/sefaria/manifest.json');remote={x['title']:x for x in external['items']};works={w['title']:w for w in m['works']};assert len(works)==len(m['works'])
for name,h in m['exported_sha256'].items():assert digest((ROOT/name).read_bytes())==h,name
for item in external['items']:
 assert digest((ROOT/item['file']).read_bytes())==item['sha256'];assert item['version_metadata']['actualLanguage']=='de';assert 'mandelstam' in item['version_metadata']['versionTitle'].casefold();assert 'deepl' not in item['version_metadata']['versionTitle'].casefold()
assert set(remote)<=set(works)
for title,w in works.items():
 raw=(ROOT/w['file']).read_bytes();d=json.loads(raw);assert d['title']==title and 'mandelstam' in d['versionTitle'].casefold();t=flat(d['text'])
 assert (len(d['text']),len(t),sum(bool(s.strip()) for s in t.values()),sum(s.count('class="footnote"') for s in t.values()))==(w['chapters'],w['segments'],w['nonempty_segments'],w['footnotes'])
 if w['selected_source']=='Safran':assert digest(raw)==m['source_sha256'][w['source']]
 if title in remote:assert w['selected_source']=='Safran'
 for link in w['links']:
  for line in (ROOT/link).read_text().splitlines():
   if line.strip():assert len(line.split('\t'))>=2
for c in read('comparison/safran-sefaria.json'):
 a=flat(read(works[c['title']]['file'])['text']);b=flat(read(c['sefaria_file'])['text'])
 diff=[r for r in a.keys()&b.keys() if a[r]!=b[r]];assert set(diff)=={r['ref'] for r in c['different_segments']}
 assert not [r for r,s in b.items() if s.strip() and not a.get(r,'').strip()]
 for r in c['different_segments']:assert digest(a[r['ref']].encode())==r['safran_sha256'] and digest(b[r['ref']].encode())==r['sefaria_sha256']
r=read('corrections/kings-and-wars.json');w=works[r['book']];raw=(ROOT/w['file']).read_bytes();assert digest(raw)==r['after_sha256'];original=json.loads(raw)
for change in reversed(r['changes']):
 c,v=map(int,change['ref'].split(':'));segment=original['text'][c-1][v-1]
 assert segment.count(change['after'])==1
 original['text'][c-1][v-1]=segment.replace(change['after'],change['before'])
assert digest(json.dumps(original,ensure_ascii=False,separators=(',',':')).encode())==r['before_sha256'],'Correction history must recover original source bytes'
assert {p.relative_to(ROOT).as_posix() for p in (ROOT/'data').glob('*.json')}=={w['file'] for w in works.values()}
print(f'OK: {len(works)} parts, {sum(w["chapters"] for w in works.values())} chapters, {sum(w["nonempty_segments"] for w in works.values())} nonempty halakhot; {len(remote)} Sefaria overlaps all use Safran; {len(r["changes"])} reversible corrections.')
