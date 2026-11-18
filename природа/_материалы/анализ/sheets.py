import re,sys,os,subprocess,urllib.request
# usage: sheets.py outdir name regex file1 file2 ...
out,name,rx=sys.argv[1],sys.argv[2],re.compile(sys.argv[3],re.I)
rows=[]
for f in sys.argv[4:]:
    for l in open(f):
        m=re.match(r'(TOP|LOW)\s+([\d.]+)x\s+([\d,]+)\s+(\S{11})\s+.*?\|\s(.*)',l.strip())
        if m and rx.search(m.group(5)): rows.append((m.group(1),float(m.group(2)),m.group(3),m.group(4),m.group(5)))
top=sorted([r for r in rows if r[0]=='TOP'],key=lambda r:-r[1])[:16]
low=sorted([r for r in rows if r[0]=='LOW'],key=lambda r:r[1])[:8]
os.makedirs(out,exist_ok=True)
txt=open(f'{out}/{name}.txt','w')
for kind,sel in (('top',top),('low',low)):
    d=f'{out}/{name}_{kind}'; os.makedirs(d,exist_ok=True)
    for i,r in enumerate(sel):
        p=f'{d}/{i:02d}.jpg'
        if not os.path.exists(p):
            try: urllib.request.urlretrieve(f'https://i.ytimg.com/vi/{r[3]}/mqdefault.jpg',p)
            except Exception as e: print('fail',r[3]); continue
        txt.write(f'{kind} {i:02d} {r[1]}x {r[2]} | {r[4]}\n')
    n=len(sel); cols=4; rws=(n+cols-1)//cols
    if n: subprocess.run(['ffmpeg','-y','-loglevel','error','-i',f'{d}/%02d.jpg','-vf',f'tile={cols}x{rws}:padding=4',f'{out}/{name}_{kind}.jpg'])
txt.close(); print(open(f'{out}/{name}.txt').read())
