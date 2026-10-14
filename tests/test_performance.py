import unittest
from unittest.mock import patch

from blackcore_core.performance import NetworkRateSampler, nvidia_gpu_status, process_snapshot


class PerformanceTests(unittest.TestCase):
    def test_network_rate_uses_elapsed_time(self):
        sampler = NetworkRateSampler(clock=lambda: 10.0)
        with patch("blackcore_core.performance.network_counters", return_value={
            "available": True, "bytes_sent": 100, "bytes_received": 200
        }):
            self.assertIsNone(sampler.sample()["sent_bytes_per_sec"])
        with patch("blackcore_core.performance.network_counters", return_value={
            "available": True, "bytes_sent": 300, "bytes_received": 600
        }):
            sampler._clock = lambda: 12.0
            sample = sampler.sample()
        self.assertEqual(sample["sent_bytes_per_sec"], 100)
        self.assertEqual(sample["received_bytes_per_sec"], 200)

    def test_network_counter_reset_does_not_return_negative_rate(self):
        times = iter([1.0, 2.0])
        sampler = NetworkRateSampler(clock=lambda: next(times))
        with patch("blackcore_core.performance.network_counters", side_effect=[
            {"available": True, "bytes_sent": 100, "bytes_received": 100},
            {"available": True, "bytes_sent": 10, "bytes_received": 20},
        ]):
            sampler.sample()
            result = sampler.sample()
        self.assertIsNone(result["sent_bytes_per_sec"])

    def test_process_snapshot_bounds_limit(self):
        with self.assertRaises(ValueError):
            process_snapshot(51)

    def test_gpu_provider_is_best_effort(self):
        with patch("blackcore_core.performance.subprocess.run", side_effect=FileNotFoundError):
            result = nvidia_gpu_status()
        self.assertFalse(result["available"])
        self.assertEqual(result["gpus"], [])


if __name__ == "__main__":
    unittest.main()
