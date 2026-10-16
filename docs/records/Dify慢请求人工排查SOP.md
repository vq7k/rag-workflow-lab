# Dify 慢请求人工排查 SOP

> 实验记录：保留本轮操作、观察与结果，不作为通用操作入口。通用步骤见 [开发 SOP](../sop/README.md)。

适用人员：RAG 应用开发与运维工程师。当前验证环境：Dify 1.13.0、Docker Compose、本机 Ollama。

目标：从一条慢问答定位主要耗时所在层，并留下可复核证据。本流程先查历史数据；没有必要时不重跑、不调整模型或配置。

## 1. 从页面锁定一条请求

在应用后台进入“日志与标注”，选择慢对话，记录：

- 应用 ID、conversation ID、问题原文、对应轮次。
- 记录时间、后台耗时、模型名称、Token 展示值。
- 是否成功生成、是否流式、是否存在重试。

同一个 conversation ID 可以有多条消息，不能把整段对话当成一次请求。下一步查询 message ID，后续证据尽量关联到消息。

本次样例：conversation ID 为 `b21621d6-ada9-4a7b-b567-8ef5301e3ae4`，两条问题分别为“栈是什么？”和“它有哪些常用操作？”。

**完成条件**：明确是哪一轮慢，而不是只知道“这个应用慢”。

## 2. 查询消息级记录，统一时区

在终端进入 **Dify checkout 的 `docker/` 目录**。以下命令都在该目录执行，项目路径不固定。

先检查服务状态：

```shell
docker compose ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'
```

再执行只读查询。复查本次问题可直接使用下列 ID；排查其他问题时替换 `conversation_id`：

```shell
docker compose exec -T db_postgres psql -U postgres -d dify \
  -v conversation_id='b21621d6-ada9-4a7b-b567-8ef5301e3ae4' <<'SQL'
SELECT id AS message_id,
       created_at AS created_at_utc,
       message_tokens AS input_tokens,
       answer_tokens AS output_tokens,
       provider_response_latency AS pipeline_seconds
FROM messages
WHERE conversation_id = :'conversation_id'
ORDER BY created_at;
SQL
```

`db_postgres`、`postgres`、`dify` 是本机部署的服务名、数据库用户和库名；其他部署按实际值调整，不在文档或截图中填写密码。

结果判读：

- 本机消息表时间为 UTC；北京时间 10:04:13 对应 02:04:13 UTC。
- 输入与输出 Token 已拆分；后台显示的是两者合计。
- `provider_response_latency` 在当前实现中是任务 Pipeline 的计时间隔，不能按字段名直接当作纯模型推理耗时。
- `created_at` 用于确定排查窗口，不等于精确的 HTTP 请求起点。

本次应查到两条消息：`9375cab6-7a27-4b49-8e6a-ab16b5af032c` 为 88.00 秒，`f0ffec94-65de-43c4-92d1-c6a13d98576d` 为 68.26 秒。

**完成条件**：得到 message ID、时间窗口、输入输出 Token 和总计时；避免把不同时区的日志错配。

## 3. 查看插件日志，找主要耗时调用

本例覆盖两轮请求的窗口为 02:04:00–02:07:30 UTC。查其他请求时，窗口应包含请求开始前的一小段时间和预计结束时间。

```shell
docker compose logs --no-color \
  --since '2026-10-16T02:04:00Z' \
  --until '2026-10-16T02:07:30Z' \
  plugin_daemon | rg '/dispatch/(llm|text_embedding)/invoke'
```

重点读三个字段：

| 字段 | 如何使用 |
|---|---|
| `/dispatch/text_embedding/invoke` | Embedding 插件调用，包含服务调用开销，不能直接当作纯向量计算耗时 |
| `/dispatch/llm/invoke` | 生成模型插件调用，包含模型服务等待及请求处理 |
| `latency_ms` | 调用时长，除以 1,000 得秒数 |
| 日志时间 | 本次记录是调用结束时间；结合时长判断对应窗口 |
| `trace_id` | 保存用于局部关联；出现 trace_id 不等于已接通完整链路 |

本例第一轮 LLM 插件为 85,820 ms，第二轮为 57,890 ms，均占 Pipeline 大部分时间，因此继续向模型服务查。Embedding 插件分别为 1,938 ms、4,123 ms。

必要时查看同一窗口 API 日志：

```shell
docker compose logs --no-color \
  --since '2026-10-16T02:04:00Z' \
  --until '2026-10-16T02:07:30Z' \
  api | rg -i 'error|warn|embedding|retriev|timeout'
```

有错误时先关联到目标消息，不能因为同一时间出现 402、超时等错误就认定是该条主回答的原因。日志可能同时包含标题生成、其他会话或后台请求。

**完成条件**：找出哪个调用覆盖主要时间，或确认现有日志不足以分层。没有匹配行时，先检查时区、日志保留及实际服务名，不将“没日志”解释成“没调用”。

## 4. 到模型服务核对调用与启动过程

本机 Ollama 运行在 macOS 上，其日志不在 Dify 容器里。先定位进程及日志去向：

```shell
lsof -nP -iTCP:11434 -sTCP:LISTEN
OLLAMA_DIAG_PID="$(lsof -t -nP -iTCP:11434 -sTCP:LISTEN | head -n 1)"
lsof -a -p "$OLLAMA_DIAG_PID" -d 1,2 -Fn
```

