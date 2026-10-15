# 确定性测试

从项目根目录运行：

```shell
.venv/bin/python -m unittest discover -s tests -v
```

`test_retrieval.py` 校验检索评分契约：文档身份与排名、未命中与无答案、失败请求分母。它不使用模拟结果证明智能能力。真实 Dify 检索由 `scripts/evaluate_dify_retrieval.py` 执行，证据保存至 `runs/`。
