"""最小演示：三段资料 + 一个问题 → 真实 Embedding → 相似度排名。

PyCharm 右键 Run 本文件即可。只调用本机 Ollama，不连接 Dify。
资料是依据《Hello 算法》整理的教学短句，不是自动切块结果。
"""

import json
import math
import time
from datetime import datetime
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

# 先看这两项：这就是本次演示的全部输入，可以自行修改问题。
DOCUMENTS = [
    {"title": "栈", "text": "栈遵循先入后出规则，后放入的元素先取出。"},
    {"title": "队列", "text": "队列遵循先入先出规则，先进入的元素先取出。"},
    {"title": "数组", "text": "数组把相同类型的元素存放在连续内存中，可以通过索引访问元素。"},
]
QUESTION = "后放进去的东西先取出来，应该用什么数据结构？"
MODEL = "bge-m3:latest"
URL = "http://127.0.0.1:11434"
ROOT = Path(__file__).resolve().parents[1]


def call_ollama(path, payload=None):
    """真实 HTTP 请求：输入文本，返回模型计算得到的向量，不做模拟。"""
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    request = Request(URL + path, data=body, headers={"Content-Type": "application/json"})
    # 本机请求不经过系统代理。
    with build_opener(ProxyHandler({})).open(request, timeout=120) as response:
        return json.load(response)


def cosine(left, right):
    """方向越接近，余弦相似度越高；不是答案正确概率。"""
    dot = math.fsum(a * b for a, b in zip(left, right, strict=True))
    length = math.sqrt(math.fsum(a * a for a in left) * math.fsum(b * b for b in right))
    if length == 0:
        raise ValueError("模型返回了零向量")
    return dot / length


def check_vectors(response, expected_count):
    vectors = response.get("embeddings", [])
    if len(vectors) != expected_count:
        raise ValueError(f"预期 {expected_count} 个向量，实际 {len(vectors)} 个：{response.get('error', '')}")
    for vector in vectors:
        if len(vector) != 1024 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in vector):
            raise ValueError("BGE-M3 向量维度或数值异常，预期 1024 维有限数值")
    return vectors


def main():
    folder = ROOT / "runs" / ("demo-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    folder.mkdir(parents=True)
    trace = {"status": "running", "model": MODEL, "input_version": "vector-demo-v0",
             "documents": DOCUMENTS, "question": QUESTION, "ranking": None}
    with (folder / "run.log").open("w", encoding="utf-8") as log:
        def show(message=""):
            print(message, flush=True)
            log.write(message + "\n")
            log.flush()

        try:
            show("目标：给一个问题，找出最相关的资料。")
            show("\n① 原始输入：3 段教学短句和 1 个问题")
            for doc in DOCUMENTS:
                show(f"   {doc['title']}：{doc['text']}")
            show(f"   问题：{QUESTION}")
            trace["ollama_version"] = call_ollama("/api/version")
            tags = call_ollama("/api/tags")
            trace["model_metadata"] = next((m for m in tags.get("models", []) if m.get("name") == MODEL), None)
            if trace["model_metadata"] is None:
                raise ValueError(f"本机没有安装 {MODEL}")

            show("\n② 资料向量化：把 3 段文字交给 BGE-M3，等待真实计算……")
            started = time.perf_counter()
            trace["document_response"] = call_ollama("/api/embed", {
                "model": MODEL, "input": [doc["text"] for doc in DOCUMENTS], "truncate": False})
            trace["document_latency_s"] = round(time.perf_counter() - started, 3)
            vectors = check_vectors(trace["document_response"], len(DOCUMENTS))
            for doc, vector in zip(DOCUMENTS, vectors, strict=True):
                show(f"   {doc['title']} → 1024 个数字，前 3 个：{[round(x, 4) for x in vector[:3]]}")
            show("   这 3 个向量先放在 Python 内存里，没有写入向量数据库。")

            show("\n③ 问题向量化：同一个 BGE-M3，把问题也转成 1024 个数字……")
            started = time.perf_counter()
            trace["question_response"] = call_ollama("/api/embed", {
                "model": MODEL, "input": [QUESTION], "truncate": False})
            trace["question_latency_s"] = round(time.perf_counter() - started, 3)
            question_vector = check_vectors(trace["question_response"], 1)[0]
            show(f"   问题向量前 3 个数字：{[round(x, 4) for x in question_vector[:3]]}")

            show("\n④ 逐一比较：问题向量 vs 每个资料向量，再按相似度排序")
            ranking = []
            for doc, vector in zip(DOCUMENTS, vectors, strict=True):
                score = cosine(question_vector, vector)
                ranking.append({**doc, "score": score})
                show(f"   问题 vs {doc['title']}：{score:.4f}")
            ranking.sort(key=lambda item: item["score"], reverse=True)
            trace["ranking"] = ranking
            show("   排名：" + " → ".join(item["title"] for item in ranking))
            show(f"   检索到的第一段资料：{ranking[0]['text']}")
            show(f"\n耗时：资料向量化 {trace['document_latency_s']:.3f}s；问题向量化 {trace['question_latency_s']:.3f}s")
            show("本次结束于找资料；没有自动切块、没有向量数据库，也没有调用聊天模型生成答案。")
            trace["status"] = "completed"
            return 0
        except Exception as exc:
            trace.update(status="failed", error=f"{type(exc).__name__}: {exc}")
            show(f"\n运行失败：{trace['error']}")
            return 1
        finally:
            (folder / "trace.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            show(f"日志及完整向量已保存：{folder}")


if __name__ == "__main__":
    raise SystemExit(main())
