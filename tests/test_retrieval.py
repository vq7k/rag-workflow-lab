"""评分契约测试：不替代真实 Dify 调用验收。"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rag_lab.retrieval import score_question, summarize


class ScoringTests(unittest.TestCase):
    def test_rank_and_document_identity(self):
        q = {'expected_segments': [2]}
        records = [{'segment': {'document_id': 'other', 'position': 2}},
                   {'segment': {'document_id': 'doc', 'position': 2}}]
        row = score_question(q, records, 'doc', 3)
        self.assertEqual(row['expected_rank'], 2)
        self.assertFalse(row['hit_at_1'])
        self.assertTrue(row['hit_at_3'])
        self.assertEqual(row['reciprocal_rank_at_3'], .5)

    def test_missing_and_unanswerable(self):
        self.assertEqual(score_question({'expected_segments': [2]}, [], 'doc', 3)['reciprocal_rank_at_3'], 0)
        self.assertIsNone(score_question({'expected_segments': []}, [], 'doc', 3)['hit_at_3'])

    def test_failures_remain_in_denominator(self):
        rows = [{'expected_segments': [2], 'status': 'ok', 'hit_at_1': True, 'hit_at_3': True, 'reciprocal_rank_at_3': 1, 'latency_s': .2},
                {'expected_segments': [2], 'status': 'failed', 'latency_s': .3},
                {'expected_segments': [], 'status': 'ok', 'latency_s': .1}]
        result = summarize(rows)
        self.assertEqual(result['hit_at_1'], .5)
        self.assertEqual(result['mrr_at_3'], .5)
        self.assertAlmostEqual(result['failure_rate'], 1 / 3)


if __name__ == '__main__':
    unittest.main()
