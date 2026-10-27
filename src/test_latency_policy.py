import unittest
from latency_policy import LatencyPolicy

class PolicyTests(unittest.TestCase):
    def test_isolated_events_do_not_permanently_inflate(self):
        p=LatencyPolicy()
        self.assertEqual(p.update(1,128,128,1),128)
        self.assertEqual(p.update(2,128,128,300),128)
    def test_clustered_underruns_raise_then_decay(self):
        p=LatencyPolicy()
        self.assertEqual(p.update(1,128,128,1),128)
        self.assertEqual(p.update(2,128,128,2),192)
        self.assertEqual(p.update(2,192,128,61),192)
        self.assertEqual(p.update(2,192,128,62),128)
    def test_stable_decrease_never_goes_below_request(self):
        p=LatencyPolicy()
        self.assertEqual(p.update(0,320,256,60),256)
        self.assertEqual(p.update(0,256,256,120),256)
    def test_raise_is_capped(self):
        p=LatencyPolicy()
        self.assertEqual(p.update(5,1024,128,1),1024)

if __name__=='__main__':
    unittest.main()
