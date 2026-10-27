import unittest
from unittest.mock import patch
import bridge

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        bridge.shutdown_requested=False
    def test_transient_failure_then_success(self):
        with patch.object(bridge,'main',side_effect=[1,0]) as attempt, patch.object(bridge.time,'sleep'):
            self.assertEqual(bridge.run_with_recovery(),0)
            self.assertEqual(attempt.call_count,2)
    def test_three_failures_stop_instead_of_busy_loop(self):
        with patch.object(bridge,'main',return_value=1) as attempt, patch.object(bridge.time,'sleep'):
            self.assertEqual(bridge.run_with_recovery(),1)
            self.assertEqual(attempt.call_count,3)
    def test_exception_recovers_without_false_success(self):
        with patch.object(bridge,'main',side_effect=[RuntimeError('USB disconnected'),0]) as attempt, patch.object(bridge.time,'sleep'):
            self.assertEqual(bridge.run_with_recovery(),0)
            self.assertEqual(attempt.call_count,2)
    def test_explicit_stop_never_restarts(self):
        def stopped():
            bridge.shutdown_requested=True
            return 1
        with patch.object(bridge,'main',side_effect=stopped) as attempt, patch.object(bridge.time,'sleep') as sleep:
            self.assertEqual(bridge.run_with_recovery(),1)
            self.assertEqual(attempt.call_count,1)
            sleep.assert_not_called()

if __name__=='__main__':
    unittest.main()
