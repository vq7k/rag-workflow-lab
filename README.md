# RAG Workflow Lab · 本地 RAG 开发闭环

基于 **Dify + Ollama + 中文《Hello 算法》** 的 RAG 工程实践仓库，记录从资料处理、向量化、检索、生成评测，到单项优化、回归、恢复发布和反馈回流的完整开发流程。

面向需要开发、评测和维护知识库问答应用的工程师。项目目录沿用 `it-helpdesk-rag`，当前使用公开算法资料验证流程；尚未接入企业 IT 服务台数据。

**主入口：[RAG 应用开发闭环：开发 SOP 与本轮交付](docs/RAG应用开发闭环.md)。** 最新状态见 [PROGRESS](docs/PROGRESS.md)，脚本参数见 [运行说明](scripts/README.md)。

## 当前交付与边界

2026-10-16：八环节开发流程验证完成，用户已人工确认发布页面显示正常。使用真实 Embedding 和生成模型；确定性测试不代替模型能力验证。

| 验证项 | 实测结果 |
|---|---|
| 资料与索引 | 六篇原始资料；仅栈章节 stack-v2 入库，共六段 |
| 混合召回 | 三道有答案开发题：Hit@1、Hit@3、MRR@3 均为 1 |
| v1 生成基线 | 六轮真实调用成功；人工整体通过 2/6 |
| v2 单项 Prompt 回归 | 整体通过 4/6，但 S03 核心要点退化，拒绝候选并恢复 v1 |
| 恢复与网页 | DSL 独立副本真实调用通过；原网页四次核心检查通过，严格质量通过 2/4；用户确认显示正常 |

这是**开发测试版本**。小样本参与过开发调优，不能代表独立验收集或 200–300 篇企业知识库效果。条件遗漏、无依据补充、拒答候选引用、页面体验和慢请求仍有待处理，完整分布式 Trace 尚未建设。恢复到 v1 不代表质量问题已经修复。

## 技术组成

- Dify 1.13.0：知识库索引、混合检索、聊天应用、会话和应用 API。
- Ollama：Embedding 使用 `bge-m3:latest`（1024 维）；生成使用 `qwen38-ms-8bit:latest`。
- Python ≥3.11：标准库实现 API 调用、证据采集、召回评分和人工标注汇总，无运行时第三方依赖。
- 中文《Hello 算法》：固定上游版本及来源许可；本轮仅使用栈章节。

模型 digest、Prompt、生成参数与检索配置见 [v1 配置快照](runs/generation-baseline-config-v1.json)。模型标签不能替代固定版本；生成模型是本次本机已有模型，其他环境需自行准备并重新建立基线。

## 更换模型或部署环境

