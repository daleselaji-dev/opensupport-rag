# Golden Review Protocol

结构审计和自动指标不能替代人工 Citation Support。Review Center 使用两个独立角色：

```text
reviewer_a 全部 50 case
reviewer_b 全部 50 case
          │
          ▼
两位 reviewer 都覆盖全部 case → release_check golden_review=approved
```

API：

- `GET /api/eval/golden-review`
- `POST /api/eval/golden-review/signoff`

每位 reviewer 必须提交自己的角色、名字、完整 case ID 列表和备注。系统拒绝未知 case ID，
只接受两个不同 reviewer 且每人覆盖 50 条的状态。签名文件位于本地 `data/`，不会提交到公开
仓库；公开仓库只包含评测集、审计问题和复现脚本。
