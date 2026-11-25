import os,sys,tempfile,unittest,json,zipfile
from pathlib import Path
os.environ['XVOK_QUEST_DATA']=tempfile.mkdtemp(prefix='quest-test-')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import desktop,engine
class CampaignTests(unittest.TestCase):
 def setUp(self):
  engine.DB=Path(tempfile.mkdtemp())/'campaigns.sqlite3';engine.DATA=engine.DB.parent;desktop.seed_profile()
 def test_demo_has_no_private_identity(self):
  state=desktop.campaign();self.assertEqual(state['edition'],'demo');self.assertEqual(state['artist']['name'],'Explorer');self.assertTrue(all(p['status']=='not_confirmed' for p in state['portals']));self.assertNotIn('Nun',json.dumps(state));self.assertNotIn('xvok555',json.dumps(state))
 def test_award_is_idempotent(self):
  desktop.award('test',10);desktop.award('test',10);self.assertEqual(desktop.campaign()['xp'],10)
 def test_seed_does_not_duplicate(self):
  before=len(engine.snapshot_rows());desktop.seed_profile();self.assertEqual(before,len(engine.snapshot_rows()))
 def test_save_restores_and_rejects_other_edition(self):
  p=engine.DATA/'save.qsave';desktop.save('player','Test');desktop.export_save(p);desktop.save('player','Changed');desktop.import_save(p);self.assertEqual(desktop.settings()['player'],'Test')
  desktop.save('edition','personal');desktop.export_save(p);desktop.save('edition','demo')
  with self.assertRaises(ValueError):desktop.import_save(p)
 def test_connection_needs_user_confirmation(self):
  with self.assertRaises(ValueError):desktop.confirm_portal('buffer')
 def test_wrong_update_rejected(self):
  p=engine.DATA/'bad.zip'
  with zipfile.ZipFile(p,'w') as z:z.writestr('release.json','{}')
  with self.assertRaises(ValueError):desktop.validate_update(p)
if __name__=='__main__':unittest.main()
