import argparse, hashlib, json, pathlib, shutil, subprocess, sys, tempfile, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--profile');args=p.parse_args()
profile=pathlib.Path(args.profile).resolve() if args.profile else ROOT/'seed/profile.json'
seed=json.loads(profile.read_text(encoding='utf-8'));edition=seed['edition'];out=ROOT/'dist'/edition;out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as td:
    stage=pathlib.Path(td);(stage/'seed').mkdir();shutil.copy2(profile,stage/'seed/profile.json')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','HibikiNoYoru','--distpath',str(out),'--workpath',str(stage/'build'),'--specpath',str(stage),'--add-data',str(ROOT/'src/ui.html')+':.','--add-data',str(stage/'seed')+':seed','--add-data',str(ROOT/'scripts')+':scripts',str(ROOT/'src/desktop.py')],check=True)
exe=out/'HibikiNoYoru.exe';sha=hashlib.sha256(exe.read_bytes()).hexdigest()
meta={'app':'HibikiNoYoru','version':'0.3.0','edition':edition,'sha256':sha};(out/'release.json').write_text(json.dumps(meta,indent=2))
(out/'SHA256SUMS.txt').write_text(sha+'  HibikiNoYoru.exe\n')
with zipfile.ZipFile(out/f'HibikiNoYoru-Windows-{edition}-v0.3.0.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ['HibikiNoYoru.exe','release.json','SHA256SUMS.txt']:z.write(out/name,name)
    z.write(ROOT/'README.md','README.md')
print(str(out))
