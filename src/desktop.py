"""Hibiki no Yoru desktop: portable executable, persistent local profile, guided portals."""
import argparse, ctypes, hashlib, json, logging, os, shutil, socket, sqlite3, subprocess, sys, tempfile, threading, time, urllib.request, webbrowser, zipfile
from pathlib import Path
from contextlib import closing
import engine

VERSION='0.3.0'
REPO='https://github.com/eddie3333/hibiki-no-yoru'
APP='HibikiNoYoru'
PORTALS={
 'kashie':{'name':'Kashie','url':'https://kashie.ai/studio','role':'Choose footage and finish collection renders'},
 'buffer':{'name':'Buffer','url':'https://publish.buffer.com/','role':'Schedule Instagram, TikTok and YouTube'},
 'metricool':{'name':'Metricool','url':'https://app.metricool.com/','role':'Alternative calendar and performance review'},
 'youtube':{'name':'YouTube Studio','url':'https://studio.youtube.com/','role':'Check your channel and upload directly'},
 'tiktok':{'name':'TikTok Studio','url':'https://www.tiktok.com/tiktokstudio','role':'Check your artist account and upload directly'},
 'instagram':{'name':'Instagram','url':'https://www.instagram.com/','role':'Check your artist account and finish Reels'},
 'github':{'name':'GitHub','url':REPO+'/releases','role':'Download app updates'},
 'lyrc':{'name':'LYRC','url':'https://lyrc.studio/','role':'Reference: lyric presets, smart shuffle, autopilot'},
 'zerodb':{'name':'0dB.studio','url':'https://www.0db.studio/','role':'Reference: batch manager, AI transcription, storage'},
}

LYRIC_PRESETS=['Heartless','Duet','Redline','SZN','Fisheye','Margin','Tiled Wave','Uplift','Ladder House','Full Set','Ticker','Rails','Letterpress','Deep Focus','Relay','Overdrive','Airplay','Quiet','Afterglow','Soft Spoken','Afterimage','Stellar','Brick','Stencil','Fly','VOLTAGE','Wave','Pikachu','Brat','Simple','Bold Pink','Elegant','Statement','Classic']

def settings():
    db=engine.connect();db.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)');db.commit();rows=db.execute('SELECT key,value FROM settings').fetchall();db.close();return {r['key']:json.loads(r['value']) for r in rows}
