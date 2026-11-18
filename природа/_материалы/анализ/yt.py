import sys,re,json,urllib.request
h=sys.argv[1]; tab=sys.argv[2] if len(sys.argv)>2 else 'videos'
req=urllib.request.Request(f'https://www.youtube.com/{h}/{tab}?hl=en&gl=US',headers={'User-Agent':'Mozilla/5.0','Accept-Language':'en-US,en'})
html=urllib.request.urlopen(req,timeout=30).read().decode('utf8')
m=re.search(r'var ytInitialData = (\{.*?\});</script>',html,re.S)
d=json.loads(m.group(1))
out=[]
def texts(o,acc):
  if isinstance(o,dict):
    if 'content' in o and isinstance(o['content'],str): acc.append(o['content'])
    for x in o.values(): texts(x,acc)
  elif isinstance(o,list):
    for x in o: texts(x,acc)
def walk(o):
  if isinstance(o,dict):
    if 'lockupViewModel' in o:
      v=o['lockupViewModel']; md=v.get('metadata',{}).get('lockupMetadataViewModel',{})
      t=md.get('title',{}).get('content','')
      acc=[]; texts(md.get('metadata',{}),acc)
      out.append((v.get('contentId',''),' · '.join(acc),t)); return
    for x in o.values(): walk(x)
  elif isinstance(o,list):
    for x in o: walk(x)
walk(d)
sub=re.search(r'([\d.,]+[KM]?) subscribers',html)
print('#',h,sub.group(1) if sub else '')
for r in out: print(' | '.join(r))
