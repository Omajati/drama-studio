import sys,re,statistics,glob
def num(s):
  m=re.match(r'([\d.]+)([KM]?)',s.replace(',',''));
  if not m: return None
  v=float(m.group(1)); return v*{'':1,'K':1e3,'M':1e6}[m.group(2)]
for f in sorted(glob.glob('lists/*.txt')):
  L=open(f).read().splitlines(); head=L[0]; rows=[]
  for l in L[1:]:
    p=l.split(' | ')
    if len(p)<3 or 'views' in p[1] and False: pass
    vs=p[1].split(' · ')[0] if len(p)>1 else ''
    if 'ago' in vs or not vs: continue
    v=num(vs); 
    if v is None: continue
    age=p[1].split(' · ')[-1]
    if re.search(r'^\d+ (hour|day)s? ago|^1 week',age): continue  # too fresh
    rows.append((v,p[0],age,p[2]))
  if not rows: print(head,'no data'); continue
  med=statistics.median(r[0] for r in rows)
  print(f"\n{head} | n={len(rows)} median={med:,.0f}")
  for v,i,a,t in sorted(rows,reverse=True):
    tag='TOP' if v>=2*med else ('LOW' if v<=0.5*med else '')
    if tag: print(f"{tag} {v/med:4.1f}x {v:>10,.0f} {i} {a} | {t}")
