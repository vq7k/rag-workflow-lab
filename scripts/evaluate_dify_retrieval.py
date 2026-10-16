"""PyCharm Run：调用本机 Dify API，评测固定四题的向量或混合检索。"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from rag_lab.retrieval import DifyClient, score_question, summarize


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_local_env():
    path = ROOT / '.env'
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or key not in {'DIFY_API_BASE', 'DIFY_API_KEY', 'DIFY_DATASET_ID', 'DIFY_DOCUMENT_ID', 'DIFY_APP_API_KEY'}:
            raise ValueError('.env 仅支持文档中列出的 DIFY_* 键，格式为 KEY=value')
        os.environ.setdefault(key, value.strip().strip('\"\''))


def validate_records(response):
    records = response.get('records')
    if not isinstance(records, list):
        raise ValueError('响应缺少 records 数组')
    for r in records:
        seg = r.get('segment', {})
        if not isinstance(seg.get('position'), int) or not seg.get('document_id') or not isinstance(seg.get('content'), str):
            raise ValueError('返回分段身份或正文缺失')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=['vector', 'hybrid'], default='hybrid')
    parser.add_argument('--semantic-weight', type=float, default=.7)
    args = parser.parse_args()
    if not 0 <= args.semantic_weight <= 1:
        parser.error('semantic-weight 必须在 0 到 1 之间')
    try:
        load_local_env()
        missing = [k for k in ('DIFY_API_KEY', 'DIFY_DATASET_ID', 'DIFY_DOCUMENT_ID') if not os.getenv(k)]
        if missing:
            raise ValueError('缺少配置：' + ', '.join(missing) + '；请参考 .env.example 或在 PyCharm 配置环境变量')
        dataset_id, document_id = str(UUID(os.environ['DIFY_DATASET_ID'])), str(UUID(os.environ['DIFY_DOCUMENT_ID']))
        api_base = os.getenv('DIFY_API_BASE', 'http://localhost/v1')
        client = DifyClient(api_base, os.environ['DIFY_API_KEY'])
        data_path = ROOT / 'data/evaluation/stack-retrieval-v0.json'
        data = json.loads(data_path.read_text(encoding='utf-8'))
        if hashlib.sha256((ROOT / data['source_file']).read_bytes()).hexdigest() != data['source_sha256']:
            raise ValueError('本地导入稿已变更，需重新核对题集与分段标注')
    except (ValueError, OSError) as exc:
        print('启动失败：' + str(exc))
        return 1

    run_dir = ROOT / 'runs' / ('dify-retrieval-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    run_dir.mkdir(parents=True)
    log = (run_dir / 'run.log').open('w', encoding='utf-8')
    def say(text):
        print(text, flush=True)
        log.write(text + '\n')
        log.flush()
    summary = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
               'scope': '真实 Dify 检索；非生成回答或上线验收', 'rows': []}
    rows = summary['rows']
    try:
        say('[1/3] 核对知识库、模型与分段标注')
        metadata, _ = client.request('/datasets/' + dataset_id)
        # 仅读取必要配置，避免将租户、账号等元数据写入共享产物。
        model = metadata.get('embedding_model')
        provider = metadata.get('embedding_model_provider')
        if model != 'bge-m3:latest' or not provider:
            raise ValueError('知识库模型与 BGE-M3 基线不一致，需先核对配置')
        segments_response, _ = client.request(f'/datasets/{dataset_id}/documents/{document_id}/segments?limit=100')
        segments = segments_response.get('data')
        if not isinstance(segments, list) or len(segments) != 6 or segments_response.get('has_more'):
            raise ValueError('预期恰好 6 个分段，请先核对当前文档索引')
        anchors = {1: ['先入后出', '栈顶'], 2: ['stack[-1]', 'stack.pop()', 'len(stack) == 0'], 4: ['扩容', '空间效率', '节点对象']}
        by_position = {s['position']: s for s in segments}
        if len(by_position) != 6:
            raise ValueError('分段 position 重复')
        for position, texts in anchors.items():
            seg = by_position.get(position, {})
            if seg.get('document_id') != document_id or not seg.get('enabled') or seg.get('status') != 'completed' or not all(t in seg.get('content', '') for t in texts):
                raise ValueError(f'分段 {position} 的身份、可用状态或答案锚点不符，停止评分')
        retrieval = {'search_method': 'semantic_search' if args.method == 'vector' else 'hybrid_search',
                     'reranking_enable': args.method == 'hybrid', 'reranking_mode': 'weighted_score',
                     'top_k': 3, 'score_threshold_enabled': False}
        if args.method == 'hybrid':
            retrieval['weights'] = {'vector_setting': {'vector_weight': args.semantic_weight,
                'embedding_provider_name': provider, 'embedding_model_name': model},
                'keyword_setting': {'keyword_weight': round(1 - args.semantic_weight, 6)}}
        write_json(run_dir / 'config.json', {'api_base': api_base, 'dataset_id': dataset_id, 'document_id': document_id,
                   'model': model, 'provider': provider, 'retrieval_model': retrieval,
                   'test_set_version': data['version'], 'test_set_sha256': hashlib.sha256(data_path.read_bytes()).hexdigest(),
                   'source_sha256': data['source_sha256'], 'scoring_contract': 'single-target-position-v1',
                   'prompt_version': None, 'cache_state': 'unknown'})
        write_json(run_dir / 'dataset.json', data)
        write_json(run_dir / 'segments.json', [{'id': s['id'], 'position': s['position'], 'document_id': s['document_id'],
                   'content': s['content'], 'content_sha256': hashlib.sha256(s['content'].encode()).hexdigest()} for s in segments])
        say(f'[2/3] {args.method}，Top K=3，阈值关闭；开始 {len(data["questions"])} 道真实 API 检索')
        for q in data['questions']:
            row = dict(q, status='failed')
            started = time.perf_counter()
            payload = {'query': q['question'], 'retrieval_model': retrieval}
            write_json(run_dir / (q['id'] + '-request.json'), payload)
            try:
                response, elapsed = client.request(f'/datasets/{dataset_id}/retrieve', payload)
                write_json(run_dir / (q['id'] + '-response.json'), response)
                records = validate_records(response)
                # 索引在预检后变化时，禁止继续以旧 position 计算命中。
                for r in records:
                    seg = r['segment']
                    if seg['document_id'] == document_id:
                        snapshot = by_position.get(seg['position'])
                        if not snapshot or seg.get('id') != snapshot['id'] or seg['content'] != snapshot['content']:
                            raise ValueError('检索结果与本轮分段快照不一致')
                row.update(status='ok', latency_s=elapsed, **score_question(q, records, document_id, 3))
                row['ranking'] = [{'rank': i, 'segment_id': r['segment'].get('id'), 'document_id': r['segment']['document_id'],
                                  'position': r['segment']['position'], 'score': r.get('score')} for i, r in enumerate(records, 1)]
                say(f'{q["id"]} | {q["question"]} | 目标排名={row["expected_rank"] if q["expected_segments"] else "无答案观察"} | {elapsed:.3f}s')
                for r in row['ranking']:
                    say(f'  {r["rank"]}. 分段 {r["position"]:02d} | score={r["score"]}')
            except (RuntimeError, ValueError, KeyError, TypeError) as exc:
                row.update(error=str(exc), latency_s=round(time.perf_counter() - started, 4))
                say(q['id'] + ' 请求或校验失败：' + str(exc))
            rows.append(row)
            write_json(run_dir / 'summary.json', summary)
        summary.update(status='completed' if all(r['status'] == 'ok' for r in rows) else 'partial_failure', metrics=summarize(rows))
        metrics = summary['metrics']
        say(f'[3/3] Hit@1={metrics["hit_at_1"]}，Hit@3={metrics["hit_at_3"]}，MRR@3={metrics["mrr_at_3"]}，失败率={metrics["failure_rate"]}')
        say('完成检索与评分，不据此宣称完整 RAG 通过；4 题的延迟分位数仅作观察。')
        return 0 if summary['status'] == 'completed' else 1
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        summary.update(status='failed', error=str(exc))
        say('执行失败：' + str(exc))
        return 1
    finally:
        write_json(run_dir / 'summary.json', summary)
        say('结果目录：' + str(run_dir.relative_to(ROOT)))
        log.close()


if __name__ == '__main__':
    raise SystemExit(main())