def save(key,value):
    db=engine.connect();db.execute('CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)');db.execute('INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value)));db.commit();db.close()
def ensure_ledger():
    db=engine.connect()
    db.executescript('''CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY,created TEXT,creative_id TEXT,artist TEXT,song TEXT,version TEXT,source_interval TEXT,collection TEXT,caption TEXT,account TEXT,local_file TEXT,render_task_id TEXT,scheduled_time TEXT,tz TEXT,scheduler_id TEXT,status TEXT,public_url TEXT,observed_time TEXT);
    CREATE TABLE IF NOT EXISTS exports(id TEXT PRIMARY KEY,created TEXT,creative_id TEXT,artist TEXT,song TEXT,style TEXT,file_path TEXT,duration REAL,width INTEGER,height INTEGER,video_stream TEXT,audio_stream TEXT,verified INTEGER,notes TEXT);
    CREATE TABLE IF NOT EXISTS backups(id TEXT PRIMARY KEY,created TEXT,destination TEXT,files TEXT,receipt TEXT,verified INTEGER);''')
    db.commit();db.close()
def seed_profile():
    p=engine.ROOT/'seed/profile.json'
    if not p.exists():return
    seed=json.loads(p.read_text(encoding='utf-8'))
    if settings().get('seed_loaded'):return
    db=engine.connect()
    for r in seed.get('rows',[]):
        db.execute('INSERT OR IGNORE INTO snapshots(post_id,observed,metric_time,song,platform,collection,mapping,published,age_hours,valid,payload) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(r['post_id'],r['observed'],r['metric_time'],r['song'],r['platform'],r['collection'],r['mapping'],r['published'],r['age_hours'],r['valid'],json.dumps({'metrics':r['metrics'],'caption':r['caption'],'source':None,'duration':r.get('duration')})))
    db.commit();db.close()
    save('artist',seed['artist']);save('seed_loaded',True);save('campaign_date',seed['snapshot_date']);save('release_notes_seen',False);save('edition',seed.get('edition','demo'));save('styles',seed.get('styles',engine.APPROVED));save('songs',seed.get('songs',[]));save('repository',seed.get('repository',REPO));save('lyric_presets',LYRIC_PRESETS)
    ensure_ledger()
def campaign():
    s=settings();engine.APPROVED=s.get('styles',engine.APPROVED);base=engine.state();base.pop('repeat_batch',None)
    portals=[{**v,'id':k,'status':s.get('connection:'+k,{}).get('status','not_confirmed'),'confirmed_at':s.get('connection:'+k,{}).get('at')} for k,v in PORTALS.items()]
    for portal in portals:
        if portal['id']=='github':portal['url']=s.get('repository',REPO)+'/releases'
    db=engine.connect();ensure_ledger()
    ledger=[dict(r) for r in db.execute('SELECT * FROM ledger ORDER BY created DESC').fetchall()]
    exports=[dict(r) for r in db.execute('SELECT * FROM exports ORDER BY created DESC').fetchall()]
    backups=[dict(r) for r in db.execute('SELECT * FROM backups ORDER BY created DESC').fetchall()]
    db.close()
    base.update({'version':VERSION,'edition':s.get('edition','demo'),'repository':s.get('repository',REPO),'artist':s.get('artist',{'name':'Your Artist'}),'songs':s.get('songs',[]),'styles':engine.APPROVED,'campaign_date':s.get('campaign_date'),'player':s.get('player'),'portals':portals,'xp':sum(v.get('xp',0) for k,v in s.items() if k.startswith('award:')),'notes':s.get('notes',[]),'engine_ready':False,'ledger':ledger,'exports':exports,'backups':backups,'lyric_presets':s.get('lyric_presets',LYRIC_PRESETS),'competitor_notes':competitor_notes()})
    try:engine.binary('ffmpeg');engine.binary('ffprobe');base['engine_ready']=True
    except ValueError:pass
    return base
def award(key,xp):
    if 'award:'+key not in settings():save('award:'+key,{'xp':xp,'at':engine.now()})
def open_portal(key):
    if key not in PORTALS:raise ValueError('Unknown service.')
    url=settings().get('repository',REPO)+'/releases' if key=='github' else PORTALS[key]['url']
    webbrowser.open(url);save('opened:'+key,engine.now());return {'ok':True,'message':'Sign in on the official site, then return here. Opening it does not verify the signed-in account.'}
def confirm_portal(key):
    if key not in PORTALS:raise ValueError('Unknown service.')
    if not settings().get('opened:'+key):raise ValueError('Open the official sign-in page first.')
    save('connection:'+key,{'status':'confirmed_by_you','at':engine.now()});award('connection:'+key,20)
    return {'ok':True,'message':'Saved your confirmation. Direct posting is not enabled by this check.'}
def export_save(destination):
    destination=Path(destination)
    with tempfile.TemporaryDirectory() as td:
        snapshot=Path(td)/'campaign.sqlite3'
        with closing(sqlite3.connect(engine.DB)) as source:
            with closing(sqlite3.connect(snapshot)) as target:source.backup(target)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(snapshot,'campaign.sqlite3');z.writestr('save.json',json.dumps({'format':'hibiki-no-yoru-save','version':1,'created':engine.now(),'app':VERSION}))
    return {'ok':True,'message':'Campaign saved. This file contains local records and paths, not platform passwords or browser sessions.'}
def import_save(source):
    with zipfile.ZipFile(source) as z:
        names=set(z.namelist())
        if 'save.json' not in names or 'campaign.sqlite3' not in names:raise ValueError('Choose a Hibiki no Yoru campaign save.')
        if json.loads(z.read('save.json')).get('format')!='hibiki-no-yoru-save':raise ValueError('Not a Hibiki no Yoru save.')
        if z.getinfo('campaign.sqlite3').file_size>30_000_000:raise ValueError('Campaign save is too large.')
        raw=z.read('campaign.sqlite3')
    if not raw.startswith(b'SQLite format 3\0'):raise ValueError('Invalid campaign database.')
    candidate=engine.DATA/'incoming.sqlite3';candidate.write_bytes(raw)
    try:
        with closing(sqlite3.connect(candidate)) as c:
            if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Campaign save is damaged.')
            for table in ['snapshots','experiments','jobs']:c.execute('SELECT * FROM '+table+' LIMIT 1')
            edition=json.loads(c.execute("SELECT value FROM settings WHERE key='edition'").fetchone()[0])
            if edition!=engine.EDITION:raise ValueError('This campaign belongs to a different edition.')
        backup=engine.DATA/('before-restore-'+str(int(time.time()))+'.qsave');export_save(backup)
        with closing(sqlite3.connect(candidate)) as c:
            with closing(sqlite3.connect(engine.DB)) as dest:c.backup(dest)
    finally:candidate.unlink(missing_ok=True)
    return {'ok':True,'message':'Campaign restored. Your previous campaign was backed up first. Sign-ins stay on their original computer.'}
def validate_update(source):
    with zipfile.ZipFile(source) as z:
        if not {APP+'.exe','release.json'}.issubset(z.namelist()):raise ValueError('Choose the Windows update ZIP from your Hibiki no Yoru release page.')
        meta=json.loads(z.read('release.json'))
        if z.getinfo(APP+'.exe').file_size>180_000_000:raise ValueError('Update file is too large.')
        raw=z.read(APP+'.exe')
        if not raw.startswith(b'MZ') or hashlib.sha256(raw).hexdigest()!=meta.get('sha256'):raise ValueError('Update checksum did not match. Download it again from your release page.')
        if meta.get('edition')!=engine.EDITION:raise ValueError('Choose an update for this edition.')
        if meta.get('app')!=APP:raise ValueError('Wrong application update.')
    def ver(v):return tuple(int(x) for x in v.split('.'))
    if ver(meta['version'])<=ver(VERSION):raise ValueError('You already have this version or a newer one.')
    return meta,raw
def dialog_action(action):
    import tkinter as tk
    from tkinter import filedialog
    import threading
    result={'value':None,'error':None}
    def worker():
        try:
            root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
            try:
                if action=='save':
                    path=filedialog.asksaveasfilename(parent=root,title='Save your Hibiki no Yoru campaign',defaultextension='.qsave',initialfile='Hibiki-campaign.qsave',filetypes=[('Hibiki no Yoru campaign','*.qsave')]);result['value']=export_save(path) if path else {'cancelled':True}
                elif action=='restore':
                    path=filedialog.askopenfilename(parent=root,title='Open your campaign save',filetypes=[('Hibiki no Yoru campaign','*.qsave')]);result['value']=import_save(path) if path else {'cancelled':True}
                elif action=='update':
                    path=filedialog.askopenfilename(parent=root,title='Choose the Windows update ZIP from Hibiki no Yoru Releases',filetypes=[('Windows update','*.zip')])
                    if not path:result['value']={'cancelled':True}
                    else:
                        meta,raw=validate_update(path)
                        if not getattr(sys,'frozen',False):result['value']={'ok':False,'message':'Update installation is available in the EXE version. Your campaign is preserved.'}
                        else:
                            staged=engine.DATA/'updates'/meta['version'];staged.mkdir(parents=True,exist_ok=True);exe=staged/(APP+'.exe');exe.write_bytes(raw)
                            subprocess.Popen([str(exe),'--apply-update',sys.executable,'--wait-pid',str(os.getpid())],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                            threading.Timer(1.5,lambda:os._exit(0)).start();result['value']={'ok':True,'message':'Installing update and restarting. Your campaign and browser sign-ins are kept.'}
                else:raise ValueError('Unknown action.')
            finally:root.destroy()
        except Exception as e:result['error']=str(e)
    t=threading.Thread(target=worker,daemon=True);t.start();t.join(timeout=120)
    if t.is_alive():return {'cancelled':True,'message':'The file dialog timed out. Please try again.'}
    if result['error']:raise ValueError(result['error'])
    return result['value']

def make_demo():
    ff=engine.binary('ffmpeg');d=engine.DATA/'demo';d.mkdir(exist_ok=True)
    colors=['0x152b4b','0x50345f','0x1c5046']
    for i,color in enumerate(colors):
        p=d/f'scene{i}.mp4'
        if not p.exists():subprocess.run([ff,'-nostdin','-v','error','-f','lavfi','-i',f'color=c={color}:s=360x640:r=30:d=2','-c:v','libx264','-pix_fmt','yuv420p',str(p)],check=True,capture_output=True)
    audio=d/'tone.wav'
    if not audio.exists():subprocess.run([ff,'-nostdin','-v','error','-f','lavfi','-i','sine=frequency=220:duration=6','-af','volume=0.04',str(audio)],check=True,capture_output=True)
    srt=d/'lyrics.srt';srt.write_text('1\n00:00:00,000 --> 00:00:02,000\nBUILD YOUR SOUND\n\n2\n00:00:02,000 --> 00:00:04,000\nCUT TO THE MOMENT\n\n3\n00:00:04,000 --> 00:00:06,000\nMAKE IT YOURS\n')
    return engine.start_render({'audio':str(audio),'audio_start':0,'shots':[{'path':str(d/f'scene{i}.mp4'),'start':0,'duration':2} for i in range(3)],'srt':str(srt)})
def launch_window(url):
    for root in [os.environ.get('PROGRAMFILES(X86)',''),os.environ.get('PROGRAMFILES',''),os.environ.get('LOCALAPPDATA','')]:
        edge=Path(root)/'Microsoft/Edge/Application/msedge.exe'
        if edge.is_file():subprocess.Popen([str(edge),'--app='+url,'--window-size=1280,850']);return
    webbrowser.open(url)
def apply_update(target,pid):
    target=Path(target).resolve();new=Path(sys.executable).resolve()
    if target==new or target.suffix.lower()!='.exe' or not target.is_file():raise ValueError('Invalid update target.')
    if os.name=='nt':
        handle=ctypes.windll.kernel32.OpenProcess(0x00100000,False,int(pid))
        if handle:ctypes.windll.kernel32.WaitForSingleObject(handle,60000);ctypes.windll.kernel32.CloseHandle(handle)
    for attempt in range(15):
        try:shutil.copy2(target,target.with_suffix('.previous.exe'));shutil.copy2(new,target);break
        except PermissionError:time.sleep(1)
    else:raise ValueError('Could not replace the previous app. Your campaign is still safe.')
    subprocess.Popen([str(target)],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
def competitor_notes():
    return [
     {'name':'Kashie','strength':'Collection styles, free previews, credits, render queue','gap':'Closed-source; our core must rebuild collections + render verification','status':'interfacer today'},
     {'name':'LYRC','strength':'30 lyric presets, smart shuffle matching clips to lyrics, autopilot daily posting, artist page, ONCE presaves','gap':'We add independent preset list + planning; no auto-post yet','status':'reference'},
     {'name':'0dB.studio','strength':'Batch manager sends daily videos to TikTok inbox, AI lyric transcription, storage/songs','gap':'We add batch ledger + AI transcription planning','status':'reference'},
    ]
def add_ledger_entry(data):
    ensure_ledger()
    import uuid
    key=uuid.uuid4().hex[:12]
    db=engine.connect()
    db.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,engine.now(),data.get('creative_id'),data.get('artist'),data.get('song'),data.get('version'),data.get('source_interval'),data.get('collection'),data.get('caption'),data.get('account'),data.get('local_file'),data.get('render_task_id'),data.get('scheduled_time'),data.get('tz'),data.get('scheduler_id'),data.get('status','planned'),data.get('public_url'),data.get('observed_time')))
    db.commit();db.close();award('ledger-entry',10);return {'ok':True,'id':key}
def add_export_verify(data):
    ensure_ledger()
    import uuid
    key=uuid.uuid4().hex[:12]
    db=engine.connect()
    db.execute('INSERT INTO exports VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(key,engine.now(),data.get('creative_id'),data.get('artist'),data.get('song'),data.get('style'),data.get('file_path'),data.get('duration'),data.get('width'),data.get('height'),data.get('video_stream'),data.get('audio_stream'),int(bool(data.get('verified'))),data.get('notes')))
    db.commit();db.close();award('export-verify',10);return {'ok':True,'id':key}
def add_backup(data):
    ensure_ledger()
    import uuid
    key=uuid.uuid4().hex[:12]
    db=engine.connect()
    db.execute('INSERT INTO backups VALUES(?,?,?,?,?,?)',(key,engine.now(),data.get('destination'),json.dumps(data.get('files',[])),data.get('receipt'),int(bool(data.get('verified')))))
    db.commit();db.close();award('backup',10);return {'ok':True,'id':key}
class DesktopHandler(engine.Handler):
    def allowed(self):return self.headers.get('Host','').split(':')[0] in ['127.0.0.1','localhost']
    def do_GET(self):
        if not self.allowed():return self.send({'error':'Local access only'},code=403)
        if self.path=='/api/state':return self.send(campaign())
        return super().do_GET()
    def do_POST(self):
        if not self.allowed():return self.send({'error':'Local access only'},code=403)
        if self.headers.get('X-Local-Token')!=engine.TOKEN:return self.send({'error':'Please reopen the app.'},code=403)
        if self.path in ['/api/profile','/api/portal','/api/confirm','/api/note','/api/save','/api/restore','/api/update','/api/demo','/api/prepare','/api/ledger','/api/exportverify','/api/backup']:
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length>16384:raise ValueError('Request too large.')
                data=json.loads(self.rfile.read(length) or '{}')
                if self.path=='/api/profile':save('player',settings().get('artist',{}).get('name','Explorer'));award('begin',25);return self.send({'ok':True})
                if self.path=='/api/prepare':
                    songs=settings().get('songs',[]);song=str(data.get('song',''))
                    if song not in [x['title'] for x in songs]:raise ValueError('Choose one of your songs first.')
                    db=engine.connect();stamp=engine.now()[:10]
                    for i,style in enumerate(settings().get('styles',engine.APPROVED)[:3]):
                        key=hashlib.sha256((stamp+song+style+str(i)).encode()).hexdigest()[:20]
                        db.execute('INSERT OR IGNORE INTO experiments VALUES(?,?,?,?,?,?,?)',(key,engine.now(),song,style,'Fresh opening, consistent audio excerpt and lyric treatment.','planned - not generated or scheduled',str(i+1)))
                    db.commit();db.close();award('plan:'+stamp+song,30);return self.send({'ok':True,'message':'Three-edit run saved. Choose the actual previews in Kashie next. No credits or posts used.'})
                if self.path=='/api/portal':return self.send(open_portal(data['service']))
                if self.path=='/api/confirm':return self.send(confirm_portal(data['service']))
                if self.path=='/api/note':
                    note=str(data.get('text','')).strip()
                    if not 1<=len(note)<=2000:raise ValueError('Write a short update first (up to 2000 characters).')
                    notes=settings().get('notes',[]);notes.append({'id':engine.uuid.uuid4().hex[:8],'text':note,'at':engine.now()});save('notes',notes);award('first-note',10);return self.send({'ok':True,'message':'Added to your improvement journal.'})
                if self.path in ['/api/save','/api/restore','/api/update']:return self.send(dialog_action(self.path.split('/')[-1]))
                if self.path=='/api/demo':return self.send(make_demo())
                if self.path=='/api/ledger':return self.send(add_ledger_entry(data))
                if self.path=='/api/exportverify':return self.send(add_export_verify(data))
                if self.path=='/api/backup':return self.send(add_backup(data))
            except Exception as e:logging.exception('App action failed');return self.send({'error':str(e)},code=400)
        return super().do_POST()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8766 if engine.EDITION=='demo' else 8767);parser.add_argument('--headless',action='store_true');parser.add_argument('--data-dir');parser.add_argument('--healthcheck',action='store_true');parser.add_argument('--apply-update');parser.add_argument('--wait-pid');args=parser.parse_args()
    if args.data_dir:engine.DATA=Path(args.data_dir);engine.DATA.mkdir(parents=True,exist_ok=True);engine.DB=engine.DATA/'campaigns.sqlite3';engine.WORKSPACE=engine.DATA/'workspace'
    logging.basicConfig(filename=str(engine.DATA/'desktop.log'),level=logging.INFO)
    if args.apply_update:return apply_update(args.apply_update,args.wait_pid)
    seed_profile()
    if args.healthcheck:
        (engine.DATA/'healthcheck.json').write_text(json.dumps({'version':VERSION,'seeded':bool(settings().get('seed_loaded')),'profile':settings().get('artist'),'frozen':bool(getattr(sys,'frozen',False))}));return
    url=f'http://127.0.0.1:{args.port}/'
    try:
        with urllib.request.urlopen(url+'api/state',timeout=1) as r:
            existing=json.load(r)
            if existing.get('version')==VERSION and existing.get('edition')==engine.EDITION:
                if not args.headless:launch_window(url)
                return
    except Exception:pass
    server=engine.ThreadingHTTPServer(('127.0.0.1',args.port),DesktopHandler)
    if not args.headless:threading.Timer(.3,lambda:launch_window(url)).start()
    server.serve_forever()
if __name__=='__main__':
    try:main()
    except Exception as e:
        logging.exception('Desktop startup failed')
        if os.name=='nt':ctypes.windll.user32.MessageBoxW(0,str(e),'Hibiki no Yoru - could not start',0x10)
        raise
