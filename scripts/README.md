# 实验入口

先运行最小演示：**[`demo_vector_search.py`](demo_vector_search.py)**。

PyCharm 右键该文件 → Run，无需参数。先看文件顶部的 `DOCUMENTS` 和 `QUESTION`，然后按控制台的 ①②③④ 理解：原文 → 文档向量 → 问题向量 → 相似度排名。

它只包含 3 段教学短句和 1 个问题；没有自动切块、数据库或生成答案。排名由真实 BGE-M3 计算，不预填结果。日志和原始向量写入 `runs/demo-时间戳/run.log` 和 `trace.json`。本轮只做语法检查，未执行模型调用。

理解演示后，再使用批量验证：[`check_embeddings.py`](check_embeddings.py)。两个入口都只使用 Python 标准库，无需 pip 安装依赖。

## PyCharm 运行

1. 先打开数据 `data/evaluation/embedding-smoke-v0.json`：6 个中文原文片段、8 个有答案问题、2 个无答案观察问题。
2. 查看 `scripts/check_embeddings.py` 的流程，具体 HTTP 调用、向量校验和余弦计算在 `src/rag_lab/embeddings.py`。
3. 确保本机 Ollama 运行且已安装 `bge-m3:latest`。本脚本不启动服务、不下载模型、不接入 Dify。
4. 解释器选项目的 `.venv/bin/python`，右键脚本 → Run。脚本按文件位置定位根目录，不依赖工作目录。
5. Run 控制台会依次展示数据校验、模型 digest、请求、耗时、1024 维向量检查、每题 Top-3 和 Hit@1/Hit@3。

终端等价命令（在项目根目录运行）：

```bash
.venv/bin/python scripts/check_embeddings.py
```

可选参数：`--timeout 180`（每个请求秒数），`--model bge-m3:latest`，`--data /绝对路径/数据.json`。该脚本按 BGE-M3 的输入契约及 1024 维预期设计，不应用于随意比较其他模型。

首次加载模型可能耗时，控制台会先打印正在调用的阶段；不自动重试或掩盖失败。

## 真实日志与结果

每次运行在 `runs/embedding-时间戳/` 生成独立目录：

- `run.log`：与控制台一致的文本日志，包括出错堆栈。
- `dataset.json`、`config.json`：实际输入、预期与请求配置。
- `raw-documents.json`、`raw-queries.json`：模型原始 JSON 响应，包含完整向量；如果请求未成功，相应文件不会生成。
- `summary.json`：模型版本/digest、调用耗时、全量排名与命中统计；失败时记录错误。

这是 6 个原文摘录上的真实向量小样本验证，不是完整 RAG，也不调用生成模型。无答案题依然有最近邻，分数不是答案正确概率；不自动设置拒答阈值。Hit@K 只统计 8 个有答案问题。

本轮仅准备代码与数据，未执行脚本，也没有预填测试成绩。
