import sys,re,urllib.request,os
# usage: sb.py VIDEO_ID OUTDIR  -> 6 storyboard pages spread across the video + prints duration
UA={'User-Agent':'Mozilla/5.0','Accept-Language':'en-US,en'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read()
vid,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True)
html=get(f'https://www.youtube.com/watch?v={vid}&hl=en').decode('utf8')
ln=re.search(r'"lengthSeconds":"(\d+)"',html)
m=re.search(r'"playerStoryboardSpecRenderer":\{"spec":"([^"]+)"',html)
if not m: print(vid,'no storyboard'); sys.exit()
spec=m.group(1).replace('\\u0026','&').split('|'); base=spec[0]; L=len(spec)-2
w,h,cnt,cols,rows,interval,name,sigh=spec[L+1].split('#')
per=int(cols)*int(rows); pages=(int(cnt)+per-1)//per
u0=base.replace('$L',str(L)).replace('$N',name)
picks=sorted(set(int(i*(pages-1)/5) for i in range(6)))
for p in picks:
    open(f'{out}/{vid}_{p:02d}.jpg','wb').write(get(u0.replace('$M',str(p))+('&sigh='+sigh if sigh else '')))
print(vid,'min',round(int(ln.group(1))/60,1) if ln else '?','pages',pages,picks)
