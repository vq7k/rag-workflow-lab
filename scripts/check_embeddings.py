"""PyCharm 右键 Run 本文件：真实调用 BGE-M3，展示中文检索结果并保存日志。"""

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rag_lab.embeddings import OllamaClient, cosine_similarity, validate_vectors


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_dataset(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw)
    passages, questions = data["passages"], data["questions"]
    if not passages or not questions:
        raise ValueError("文档片段和问题均不能为空")
    ids = {item["id"] for item in passages}
    if len(ids) != len(passages):
        raise ValueError("片段 ID 重复")
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("问题 ID 重复")
    for item in passages:
        source = (ROOT / item["source_file"]).resolve()
        if not source.is_relative_to(ROOT):
            raise ValueError("来源文件必须在项目内")
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != item["source_sha256"]:
            raise ValueError(f'{item["id"]} 原文版本已变更，请重新核对摘录')
        excerpts = item["excerpts"]
        if not excerpts or not all(text and text in content.decode("utf-8") for text in excerpts):
            raise ValueError(f'{item["id"]} 的摘录不是原文内容')
        if item["text"] != "\n\n".join(excerpts):
            raise ValueError(f'{item["id"]} 的输入与原文摘录不一致')
    for question in questions:
        if not question["question"].strip():
            raise ValueError("问题不能为空")
        if not set(question["expected_ids"]).issubset(ids):
            raise ValueError("预期片段 ID 不存在")
    return data, hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="bge-m3:latest")
    parser.add_argument("--data", type=Path, default=ROOT / "data/evaluation/embedding-smoke-v0.json")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout 必须大于 0")

    run_dir = ROOT / "runs" / ("embedding-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    run_dir.mkdir(parents=True)
    logger = logging.getLogger("embedding_check")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(run_dir / "run.log", encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    started = time.perf_counter()
    summary = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(),
               "model": args.model, "input_contract": "bge-m3-dense-v0", "run_dir": str(run_dir),
               "scope": "中文摘录小样本检索；不是全文 RAG、拒答或生成模型验收"}
    try:
        logger.info("[1/5] 加载数据：%s", args.data)
        data, checksum = load_dataset(args.data)
        summary.update(dataset_version=data["version"], dataset_sha256=checksum)
        write_json(run_dir / "dataset.json", data)
        write_json(run_dir / "config.json", {"model": args.model, "timeout_s": args.timeout,
                   "endpoint": "http://127.0.0.1:11434", "truncate": False,
                   "input_contract": summary["input_contract"], "expected_dimensions": data["dimensions"]})
        passages, questions = data["passages"], data["questions"]
        logger.info("%s；%d 个原文片段，%d 个问题。原文哈希及摘录核对通过。", data["version"], len(passages), len(questions))
        for item in passages:
            logger.info("片段 %s [%s]：%s", item["id"], item["title"], item["text"])
        client = OllamaClient(args.timeout)
        logger.info("[2/5] 检查本机 Ollama 和已安装模型；不会自动下载模型")
        version, _ = client.request("/api/version")
        tags, _ = client.request("/api/tags")
        installed = next((m for m in tags.get("models", []) if args.model in (m.get("name"), m.get("model"))), None)
        if installed is None:
            raise ValueError(f"未找到 {args.model}，请在 Ollama 安装后再运行")
        summary.update(provider="Ollama", provider_version=version, model_metadata=installed)
        logger.info("Ollama=%s；模型=%s；digest=%s", version.get("version"), args.model, installed.get("digest"))
        logger.info("[3/5] POST /api/embed：%d 个文档片段，首次加载模型可能较慢", len(passages))
        doc_response, doc_seconds = client.embed(args.model, [p["text"] for p in passages])
        write_json(run_dir / "raw-documents.json", doc_response)
        doc_vectors = validate_vectors(doc_response, len(passages), data["dimensions"])
        logger.info("文档向量返回：条数=%d，维度=%d，耗时=%.3fs", len(doc_vectors), len(doc_vectors[0]), doc_seconds)
        for q in questions:
            logger.info("问题 %s：%s；预期=%s", q["id"], q["question"], q["expected_ids"] or "无相关依据，不计入命中率")
        logger.info("[4/5] POST /api/embed：%d 个问题", len(questions))
        query_response, query_seconds = client.embed(args.model, [q["question"] for q in questions])
        write_json(run_dir / "raw-queries.json", query_response)
        query_vectors = validate_vectors(query_response, len(questions), data["dimensions"])
        logger.info("问题向量返回：条数=%d，维度=%d，耗时=%.3fs", len(query_vectors), len(query_vectors[0]), query_seconds)
        logger.info("[5/5] 计算余弦相似度，展示 Top-3；分数不是正确概率")
        rows = []
        for question, vector in zip(questions, query_vectors, strict=True):
            ranking = sorted([{"id": p["id"], "title": p["title"],
                               "score": cosine_similarity(vector, dv)}
                              for p, dv in zip(passages, doc_vectors, strict=True)],
                             key=lambda r: r["score"], reverse=True)
            expected = set(question["expected_ids"])
            hit1 = ranking[0]["id"] in expected if expected else None
            hit3 = bool(expected.intersection(r["id"] for r in ranking[:3])) if expected else None
            row = {"id": question["id"], "question": question["question"], "expected_ids": sorted(expected),
                   "hit_at_1": hit1, "hit_at_3": hit3, "ranking": ranking}
            rows.append(row)
            logger.info("%s | %s | Top-1=%s | %s", question["id"], question["question"], ranking[0]["title"],
                        ("命中" if hit1 else "未命中") if expected else "无答案观察题：不能据近邻判定可回答")
            for rank, item in enumerate(ranking[:3], 1):
                logger.info("  %d. %s (%s) cosine=%.4f", rank, item["title"], item["id"], item["score"])
        scored = [r for r in rows if r["expected_ids"]]
        summary.update(status="completed", dimensions=data["dimensions"],
                       document_latency_s=doc_seconds, query_latency_s=query_seconds,
                       scored_questions=len(scored), unanswerable_observations=len(rows) - len(scored),
                       hit_at_1=sum(r["hit_at_1"] for r in scored) / len(scored) if scored else None,
                       hit_at_3=sum(r["hit_at_3"] for r in scored) / len(scored) if scored else None,
                       results=rows)
        logger.info("有答案题 %d 道，Hit@1=%s，Hit@3=%s", len(scored), summary["hit_at_1"], summary["hit_at_3"])
        logger.info("调用与计算完成；不按预设门槛宣称效果通过。未连接 Dify 或生成模型。")
        return 0
    except Exception as exc:
        summary.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        logger.exception("验证失败：%s", exc)
        return 1
    finally:
        summary["total_latency_s"] = round(time.perf_counter() - started, 4)
        write_json(run_dir / "summary.json", summary)
        logger.info("完整日志和原始向量响应保存至：%s", run_dir)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)


if __name__ == "__main__":
    raise SystemExit(main())
