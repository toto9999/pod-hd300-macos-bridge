import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import settings

class SettingsTests(unittest.TestCase):
    def test_missing_settings_do_not_add_gain(self):
        with tempfile.TemporaryDirectory(dir=settings.ROOT/'.cache') as folder,patch.object(settings,'ROOT',Path(folder)):
            self.assertEqual(settings.load()['gain_db'],0)
    def test_invalid_settings_cannot_create_unbounded_gain(self):
        with tempfile.TemporaryDirectory(dir=settings.ROOT/'.cache') as folder,patch.object(settings,'ROOT',Path(folder)):
            for data in [[],{'gain_db':100},{'gain_db':True},{'gain_db':float('nan')},{'profile':'unknown'}]:
                (Path(folder)/'settings.json').write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    settings.load()
    def test_low_latency_keeps_gain_independent(self):
        with tempfile.TemporaryDirectory(dir=settings.ROOT/'.cache') as folder,patch.object(settings,'ROOT',Path(folder)):
            (Path(folder)/'settings.json').write_text(json.dumps({'profile':'low','gain_db':-3}))
            self.assertEqual(settings.load(),{'profile':'low','gain_db':-3.0,'target':256})

if __name__=='__main__':
    unittest.main()
