# Golden Review Protocol

结构审计和自动指标不能替代人工 Citation Support。Review Center 使用两个独立角色：

```text
reviewer_a 全部 50 case
reviewer_b 全部 50 case
          │
          ▼
两位 reviewer 都覆盖全部 case → release_check golden_review=approved
```

生成逐案例审阅表：

```powershell
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe scripts\generate_golden_review_packet.py
```

输出 `evals/customer_support_benchmark_v0.3_review_form.md`。两位 reviewer 应分别打开
原始 URL，判断来源是否真的支持问题、来源类型是否完整、拒答边界是否安全，再提交完整
`case_id` 集合；不能只看自动 Hit@k 或 URL 是否相关。

提交工具（只有 reviewer 完成独立审阅后才能使用）：

```powershell
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe scripts\signoff_golden_review.py --role reviewer_a --reviewer "Reviewer A" --all-cases --notes "逐条检查完成"
.\.venv\Scripts\python.exe scripts\signoff_golden_review.py --role reviewer_b --reviewer "Reviewer B" --all-cases --notes "独立复核完成"
```

`--all-cases` 是显式承诺，不是自动批准开关；脚本不会替 reviewer 判断证据。

API：

- `GET /api/eval/golden-review`
- `POST /api/eval/golden-review/signoff`

每位 reviewer 必须提交自己的角色、名字、完整 case ID 列表和备注。系统拒绝未知 case ID，
只接受两个不同 reviewer 且每人覆盖 50 条的状态。签名文件位于本地 `data/`，不会提交到公开
仓库；公开仓库只包含评测集、审计问题和复现脚本。