本实验使用 Dify → 本地 Ollama。迁移到其他服务或环境时，应先核对模型版本、接口与输入处理。更换 Embedding 模型或改变向量生成规则后，重建文档向量与索引；仅改变调用路径时，先验证模型与输出是否一致，再决定是否重建。迁移后重新测基线，不直接沿用历史成绩。见[模型与调用路径迁移要求](docs/RAG应用开发闭环.md#121-模型与调用路径迁移)。

正式验收应使用独立业务题集，规模按覆盖范围与统计精度确定；题目较多时，可采用经人工校准的模型自动评判和分层人工抽检。通过率需同时报告样本数、统计口径与置信区间，不能把本实验的小样本结果推广到实际业务。见[正式验收测试方案](docs/生成回答评测规则.md#10-正式验收测试方案批量评测与自动评判)。自动评判尚未实现，本轮仍为人工标注。

## 本地准备与运行

本仓库不包含 Dify 服务、向量数据库或模型权重。先在本机准备 Dify、Ollama 和上述模型，按 [本地生成模型接入](docs/本地生成模型接入.md) 与 [应用配置记录](docs/Dify问答应用配置与验证.md) 配置。

在项目根目录执行：

```shell
python3 -m venv .venv
cp .env.example .env
```

在本地 `.env` 填写 `DIFY_API_BASE`、知识库与文档 ID，以及两个不同的 Key：

- `DIFY_API_KEY`：知识库 API Key，用于召回评测。
- `DIFY_APP_API_KEY`：应用 API Key，用于生成评测。

脚本当前仅支持本机 Dify。新环境需导入 [stack-v2.md](data/knowledge/hello-algo-v0/import/stack-v2.md)、核查六个分段并校准题集来源标注；应用可参考 [DSL 留档](releases/stack-rag-dev-v1/README.md) 导入并重新绑定知识库、模型与插件依赖。历史 ID 和 localhost 网页链接只用于定位原实验，不能直接复用到新实例。

按所需阶段运行，以下模型相关命令均会产生真实调用：

```shell
# 单题 Embedding 与本地余弦检索演示；不含切块、持久化和生成
.venv/bin/python scripts/demo_vector_search.py

# 批量 Embedding 验证
.venv/bin/python scripts/check_embeddings.py

# Dify 混合召回评测
.venv/bin/python scripts/evaluate_dify_retrieval.py --method hybrid --semantic-weight 0.7

# Dify 生成采集；先人工核对当前应用与快照一致
.venv/bin/python scripts/evaluate_dify_generation.py --label baseline-v1 --snapshot runs/generation-baseline-config-v1.json
```

生成采集只创建待标注表。对照原文、实际输入与回答填写新运行目录的 `review.csv` 后，再汇总：

```shell
.venv/bin/python scripts/summarize_generation.py runs/实际运行目录
```

PyCharm：打开包含 `pyproject.toml` 的项目根目录，解释器选择 `.venv/bin/python`；可直接右键运行采集脚本。汇总脚本需在 Run Configuration 的 Parameters 填写运行目录。详细执行与标注规范见 [生成评测 SOP](docs/生成回答评测规则.md)。

## 开发流程与文档导航

1. **需求与资料范围**：[原始资料、固定来源与许可](data/knowledge/hello-algo-v0/README.md)。
2. **预处理、分块与入库**：[开发流程与验收方法](docs/RAG文档预处理与分块开发流程.md)。
3. **向量化与召回评测**：[BGE-M3 原理与指标](docs/向量检索演示原理.md)、[召回测试与权重实验](docs/召回测试记录.md)。
4. **应用与多轮问答**：[应用配置](docs/Dify问答应用配置与验证.md)、[多轮验证](docs/Dify多轮对话支持与验证.md)。
5. **冻结生成基线**：[评测 SOP](docs/生成回答评测规则.md)、[逐题判断与基线](docs/生成评测记录.md)。
6. **单项优化与回归**：[Prompt 改动、拒绝候选和恢复记录](docs/Prompt单项优化与回归记录.md)。
7. **版本留档与发布验收**：[发布与恢复 SOP](docs/RAG版本发布与反馈回流SOP.md)、[DSL 版本](releases/stack-rag-dev-v1/README.md)。
8. **反馈回流与排障**：[反馈处理链](docs/Prompt单项优化与回归记录.md#8-本轮反馈处理链)、[慢请求人工排查 SOP](docs/Dify慢请求人工排查SOP.md)。

## 目录

```text
├── src/rag_lab/       # 模型调用、检索与生成评测的可复用逻辑
├── scripts/           # CLI / PyCharm 运行入口
├── tests/             # 评分、会话及异常处理的确定性测试
├── data/knowledge/    # 公开原文、来源许可、派生导入稿
├── data/evaluation/   # 固定开发题集与预期
├── docs/              # 工程 SOP、决策记录、drawio 源图及历史截图
├── releases/          # 已选版本的官方 DSL 与导出元信息
├── runs/              # 本轮与历史真实调用、人工标注和结果证据
└── archive/gnome-v0/  # 已停用的英文样本，不参与当前评测
```

`runs/` 保留公开语料实验的可追溯证据，运行时间、会话和消息 ID 用于关联结果；API 响应与保存消息不是完整 Provider HTTP Trace。本轮最终网页无截图，页面显示依据用户人工确认；`docs/screenshots/` 中是此前步骤的截图。早期日志中的机器路径已改为项目相对路径。

## 验证与 GitHub 提交准备

```shell
.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

七项确定性测试覆盖评分、失败计数、会话隔离与续传、不完整响应和断裂多轮处理，不调用模型。真实推理结论分别保存在 `runs/` 和上述评测记录中。

`.env`、虚拟环境、IDE 配置与 Python 缓存已忽略；保留空值的 `.env.example`。提交前查看 `git status --short` 和实际 diff；公开分享不得新增公司文档、真实员工对话、凭据或个人路径。GitHub 仓库：[vq7k/it-helpdesk-rag](https://github.com/vq7k/it-helpdesk-rag)，公开提供代码、工程文档和公开语料实验记录。

## 资料许可与署名

《Hello 算法》来自 [krahets/hello-algo](https://github.com/krahets/hello-algo)，固定版本、逐篇来源和哈希见 [sources.json](data/knowledge/hello-algo-v0/sources.json)，资料采用 [CC BY-NC-SA 4.0](data/knowledge/hello-algo-v0/LICENSE)。栈导入稿包含引用展开、清理和分块调整，改动记录见 [import/README.md](data/knowledge/hello-algo-v0/import/README.md)，派生资料沿用原许可要求。

归档 GNOME 样本的来源见 [sources.json](archive/gnome-v0/knowledge/sources.json)，许可声明保留在[原始 legal.xml](archive/gnome-v0/knowledge/raw/legal.xml)。本仓库自有代码采用 [MIT License](LICENSE)。第三方资料、其派生导入稿及包含这些资料的实验输出继续遵守原许可，不因根目录 MIT 许可证而重新授权；Dify 的许可证另行适用。
