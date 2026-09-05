import json
import tempfile
import unittest
from pathlib import Path

import epicormic_growth as growth


class EpicormicGrowthTests(unittest.TestCase):
    def make_records(self, count=20):
        records = []
        previous = "0" * 64
        for index in range(count):
            record = growth.make_record(index, previous, growth.DEFAULT_SEED, records)
            records.append(record)
            previous = record["record_hash"]
        return records

    def test_generation_is_deterministic(self):
        self.assertEqual(self.make_records(), self.make_records())

    def test_every_shoot_points_backward(self):
        records = self.make_records(200)
        self.assertTrue(all(record["parent"] < record["id"] for record in records[1:]))

    def test_ledger_verifies_hash_chain_and_canonical_json(self):
        records = self.make_records()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shoots.jsonl"
            path.write_text("".join(growth.canonical(record) + "\n" for record in records), encoding="utf-8")
            self.assertEqual(growth.read_ledger(path), records)

    def test_changed_history_is_rejected(self):
        records = self.make_records()
        records[4]["length"] += 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shoots.jsonl"
            path.write_text("".join(growth.canonical(record) + "\n" for record in records), encoding="utf-8")
            with self.assertRaises(growth.GrowthError):
                growth.read_ledger(path)

    def test_render_is_reproducible_and_complete(self):
        records = self.make_records()
        first = growth.render(records)
        second = growth.render(records)
        self.assertEqual(first, second)
        snapshot = json.loads(first[growth.SNAPSHOT])
        self.assertEqual(snapshot["shoot_count"], 19)
        self.assertEqual(len(snapshot["shoots"]), 20)


if __name__ == "__main__":
    unittest.main()
