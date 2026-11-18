import sys,re,json,urllib.request,html
vid=sys.argv[1]
def get(u,data=None,h={}):
    req=urllib.request.Request(u,data=data,headers={'User-Agent':'Mozilla/5.0','Accept-Language':'en-US',**h});return urllib.request.urlopen(req,timeout=30).read().decode('utf8')
body=json.dumps({"context":{"client":{"clientName":"ANDROID","clientVersion":"20.10.38","androidSdkVersion":30,"hl":"en"}},"videoId":vid}).encode()
p=json.loads(get('https://www.youtube.com/youtubei/v1/player',body,{'Content-Type':'application/json','User-Agent':'com.google.android.youtube/20.10.38 (Linux; U; Android 11) gzip'}))
tr=p.get('captions',{}).get('playerCaptionsTracklistRenderer',{}).get('captionTracks',[])
if not tr: print('NO CAPTIONS',p.get('playabilityStatus',{}).get('status')); sys.exit()
t=[x for x in tr if x['languageCode'].startswith('en')] or tr
x=get(t[0]['baseUrl'])
txt=re.findall(r'<(?:text|s)[^>]*>(.*?)</(?:text|s)>',x,re.S)
print(p['videoDetails']['title'],'|',p['videoDetails']['lengthSeconds'],'s')
print(html.unescape(' '.join(html.unescape(s) for s in txt)).replace('\n',' '))
