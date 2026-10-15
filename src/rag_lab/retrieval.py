"""Dify 知识库 API 与单目标分段检索评分；不调用生成模型。"""
import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener


class DifyClient:
    def __init__(self, base_url, api_key, timeout=120):
        parsed = urlsplit(base_url)
        if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('DIFY_API_BASE 必须是无凭据、查询参数的 HTTP(S) URL')
        local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
        if not local and parsed.scheme != 'https':
            raise ValueError('远程 API 必须使用 HTTPS')
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        if not local:
            raise ValueError('本脚本当前仅支持本机 Dify；远程代理接入另行配置，避免密钥发送到误填地址')
        self.opener = build_opener(ProxyHandler({}))

    def request(self, path, payload=None):
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = Request(self.base_url + path, data=body, headers={
            'Authorization': 'Bearer ' + self.api_key, 'Content-Type': 'application/json'})
        started = time.perf_counter()
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                value = json.load(response)
        except HTTPError as exc:
            # 不输出服务端错误正文，避免异常响应回显凭据。
            raise RuntimeError(f'Dify HTTP {exc.code}，请检查 API Key、知识库 ID 或服务日志') from None
        except (URLError, TimeoutError, OSError):
            raise RuntimeError('无法连接本机 Dify 或请求超时') from None
        if not isinstance(value, dict):
            raise ValueError('Dify 响应不是 JSON 对象')
        return value, round(time.perf_counter() - started, 4)


def score_question(question, records, document_id, top_k):
    if top_k != 3:
        raise ValueError('当前评分契约固定 Top K = 3')
    expected = set(question['expected_segments'])
    rank = next((i for i, r in enumerate(records[:top_k], 1)
                 if r['segment']['document_id'] == document_id and r['segment']['position'] in expected), None)
    return {'expected_rank': rank,
            'hit_at_1': rank == 1 if expected else None,
            'hit_at_3': rank is not None if expected else None,
            'reciprocal_rank_at_3': (1 / rank if rank else 0) if expected else None}


def summarize(rows):
    scored = [r for r in rows if r['expected_segments']]
    latencies = sorted(r['latency_s'] for r in rows)
    def mean_metric(key):
        return sum((r.get(key) or 0) if r['status'] == 'ok' else 0 for r in scored) / len(scored) if scored else None
    def percentile(p):
        return latencies[max(0, math.ceil(len(latencies) * p) - 1)] if latencies else None
    return {'questions': len(rows), 'answerable_questions': len(scored),
            'unanswerable_observations': len(rows) - len(scored),
            'hit_at_1': mean_metric('hit_at_1'), 'hit_at_3': mean_metric('hit_at_3'),
            'mrr_at_3': mean_metric('reciprocal_rank_at_3'),
            'failure_rate': sum(r['status'] != 'ok' for r in rows) / len(rows) if rows else None,
            'latency_p50_s': percentile(.5), 'latency_p95_s': percentile(.95),
            'latency_method': 'nearest-rank; includes failed calls; cache/cold-start state unknown'}
