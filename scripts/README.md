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


## Dify 召回自动评分

运行入口：[evaluate_dify_retrieval.py](evaluate_dify_retrieval.py)。PyCharm 中右键该文件 → Run，默认执行混合检索（语义 0.7、关键词 0.3），Top K 固定 3，阈值关闭；不会修改知识库持久配置、创建应用或调用生成模型。调用会在 Dify 留下查询记录，也可能增加分段命中次数。

密钥入口与本地配置截图说明见 [API 密钥与本地配置记录](../docs/召回测试记录.md#api-密钥与本地配置记录2026-10-15)。

1. 在 Dify 顶部“知识库”列表 → 右上角“服务 API” → “API 密钥”中创建并复制知识库 API Key。当前版本单个知识库左下角“访问 API”只显示服务开关和文档链接，不是密钥管理入口。它与模型供应商 Key、应用 API Key 不同，不要发到聊天或提交 Git。
2. 在本地 `.env` 填写 Key；本机的知识库与文档 ID 已准备。其他机器复制根目录 `.env.example` 为 `.env` 并填写四项，ID 从各自知识库与文档页面 URL 获取。也可在 PyCharm 的 Run Configuration → Environment variables 设置；环境变量优先于文件。
3. 右键 Run 默认运行混合检索。测试向量检索时，在该 Run Configuration 的 Parameters 填 `--method vector`；混合权重实验例如 `--method hybrid --semantic-weight 0.5`。当前四题仅为开发样本。
4. 控制台显示三个阶段和每题排名，完整产物写入 `runs/dify-retrieval-时间戳/`：`config.json`、题集快照、分段快照、每题 request/response、`run.log`、`summary.json`。这些文件不包含 Authorization 请求头。

终端命令（从项目根目录执行，密钥由本地配置读取）：

```shell
.venv/bin/python scripts/evaluate_dify_retrieval.py --method vector
.venv/bin/python scripts/evaluate_dify_retrieval.py --method hybrid
```

模型和知识库信息通过 API 核对；本地导入稿哈希需与题集一致，远端需为 6 块且目标段启用、完成索引、包含预标注答案锚点。每次保存远端分段正文和哈希，检索期间目标文档的结果必须与快照一致，防止把其他文档的同编号段当成命中。当前仅检查答案锚点及分段身份，不声称本地文件哈希能够证明远端全文与本地完全一致；重分块或更换语料后必须重新核对标注。

Hit@1、Hit@3、MRR@3 只统计三道有答案题；无答案题仅观察。请求或结果校验失败记入失败率，有答案失败题按未命中计，不从分母排除。P50/P95 是客户端端到端耗时，包含失败请求；四题不足以代表性能，缓存和冷启动未知，脚本不能证明每次请求都重新执行 Embedding 推理。

首次运行分别与 [手工基线](../docs/召回测试记录.md) 对照：向量预期目标排名 1、2、1；混合预期 1、1、1。对比实际分段与排名，分数以 API 原始值保存，页面仅显示两位小数；若不一致先检查输入、配置和索引，不修改预期答案追随输出。脚本不会把与旧结果不同自动判为程序错误，也不以该小样本作为上线验收。

只访问本机 HTTP(S) 地址，localhost 绕过系统代理；当前不支持远程 Dify。`.env` 为简单 `KEY=value` 格式，不执行变量替换或 shell 命令，不依赖第三方包。代码不打印密钥；原始检索响应包含知识正文，分享前应核对资料范围，本项目当前语料为公开资料。

## Dify 生成回答采集与人工评测

PyCharm 运行 `evaluate_dify_generation.py`，前置条件与逐项 SOP 见 [生成评测开发 SOP](../docs/生成回答评测规则.md#9-本项目-api-执行入口)。该脚本真实调用应用，保存响应并创建待标注表；`summarize_generation.py` 汇总已填写标注，不自动判断语义。当前入口已准备，首次真实 API 基线已完成，记录见 [生成评测记录](../docs/生成评测记录.md)。
