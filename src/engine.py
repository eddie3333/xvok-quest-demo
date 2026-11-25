"""Local Hibiki no Yoru campaign lab. No cloud credentials, uploads, or subscription required."""
import argparse, csv, hashlib, io, json, math, os, re, secrets, shutil, sqlite3, subprocess, threading, uuid, textwrap, sys
from collections import defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

HERE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
ROOT=HERE if getattr(sys,'frozen',False) else HERE.parent
EDITION=json.loads((ROOT/'seed/profile.json').read_text(encoding='utf-8')).get('edition','demo')
DATA=Path(os.environ.get('HIBIKI_NO_YORU_DATA',os.environ.get('XVOK_QUEST_DATA',str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/('HibikiNoYoruDemo' if EDITION=='demo' else 'HibikiNoYoru'))))); DATA.mkdir(parents=True,exist_ok=True)
WORKSPACE=Path(os.environ.get('XVOK_WORKSPACE',str(DATA/'workspace')))
DB=DATA/'campaigns.sqlite3'
APPROVED=['Winter Glow','Night Ride','Pixel Rush','Anime Action','Liminal Rooms']
TOKEN=secrets.token_urlsafe(24)
JOBS={}
def now():return datetime.now(timezone.utc).isoformat()
def date(value):
    try:return datetime.fromisoformat(value.replace('Z','+00:00'))
    except (ValueError,AttributeError):return None
def connect():
    db=sqlite3.connect(DB);db.row_factory=sqlite3.Row
    db.executescript('''CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY,post_id TEXT,observed TEXT,metric_time TEXT,song TEXT,platform TEXT,collection TEXT,mapping TEXT,published TEXT,age_hours REAL,valid INTEGER,payload TEXT,artist_id TEXT,UNIQUE(post_id,metric_time,payload));
    CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY,created TEXT,song TEXT,collection TEXT,hypothesis TEXT,status TEXT,variant TEXT,artist_id TEXT);
    CREATE TABLE IF NOT EXISTS roles(id TEXT PRIMARY KEY,created TEXT,status TEXT,result TEXT,artist_id TEXT);
    CREATE TABLE IF NOT EXISTS artists(id TEXT PRIMARY KEY,name TEXT,handle TEXT,spotify TEXT,instagram TEXT,tiktok TEXT,monthly_listeners INTEGER,budget_promo TEXT,budget_mv TEXT,budget_shortform TEXT,notes TEXT,care_level INTEGER,alignment TEXT,active INTEGER,created TEXT);''')
    return db
def norm(text):return ' '.join((text or '').lower().split())
def catalogue():
    p=WORKSPACE/'outputs/queue/xvok-kashie-batches.json'
    return json.loads(p.read_text(encoding='utf-8-sig')).get('batches',[]) if p.exists() else []
def infer(node):
    cap=norm(node.get('text'));sources=[x.get('source') for x in (node.get('assets') or [])]
    for b in catalogue():
        for c in b['clips']:
            for platform,d in c.get('destinations',{}).items():
                if node['id']==d.get('buffer_post_id') or (c.get('media_url') and c['media_url'] in sources) or (cap and cap==norm(d.get('caption'))):
                    return b.get('song_alias',b.get('song','Unknown')),c['collection'],'local campaign record'
    return 'Unknown','Unmapped','needs campaign mapping'

