import sys,re,json,urllib.request,urllib.parse,collections
q=sys.argv[1]; hl=sys.argv[2] if len(sys.argv)>2 else 'en'
req=urllib.request.Request('https://www.youtube.com/results?search_query='+urllib.parse.quote(q)+'&hl='+hl,headers={'User-Agent':'Mozilla/5.0','Accept-Language':hl})
html=urllib.request.urlopen(req,timeout=30).read().decode('utf8')
d=json.loads(re.search(r'var ytInitialData = (\{.*?\});</script>',html,re.S).group(1))
res=[]
def walk(o):
  if isinstance(o,dict):
    if 'videoRenderer' in o:
      v=o['videoRenderer']
      t=''.join(r.get('text','') for r in v.get('title',{}).get('runs',[]))
      ch=''.join(r.get('text','') for r in v.get('ownerText',{}).get('runs',[]))
      url=v.get('ownerText',{}).get('runs',[{}])[0].get('navigationEndpoint',{}).get('browseEndpoint',{}).get('canonicalBaseUrl','')
      res.append((v['videoId'],v.get('viewCountText',{}).get('simpleText',''),ch,url,t))
    for x in o.values(): walk(x)
  elif isinstance(o,list):
    for x in o: walk(x)
walk(d)
for r in res: print(' | '.join(r))
