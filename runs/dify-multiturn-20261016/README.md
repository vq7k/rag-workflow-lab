# 多轮问答小样本：multiturn-smoke-v0

2026-10-16，在已发布 Dify 网页开启一个新会话，依次发送两条问题，中间未新建会话、未改配置，使用真实本地模型生成。

- `config.json`：模型 digest、Prompt/知识库版本、测试题、会话 ID 和后台统计。
- `turn1-ui.txt`、`turn2-ui.txt`：网页可访问性文本，后者含同一会话的两轮输出；不是 Provider 原始响应。
- `backend-ui.txt`：同一会话的后台模型、问答、时间与 Token 展示记录；已排除浏览器外壳和账户列表。
- 页面截图与人工结论见[多轮对话支持与验证](../../docs/Dify多轮对话支持与验证.md)。

两轮核心预期满足；未验证复杂指代、话题切换、历史截断或跨会话记忆。原始文本保留 UI 的缩进和格式，不用于生产数据导入。

历史耗时核查追加 `latency-investigation.json`、`plugin-timings.json` 和 `ollama-timing-excerpts.log`。它们来自既有数据库及服务日志，不是新一次推理或完整 Trace；结论与计时包含关系见[慢请求定位](../../docs/Dify多轮对话支持与验证.md#历史慢请求定位2026-10-16)。
