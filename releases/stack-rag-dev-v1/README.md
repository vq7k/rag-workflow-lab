# stack-rag-dev-v1 配置留档

状态：已恢复发布原应用、导出配置并完成 S03 单题恢复验证；**DSL 导入副本及单题真实验证已完成，原发布网页四次请求后台核查已完成，用户已于 2026-10-16 人工确认“页面显示正常”**。本版本仅供项目组本机开发测试，不是质量准出或企业 IT 系统正式版本。

- `app.yml`：由当前 Dify 1.13.0 镜像的官方 `AppDslService.export_dsl(include_secret=False)` 导出，不是手写 DSL；只读导出，不修改 Dify 源码或服务配置。
- `export-metadata.json`：导出方式、哈希和验证边界；已检查不包含本地两个 API Key。导出包含工作区知识库绑定及模型插件依赖，迁移时需重新核对。
- Prompt：grounded-rag-v1；模型、生成参数、资料与检索设置见[配置快照](../../runs/generation-baseline-config-v1.json)。
- 原应用 ID：`03b1eb2b-d822-41b0-8d57-91a5e21e3be0`；本机发布网页：`http://localhost/chat/Ftp5iQMApw2UV9JM`。
- 选择依据：[v1 基线](../../runs/dify-generation-20261016-113205-176419/README.md)、[v2 回归及拒绝决定](../../runs/dify-generation-20261016-114324-193879/README.md)、[v1 恢复验证](../../runs/dify-restore-v1-20261016/README.md)。

已知问题：S02、S03、M01 的条件不完整，S03 有无依据补充；拒答仍显示候选来源；慢请求与 UI 体验未解决。v2 虽整体通过数增加，但出现 S03 核心退化，按既定标准拒绝。本次恢复保留了已知问题，不把版本恢复称为质量修复。

DSL 只保存应用配置，不是知识库正文、向量索引、模型文件、数据库或凭据备份。已通过[独立副本导入与真实验证](../../runs/dsl-import-restore-20261016/README.md)，仅证明当前工作空间既有依赖下恢复成功。原发布网页有答案、拒答和两轮四次新请求的后台核查均已完成，见[网页验收](../../runs/published-web-acceptance-20261016/README.md)；用户已于 2026-10-16 人工确认“页面显示正常”。本轮未采集页面截图。
