"""Ollama 的真实 Embedding 调用与余弦相似度；不包含规则或模拟响应。"""

import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


class OllamaClient:
    def __init__(self, timeout: float = 120):
        self.base_url = "http://127.0.0.1:11434"
        self.timeout = timeout
        # 只访问本机服务，不让 localhost 请求进入系统代理。
        self.opener = build_opener(ProxyHandler({}))

    def request(self, path: str, payload: dict | None = None) -> tuple[dict, float]:
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        request = Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                result = json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:1000]
            raise RuntimeError(f"Ollama {path} 返回 HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"无法调用本机 Ollama {path}: {exc}") from exc
        if not isinstance(result, dict) or result.get("error"):
            raise RuntimeError(f"Ollama {path} 响应异常: {result}")
        return result, round(time.perf_counter() - started, 4)

    def embed(self, model: str, texts: list[str]) -> tuple[dict, float]:
        # BGE-M3 不添加 nomic 的 search_query/search_document 前缀。
        # 禁止静默截断；样本太长时让服务明确报错。
        return self.request("/api/embed", {"model": model, "input": texts, "truncate": False})


def validate_vectors(response: dict, count: int, dimensions: int) -> list[list[float]]:
    vectors = response.get("embeddings")
    if not isinstance(vectors, list) or len(vectors) != count:
        raise ValueError(f"向量条数不符，预期 {count}")
    for index, vector in enumerate(vectors):
        if not isinstance(vector, list) or len(vector) != dimensions:
            raise ValueError(f"第 {index} 个向量维度不符，预期 {dimensions}")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in vector):
            raise ValueError(f"第 {index} 个向量包含非法数值")
        if not any(v != 0 for v in vector):
            raise ValueError(f"第 {index} 个向量为零向量")
    return vectors


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        raise ValueError("余弦相似度要求两个非空向量维度相同")
    left_norm = math.sqrt(math.fsum(v * v for v in left))
    right_norm = math.sqrt(math.fsum(v * v for v in right))
    if not left_norm or not right_norm:
        raise ValueError("不能计算零向量的余弦相似度")
    score = math.fsum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    return max(-1.0, min(1.0, score))
