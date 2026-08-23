# 第 2 课：把 LM Studio 接入 RAG

## 先理解：本项目需要两种模型

| 模型角色 | 做什么 | 在 LM Studio 中要找什么 |
|---|---|---|
| Chat Model | 读到检索证据后，写出带引用的回答 | Instruct / Chat 类型模型 |
| Embedding Model | 把问题和投诉转成向量 | 名称带 embedding / embed 的模型 |

一个聊天模型通常**不能替代** Embedding 模型。RAG 的关键是：问题和资料必须由同一种 Embedding Model 转成同一个“语义坐标系”，Qdrant 才能比较它们。

## 操作步骤

1. 打开 LM Studio。
2. 进入 **Developer** 页面，点击 **Start server**。
3. 确认浏览器或 PowerShell 能访问。默认端口是 1234；如果 Windows 拒绝该端口，可以改用高位端口，例如本机当前使用的 23145：

   ```powershell
   Invoke-RestMethod http://localhost:23145/v1/models | ConvertTo-Json -Depth 5
   ```

4. 复制一个 `type: llm` 的模型标识，填入 `.env` 的 `CHAT_MODEL`。
5. 复制一个 `type: embedding` 的模型标识，填入 `.env` 的 `EMBEDDING_MODEL`。
6. 需要时在 LM Studio 中加载这两个模型。LM Studio 可在请求时自动加载模型，具体取决于你的服务设置。

## 为什么项目用 OpenAI 客户端却不必使用 OpenAI？

`openai` Python 包只是一个会发送 HTTP 请求的客户端。LM Studio 实现了与 OpenAI 相同形状的 `/v1/embeddings` 和 `/v1/chat/completions` 接口；把 `base_url` 改成 LM Studio 实际运行的本地地址（本机当前为 `http://localhost:23145/v1`）后，请求会留在你的电脑上。

## 本课检查

当 `/v1/models` 能返回模型列表时，你已经完成了 RAG 的本地模型服务准备。下一步我们会一起把具体模型 ID 写进 `.env`，启动 Qdrant，并用真实 CFPB 投诉建立第一个向量索引。

## Embedding 的线上备用方案

如果本地 Qwen Embedding 下载速度过慢，可以只把 Embedding 切到阿里云百炼，Chat Model 仍由 LM Studio 本地运行：

```text
EMBEDDING_PROVIDER=qwen-api
EMBEDDING_BASE_URL=https://<WorkspaceId>.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
EMBEDDING_API_KEY=sk-your-dashscope-key
EMBEDDING_MODEL=qwen3.7-text-embedding
EMBEDDING_FAMILY=qwen-api
```

不要把真实 API key 提交到 Git。阿里云官方文档列出的 `qwen3.7-text-embedding` 价格约为每 1K 输入 Token 0.0005 元；实际区域、免费额度和账单以百炼控制台为准。

当前项目会自动按每批 10 条文本调用 Qwen Embedding API，符合 `text-embedding-v4`/`qwen3.7-text-embedding` 的官方接口限制；你不需要手工切分 200 条投诉。

## 官方依据

- LM Studio Local Server: <https://lmstudio.ai/docs/developer/core/server>
- OpenAI-compatible endpoints: <https://lmstudio.ai/docs/developer/openai-compat>
- Embeddings: <https://lmstudio.ai/docs/developer/openai-compat/embeddings>