若没有监听进程，先确认实际运行位置；不要继续执行带空 PID 的命令。本机输出的日志路径为 `/opt/homebrew/var/log/ollama.log`。其他安装方式可能不同，使用上一步实际发现的路径。

本例查看北京时间 10:04–10:07 的事件：

```shell
rg '2026-10-16T10:0[4-7]:|2026/10/16 - 10:0[4-7]:' \
  /opt/homebrew/var/log/ollama.log
```

按以下顺序核对：

1. 找 `/api/embed`、`/api/chat` 的结束时间和耗时，与插件调用对应。
2. 找 `starting mlx runner subprocess` 和 `mlx runner is ready`，计算启动到可用的间隔。
3. 找内部 `/v1/completions` 耗时；这是当前 MLX 后端的日志路径，其他后端不一定出现。
4. 用模型名、输入 Token、时间顺序交叉核对，排除相邻的其他请求。

本例第一轮 10:04:14.795 启动，10:04:42.002 ready，冷启动约 27.207 秒；随后模型内部请求为 58.545 秒。第二轮内部请求仍为 57.810 秒。因此目前定位到“模型服务内部仍慢”，还未证明内部计算究竟慢在哪里。

**计时包含关系**：Pipeline 覆盖插件调用；LLM 调用又包含加载、等待和模型处理。不能将嵌套计时相加，也不能把总耗时减去已知项后的全部剩余时间命名为“检索耗时”。

`Prompt processing progress` 只是进度事件，不能当作精确 prefill 完成或首 Token 时刻。系统内存占用高也只是线索，不能单凭一个快照认定为根因。

**完成条件**：区分模型冷启动与启动后的请求处理；证据不够时停在服务层定位，不编造更细的阶段耗时。

## 5. 判断是否具备完整 Trace

检查 API 容器 OTel 开关：

```shell
docker compose exec -T api printenv ENABLE_OTEL
```

查询应用追踪状态，不读取追踪平台凭据：

```shell
docker compose exec -T db_postgres psql -U postgres -d dify \
  -v app_id='03b1eb2b-d822-41b0-8d57-91a5e21e3be0' <<'SQL'
SELECT id, COALESCE(tracing, '') <> '' AS tracing_config_present
FROM apps WHERE id = :'app_id';
SELECT app_id, tracing_provider
FROM trace_app_config WHERE app_id = :'app_id';
SQL
```

本机实测 OTel 为 false，应用 tracing 为空且没有追踪配置。这表明当前没有通过这些入口建立完整追踪。

即使开关启用，也要继续确认能否找到**同一条请求**的父子 Span、开始结束时间、各处理阶段与模型调用。只有多个服务各自打印 trace_id，不能称为完整 Trace。外部反向代理等独立观测能力需另行核查，不能由以上结果一概推断。

本次证据来自消息表、插件及 Ollama 日志的人工关联；并发较多时，仅按时间难以可靠匹配，应先补关联能力，而不是强行拼接。

## 6. 写排查结论，再决定下一步

每次记录以下六项即可：

```text
目标请求：应用 / conversation ID / message ID / 时间与时区
实际现象：总耗时、是否成功、输出规模
分层证据：各日志来源、对应时刻与时长
已确认：主要耗时所在服务，是否包含冷启动
未确认：首 Token、输入计算、生成、排队等缺口
下一步：只补哪一项证据，保持哪些配置不变
```

按当前发现选择下一步：

| 已有证据 | 下一步 |
|---|---|
| 冷启动占主要时间，热调用明显改善 | 对照模型加载／驻留状态；记录后再讨论预热或驻留配置 |
| 热调用内部请求仍慢 | 采集同输入、同模型的真实流式首 Token 与 Ollama 原始计时字段 |
| 插件慢，模型服务请求明显短 | 核查插件等待、连接、重试及排队，先保证请求正确关联 |
| Pipeline 慢，插件调用解释不了 | 补查检索、重排、历史与 Prompt 构建等阶段，保留未归因时间 |
| 后台完成快，但用户等待明显 | 检查浏览器 Network 的流式到达、代理缓冲与渲染 |

Ollama 原始响应若提供 `load_duration`、`prompt_eval_duration`、`eval_duration`，通常单位为纳秒，使用前核对实际版本。首 Token 时间需在流式客户端单独记录；收到 HTTP 响应头或第一块元数据不等于收到第一个答案 Token。保留真实输出，不能用关键词规则或固定响应替代模型性能测试。

需要补采时，先写清调用输入和配置，再执行定向实验；不在定位途中同时换模型、改 Prompt、改 Top K 或重启服务。冷启动实验也不应直接卸载正在被其他工作使用的模型。

## 本次已走到哪里

已完成步骤 1–5：确定两条消息、查到插件与模型服务时长、确认第一轮约 27.2 秒启动等待，以及当前没有完整 Trace。尚未执行新的冷／热对照或流式计时。

原始摘录与结构化数据见[本次运行目录](../../runs/dify-multiturn-20261016/README.md)，数值和边界见[慢请求定位记录](Dify多轮对话支持与验证.md#历史慢请求定位2026-10-16)。

运行目录可分享时，仅保留必要的时刻、调用类型、耗时与关联 ID；删除凭据、账户信息及无关知识正文。没有采集到的历史细节无法通过现在打开追踪开关补回。
