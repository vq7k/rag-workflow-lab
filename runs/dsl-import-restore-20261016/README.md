# DSL 导入副本与真实恢复验证

2026-10-16 使用当前 Dify 1.13.0 镜像内官方 `AppDslService.import_app`，导入项目留档的 `releases/stack-rag-dev-v1/app.yml`。import_mode 为 yaml-content，指定新的测试应用名，不传 app_id，不覆盖原应用。使用原应用创建者在现有工作空间的管理角色执行，已核对 owner/admin 权限。

## 执行结果

- 导入状态 completed，DSL 版本 0.6.0，无导入错误。
- 副本“算法知识库问答实验-DSL恢复验证-20261016”，app_id：`1701328e-a125-43a7-bae4-ee7dc0461fc5`。
- 通过 `app_model_config.to_dict()` 比较导入配置与原版，差异为空；`check_dependencies` 返回 leaked_dependencies 为空。
- 独立会话向副本应用 API 真实提交 S01，正确回答栈与先入后出；客户端耗时 31.44 秒。
- 按返回 message_id 核对数据库保存消息，确认本次属于副本、模型为 qwen38-ms-8bit:latest、SYSTEM 使用 v1 且有定义来源。
- 本次测试临时创建一个副本 API Key，未保存密钥正文；调用后已撤销，独立查询确认该 Key 记录不存在。

## 文件

`import-result.json` 为官方导入结果；`config-verification.json` 为身份、全量模型配置及依赖核查。`S01-request.json`、`S01-response.json`、`S01-stored-message.json` 保存真实请求体、完整响应与实际保存消息；`call-result.json` 保存耗时和端点；`review.json` 保存人工判断。`temporary-key-*.json` 只保存临时凭据记录 ID 和撤销结果，没有密钥正文。

## 范围与限制

这是当前工作空间内的应用配置恢复，复用既有知识库、索引、模型与插件凭据；不证明 DSL 自带这些资源，不是新服务器或整库灾备恢复。本次直接调用镜像内服务 API，未经过 Nginx 或网页渲染，因此延迟不与原网页端比较，也不算原发布网页的最终验收。

副本保留供用户查看：[编排页](http://localhost/app/1701328e-a125-43a7-bae4-ee7dc0461fc5/configuration)、[副本网页](http://localhost/chat/Fe24IJ9EmtQAkwaf)。网页身份已由导入生成，尚未用浏览器逐项测试；没有自动清理副本。
