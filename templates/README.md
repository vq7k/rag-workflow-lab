# 可填写模板

这些文件是填写起点，不包含真实测试成绩。先复制到自己的工作目录，再替换全部占位内容；真实调用证据保存在对应 `runs/` 目录。

| 文件 | 填写时机 | 用途 |
| --- | --- | --- |
| [test-cases.json](test-cases.json) | 调用前 | 冻结问题、预期行为、答案要点与来源依据 |
| [review.csv](review.csv) | 调用后 | 对每个实际回答逐轮标注 |
| [release-record.md](release-record.md) | 变更前准备，验证后补全 | 关联版本、评测决定、发布与恢复证据 |

## 题集

`test-cases.json` 沿用现有生成题集结构。所有字段都由维护者填写，不是脚本自动生成的预期答案：

- 顶层 `version`、`purpose`、`annotation_timing` 说明题集版本、用途及是否看过模型输出；`source_file` 使用项目相对路径，`source_sha256` 填实际资料文件哈希。
- `id` 必须唯一；`turns` 的每个字符串是一轮输入，同一题按顺序续传会话，不同题重新建会话。
- `expected_action` 使用 `answer` 或 `refuse`。`required_points` 按语义定义答案要点，多轮题用从 1 开始的 `turn` 指定轮次。
- `required_conditions` 定义必须保留的条件；`conditional_constraints` 定义回答涉及某结论时才需核对的约束。
- `evidence` 保存来源章节和原文；入库后核实 `segment_number`，模板中的 `null` 不是已知分段号。`evidence_id` 引用同题的来源 ID。
- 无答案题填写 `absence_basis` 说明资料范围核查依据，不把最近邻低分等同于没有答案。没有约束的数组清空，不保留占位条目。

**当前生成采集脚本固定读取 `data/evaluation/stack-generation-v0.json`，尚无 `--cases` 参数。** 此模板不能直接作为命令行输入。适配新题集时，需要明确修改该入口读取路径，并核对资料哈希及标注规则；不要覆盖已有基线题集冒充同一版本。模板也不适用于召回脚本，召回题集还需要预期分段与答案锚点。

## 标注表

优先使用采集脚本在本轮目录自动创建的 `review.csv`；这里的 CSV 仅展示相同列结构。题号与轮次必须来自该轮 `results.json`，不能把示例行直接复制进真实标注表。

- `case_id`、`turn`：采集脚本自动填写；每一组题号和轮次只能出现一次。
- `core`、`source`、`conditions`、`refusal`、`multiturn`：人工填写，建议统一为 `pass`、`fail`、`na` 或 `pending`，并依评测规则核对适用维度。汇总脚本目前不校验或统计这些列。
- `overall`：脚本初始填写 `pending`，人工改为 `pass`、`fail` 或保留 `pending`。不得把接口调用成功当作质量通过。
- `reason`、`reviewer`：人工填写依据与评审人；`pass` / `fail` 必须有 `reason`。现有汇总脚本校验依据非空，但不验证评审人，也不自动推导 `overall`。

填写后从项目根目录运行 `python scripts/summarize_generation.py <本轮目录>`。该命令读取本轮 `results.json` 和 `review.csv`，不调用模型；未执行或跳过的轮次不会计入质量通过。详细做法见[生成评测 SOP](../docs/sop/05-生成评测.md)。

## 发布记录

填写实际版本和证据路径；未执行的操作明确写“未执行”，未知项写“未知”。恢复配置成功、真实推理成功和人工页面核查分别留证，不用一项替代其余项。不要在公开记录中写入凭据或内部平台现状。
