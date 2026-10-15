# RAG 流程实验

使用《Hello 算法》的中文文档，在本机验证 Embedding → 检索 → Dify 问答 → 评测 → 发布流程。项目目录沿用 `it-helpdesk-rag`，当前样本已从 IT 服务台切换为算法知识；未来可替换数据源。

## 用 PyCharm 打开

1. Open 本项目根目录 `.`，不要只打开 `src`。
2. Python Interpreter 选择现有解释器中的 `.venv/bin/python`。本次创建的环境无第三方依赖，版本见 `.venv/pyvenv.cfg`。
3. `src` 是可复用源码目录；如 IDE 没有自动识别，右键 → Mark Directory as → Sources Root。
4. 先看 [BGE-M3 接入与向量化验证](docs/向量检索演示原理.md)、[当前进度](docs/PROGRESS.md) 和 [样本文档](data/knowledge/hello-algo-v0/README.md)。
5. 先打开 `scripts/demo_vector_search.py` 右键 Run，理解单题演示后再看批量验证；详细步骤见 [运行说明](scripts/README.md)。脚本会真实调用本机 Ollama，是否运行由你决定。

## 目录

```text
it-helpdesk-rag/
├── pyproject.toml                 # Python 项目元数据；当前零依赖
├── .venv/                        # 本地 Python 虚拟环境，不提交
├── src/rag_lab/                  # 后续模型调用、检索和评分的复用代码
├── scripts/                      # 后续可在 PyCharm 运行的实验入口
├── tests/                        # 后续确定性逻辑测试
├── data/
│   ├── knowledge/hello-algo-v0/   # 6 篇中文原文、来源、固定版本、许可
│   └── evaluation/               # 中文 Embedding 开发样本；最终验收集尚未创建
├── runs/                         # 真实调用日志与结果，保留历史记录
├── docs/                         # 环境说明、流程和当前进度
└── archive/gnome-v0/             # 旧英文文档、旧题集及旧操作说明
```

## 下一步

BGE-M3 验证代码和 10 个问题已准备好，由你在 PyCharm 运行。入口为 [check_embeddings.py](scripts/check_embeddings.py)，数据见 [embedding-smoke-v0.json](data/evaluation/embedding-smoke-v0.json)。本轮未调用模型、未生成测试成绩。

运行记录必须区分模型接口可用、检索效果、完整 RAG 效果。真实推理尚未完成的步骤不得标为通过。密钥不写入代码或日志。
