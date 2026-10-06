import unittest

from quantum_backend import Layout, NoiseConfig, measure, run_batch
from entities import Miner, Storage
from strategies import RoundRobinStrategy


class HeadlessModuleTests(unittest.TestCase):
    def test_backend_is_reproducible_and_layout_is_hashable(self):
        layout = Layout(2, 2)
        self.assertEqual(run_batch(layout, 4, NoiseConfig(seed=3), use_aer=False),
                         run_batch(layout, 4, NoiseConfig(seed=3), use_aer=False))
        self.assertIsInstance(hash(layout), int)
        self.assertEqual(len(measure(layout, use_aer=False)), layout.width)
        self.assertTrue(all(len(outcome) == 2 for outcome in measure(layout, use_aer=False)))

    def test_round_trip_entities(self):
        miner, storage = Miner(capacity=3), Storage(capacity=3)
        self.assertEqual(miner.mine(3), 3)
        self.assertEqual(storage.deposit(miner.unload()), 3)
        self.assertEqual(storage.amount, 3)

    def test_round_robin(self):
        strategy = RoundRobinStrategy()
        layout = Layout(2, 2)
        self.assertEqual([strategy.choose(layout) for _ in range(4)], [0, 1, 0, 1])


if __name__ == "__main__":
    unittest.main()