def import_metrics():
    files=sorted((WORKSPACE/'outputs/queue').glob('artist-performance-*.json'))
    if not files:return 0
    data={'edges':[e for p in files for e in json.loads(p.read_text()).get('edges',[])]};db=connect();count=0
    for e in data.get('edges',[]):
        n=e['node']
        if n.get('status')!='sent':continue
        song,col,evidence=infer(n);published=date(n.get('sentAt'));stamp=date(n.get('metricsUpdatedAt'))
        age=(stamp-published).total_seconds()/3600 if published and stamp else None
        metrics={m['type']:m['value'] for m in (n.get('metrics') or [])}
        asset=(n.get('assets') or [{}])[0]
        payload=json.dumps({'metrics':metrics,'caption':n.get('text'),'source':asset.get('source'),'duration':(asset.get('video') or {}).get('durationMs')},ensure_ascii=False,sort_keys=True)
        db.execute('INSERT OR IGNORE INTO snapshots(post_id,observed,metric_time,song,platform,collection,mapping,published,age_hours,valid,payload) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(n['id'],now(),n.get('metricsUpdatedAt'),song,n['channelService'],col,evidence,n.get('sentAt'),age,int(age is not None and age>=0 and bool(metrics)),payload));count+=1
        db.execute('UPDATE snapshots SET song=?,collection=?,mapping=? WHERE post_id=? AND metric_time IS ? AND payload=?',(song,col,evidence,n['id'],n.get('metricsUpdatedAt'),payload))
    db.commit();db.close();return count
def snapshot_rows():
    db=connect();rows=db.execute('SELECT * FROM snapshots ORDER BY metric_time DESC,id DESC').fetchall();db.close();seen=set();out=[]
    for r in rows:
        if r['post_id'] in seen:continue
        seen.add(r['post_id']);d=dict(r);d.update(json.loads(d.pop('payload')))
        views=d['metrics'].get('views');shares=d['metrics'].get('shares');watch=d['metrics'].get('averageTimeWatched');duration=d.get('duration')
        d['shares_per_1000']=shares/views*1000 if views and shares is not None else None
        d['watch_ratio']=watch/(duration/1000) if duration and watch is not None else None
        out.append(d)
    return out
def coverage(rows):
    result=[]
    for song in sorted({r['song'] for r in rows}):
        for col in APPROVED:
            r=[x for x in rows if x['song']==song and x['collection']==col]
            platforms={p:len([x for x in r if x['platform']==p]) for p in ['tiktok','instagram','youtube']}
            matched={p:{str(h):sum(1 for x in r if x['platform']==p and x['valid'] and x['age_hours'] is not None and abs(x['age_hours']-h)<=6) for h in [24,48,72]} for p in platforms}
            result.append({'song':song,'collection':col,'posts':platforms,'matched_windows':matched,'status':'needs repeats'})
    return result

def state():
    rows=snapshot_rows();db=connect();ex=[dict(r) for r in db.execute('SELECT * FROM experiments ORDER BY created,id')];roles=[dict(r) for r in db.execute('SELECT * FROM roles ORDER BY created DESC')];db.close()
    return {'rows':rows,'coverage':coverage(rows),'experiments':ex,'roles':roles,'token':TOKEN,'notice':'Snapshot ages use the source metric timestamp. Lifetime ranks are provisional, not controlled comparisons. Source metrics can lag; old 24/48/72-hour results cannot be reconstructed from lifetime totals.','updated':max((r['metric_time'] or '' for r in rows),default=''),'source':'Imported Buffer snapshot, 2026-11-24. Manual refresh required; no background connector.'}
def plan():
    return {'ok':False,'message':'Choose a song in the campaign screen to prepare a run.'}

def binary(name):
    found=shutil.which(name)
    if not found and (DATA/'tools'/(name+'.exe')).exists():return str(DATA/'tools'/(name+'.exe'))
    if found:return found
    base=Path(os.environ.get('LOCALAPPDATA',''))/'Microsoft/WinGet/Packages'
    found=next(base.glob('ch.LosslessCut_*/resources/'+name+'.exe'),None)
    if not found:raise ValueError('Install FFmpeg or put '+name+' on PATH.')
    return str(found)
def probe(path):return json.loads(subprocess.check_output([binary('ffprobe'),'-v','error','-show_format','-show_streams','-of','json',str(path)],text=True))
def render(manifest,role_id):
    roledir=DATA/'renders'/role_id;roledir.mkdir(parents=True)
    try:
        audio=Path(manifest['audio']);audio_start=float(manifest.get('audio_start',0));shots=manifest['shots']
        if not audio.is_file() or audio_start<0:raise ValueError('Choose an existing local audio file and a nonnegative start.')
        if not 1<=len(shots)<=24:raise ValueError('Use 1-24 shots.')
        duration=sum(float(s['duration']) for s in shots)
        if not 1<=duration<=60:raise ValueError('Preview duration must be 1-60 seconds.')
        if audio_start+duration>float(probe(audio)['format']['duration'])+0.05:raise ValueError('Audio segment exceeds source duration.')
        parts=[]
        for i,shot in enumerate(shots):
            src=Path(shot['path']);length=float(shot['duration']);start=float(shot.get('start',0))
            if not src.is_file() or start<0 or length<=0:raise ValueError('Invalid shot source, start or length.')
            if start+length>float(probe(src)['format']['duration'])+0.05:raise ValueError('Shot exceeds source duration.')
            target=roledir/f'part-{i:02}.mp4'
            args=[binary('ffmpeg'),'-nostdin','-v','error','-ss',str(start),'-i',str(src),'-t',str(length),'-an','-vf','scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p',str(target)]
            subprocess.run(args,check=True,capture_output=True,timeout=180);parts.append(target)
        (roledir/'cuts.txt').write_text('\n'.join("file '"+p.name+"'" for p in parts))
        # A local SRT is optional; copy to a fixed safe filename for filter escaping.
        vf=[]
        if manifest.get('srt'):
            subs=Path(manifest['srt'])
            if not subs.is_file():raise ValueError('Subtitle file not found.')
            shutil.copyfile(subs,roledir/'lyrics.srt')
            content=subs.read_text(encoding='utf-8-sig').replace('\r','')
            events=[]
            def asstime(s):
                hh,mm,ss,ms=map(int,re.split('[:,.]',s));return f'{hh}:{mm:02}:{ss:02}.{ms//10:02}'
            for block in re.split(r'\n\s*\n',content.strip()):
                lines=block.splitlines();idx=next((i for i,l in enumerate(lines) if '-->' in l),None)
                if idx is None:continue
                times=re.findall(r'\d{2}:\d{2}:\d{2}[,.]\d{3}',lines[idx])
                if len(times)!=2:continue
                text=' '.join(lines[idx+1:]);text=re.sub(r'<[^>]*>','',text).replace('{','(').replace('}',')').replace('\\','/')
                text='\\N'.join(textwrap.wrap(text,width=22))
                events.append('Dialogue: 0,'+asstime(times[0])+','+asstime(times[1])+',Default,,0,0,0,,{\\an5\\pos(360,640)}'+text)
            if not events:raise ValueError('No valid timed subtitle cues found.')
            header='[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\nWrapStyle: 2\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,62,&H00FFFFFF,&H00FFFFFF,&H80000000,&H00000000,0,0,0,0,82,100,0,0,1,1,0,5,60,60,100,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
            (roledir/'lyrics.ass').write_text(header+'\n'.join(events),encoding='utf-8')
            vf=['-vf','ass=lyrics.ass']
        args=[binary('ffmpeg'),'-nostdin','-v','error','-f','concat','-safe','0','-i','cuts.txt','-ss',str(audio_start),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-t',str(duration),*vf,'-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','192k','-movflags','+faststart','preview.mp4']
        subprocess.run(args,cwd=roledir,check=True,capture_output=True,timeout=240)
        result={'file':str(roledir/'preview.mp4'),'duration':duration,'manifest':manifest,'note':'Local preview only; manual cuts, optional approximate lyric typography. No upload or automated beat detection.'}
        (roledir/'manifest.json').write_text(json.dumps(result,indent=2))
        status='complete'
    except Exception as exc:
        detail=exc.stderr.decode(errors='replace')[-1500:] if isinstance(exc,subprocess.CalledProcessError) and exc.stderr else str(exc)
        status='failed';result={'error':detail}
    db=connect();db.execute('UPDATE roles SET status=?,result=? WHERE id=?',(status,json.dumps(result),role_id));db.commit();db.close()
def start_render(manifest):
    role=uuid.uuid4().hex[:12];db=connect();db.execute('INSERT INTO roles VALUES(?,?,?,?)',(role,now(),'rendering','{}'));db.commit();db.close()
    threading.Thread(target=render,args=(manifest,role),daemon=True).start();return {'role_id':role,'status':'rendering'}
class Handler(BaseHTTPRequestHandler):
    def send(self,data,ctype='application/json',code=200):
        content=json.dumps(data,ensure_ascii=False).encode() if ctype=='application/json' else data
        self.send_response(code);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(content)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/':return self.send((HERE/'ui.html').read_bytes(),'text/html; charset=utf-8')
        if path=='/api/state':return self.send(state())
        if path=='/api/export':
            buf=io.StringIO();w=csv.writer(buf);w.writerow(['song','platform','collection','post_id','published','metric_time','age_hours','views','likes','shares','average_watch_seconds','valid'])
            for r in snapshot_rows():w.writerow([r['song'],r['platform'],r['collection'],r['post_id'],r['published'],r['metric_time'],r['age_hours'],r['metrics'].get('views'),r['metrics'].get('reactions'),r['metrics'].get('shares'),r['metrics'].get('averageTimeWatched'),r['valid']])
            return self.send(buf.getvalue().encode(),'text/csv; charset=utf-8')
        if path.startswith('/preview/'):
            key=path.split('/')[-1]
            if not re.fullmatch('[a-f0-9]{12}',key):return self.send({'error':'Invalid ID'},code=400)
            f=DATA/'renders'/key/'preview.mp4'
            if f.is_file():return self.send(f.read_bytes(),'video/mp4')
        return self.send({'error':'Not found'},code=404)
    def do_POST(self):
        if self.headers.get('X-Local-Token')!=TOKEN:return self.send({'error':'Reload the local app first.'},code=403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>65536:raise ValueError('Request too large.')
            data=json.loads(self.rfile.read(length) or '{}')
            if self.path=='/api/import':return self.send({'imported':import_metrics()})
            if self.path=='/api/plan':return self.send(plan())
            if self.path=='/api/render':return self.send(start_render(data),code=202)
            if self.path=='/api/forge-preview':
                preset=DATA/'renderer-test/manifest.json'
                if not preset.is_file():raise ValueError('The local preview kit is not set up yet.')
                return self.send(start_render(json.loads(preset.read_text())),code=202)
            return self.send({'error':'Not found'},code=404)
        except (ValueError,KeyError) as e:return self.send({'error':str(e)},code=400)
    def log_message(self,*args):pass

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--import-only',action='store_true');args=parser.parse_args()
    count=import_metrics()
    if args.import_only:print(json.dumps({'imported':count,'coverage':coverage(snapshot_rows())}));raise SystemExit
    print(f'Hibiki no Yoru local lab: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
