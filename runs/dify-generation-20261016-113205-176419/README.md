# v1 真实 API 生成基线

2026-10-16 执行，label 为 `baseline-v1`，应用为既有“算法知识库问答实验”。四道单轮独立会话，一组两轮同会话，共六次真实 Dify 应用 API 调用。没有更改 Prompt、模型、资料或检索设置，没有重试。

## 文件与证据来源

- `cases.json`：运行前冻结的生成开发题集，历史输出已参与题目整理，非独立验收集。
- `config.json`、`config-verification.json`：原 v1 非凭据快照及当前配置比对，model、pre_prompt、dataset_configs 一致。
- `*-request.json`：应用 API 请求体；不保存密钥或 Authorization 头。
- `*-response.json`：完整应用 API 响应，包含回答、引用候选、用量、消息与会话身份。
- `*-stored-message.json`：按本轮返回 message_id 从本机数据库只读提取的保存消息。核查 app_id 正确、回答与 API 响应一致，包含实际组装的 SYSTEM 和会话消息。不是 Provider 原始 HTTP 请求或完整分布式 Trace。
- `results.json`：每轮调用状态和客户端 blocking API 耗时。
- `review.csv`：Codex 按预期、回答原句、入库原文和实际保存上下文逐项人工复核；未使用评分 LLM。
- `summary.json`：汇总人工标注。接口成功六轮；整体通过两轮，四轮因条件或资料支持问题未通过。

## 口径

`source=pass` 表示回答事实可在本次上下文找到支持；不代表世界知识层面所有适用条件均正确。S02 与 M01 沿用了输入中的 O(1) 简写，条件维度仍 fail，整体亦 fail。S03 则既有上下文未提供的机制补充，也遗漏已提供的限定。

客户端耗时含模型加载、检索、网络及应用处理，不是纯推理或首 Token。缓存和冷热状态未知，不与历史网页耗时作优化对比。当前是一次开发基线，不证明稳定性、独立准确率或正式 IT 系统可用。

复现入口：从项目根目录运行 `scripts/evaluate_dify_generation.py --label baseline-v1 --snapshot runs/generation-baseline-config-v1.json`。它会创建新目录并再次发起真实推理，不覆盖本次记录；本地需已填写应用 Key。
