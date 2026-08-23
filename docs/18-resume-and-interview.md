# 简历与面试叙事（只写已实测内容）

## 项目一句话

构建基于真实 CFPB 投诉、官方指导和法规的双语客服 RAG 工作台，按版本比较 Dense、Native
Sparse/RRF、Intent/Metadata、Contextual/Parent-Child、Corrective Retrieval 和本地
Cross-Encoder，并用 Trace、确定性 Eval、安全扫描、缓存、Alias 回滚和 CI 证明生产约束。

## 可展示的实测证据

- 真实数据：200 条新增投诉、335 个主索引点、432 个 V0.5 contextual 点、Manifest 335/335；
- V0.4：Qwen3 Reranker 0.6B Q8_0 GGUF 本地运行，8-case Hit@3 1.0，但 MRR 0.9375、p95 35.17s，因权衡未晋级默认；
- V0.5：40-case draft Hit@3 0.975、MRR 0.8958、p95 108.28ms；
- Answer/Safety：11-case 自动门引用有效/覆盖/拒答正确率均 1.0，危险声明 0；
- Operations：Embedding Cache、API 429、model timeout/concurrency、蓝绿 Alias 激活/回滚、10 次 stability smoke 0 错误；
- CI：GitHub Actions clean runner 通过 pytest、compileall、benchmark audit 和 Compose config。

## 面试回答结构

1. 先说失败：例如 Reranker 一次请求导致 llama.cpp `ubatch` 500，或 R1 的全角引用导致过多人工复核；
2. 再说必要升级：batch/truncation 或 citation normalization + repair；
3. 展示 Trace 前后变化和同集指标；
4. 说明为什么没有把每个前沿模块都设为默认；
5. 明确限制：Golden Draft 仍需双人复核，V0.8 CFPB PDF CDN 有 403，V1 Agent 尚未解除锁定。

不要把 `release_check` 当前的 false 隐藏：它准确指出唯一未通过的公开发布门是独立人工 Golden Review。
