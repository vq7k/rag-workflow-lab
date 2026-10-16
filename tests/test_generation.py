"""确定性契约检查，不是模型能力证据。"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rag_lab.generation import execute_cases, summarize_reviews

class GenerationTests(unittest.TestCase):
    def test_conversation_chaining_and_isolation(self):
        calls=[]
        def request(payload):
            calls.append(payload.copy())
            n=len(calls)
            return {'answer':'确定性替身，仅供契约测试','message_id':f'm{n}', 'conversation_id':payload['conversation_id'] or f'c{n}'}, .1
        rows=execute_cases([{'id':'A','turns':['q1','q2']},{'id':'B','turns':['q3']}],request,lambda *args:None)
        self.assertEqual([p['conversation_id'] for p in calls],['','c1',''])
        self.assertEqual([r['status'] for r in rows],['ok']*3)

    def test_failure_kept_and_dependent_turn_skipped(self):
        def request(payload): raise RuntimeError('请求失败')
        rows=execute_cases([{'id':'A','turns':['q1','q2']}],request,lambda *args:None)
        self.assertEqual([r['status'] for r in rows],['failed','skipped'])
        self.assertEqual(len(rows),2)

    def test_incomplete_response_is_not_success(self):
        rows=execute_cases([{'id':'A','turns':['q']}],lambda p:({'answer':'x'},.1),lambda *args:None)
        self.assertEqual(rows[0]['status'],'failed')

    def test_unknown_review_not_counted_as_pass(self):
        rows=[{'case_id':'A','turn':1,'status':'ok'}, {'case_id':'B','turn':1,'status':'failed'}]
        reviews=[{'case_id':'A','turn':'1','overall':'pending'}]
        result=summarize_reviews(rows,reviews)
        self.assertEqual(result['planned_turns'],2)
        self.assertEqual(result['quality_passed'],0)
        self.assertEqual(result['quality_pending'],1)
        self.assertEqual(result['execution_failed_or_skipped'],1)

if __name__=='__main__': unittest.main()
