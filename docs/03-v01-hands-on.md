# 第 3 课：亲手启动 V0.1

这一课的目标不是“看见一个网页”，而是亲手验证真实 RAG 的完整链路：

```text
真实 CFPB 数据 → Embedding → Qdrant → 双证据检索 → LM Studio 生成 → 引用
```

## 第一步：准备两种本地模型

你已有 Chat Model：`DeepSeek-R1-Distill-Qwen-7B-Q4_K_M`。

还需要在 LM Studio 下载官方 Qwen3-Embedding-0.6B GGUF Embedding Model。它用于让中文问题能检索到英文 CFPB 资料。可用命令：

```powershell
lms get https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF --gguf --yes
```

不要把 Chat Model 填到 `EMBEDDING_MODEL`；两个模型的工作不同。

## 第二步：启动服务

1. 在 LM Studio 的 Developer 页面启动 Server。
2. 在 PowerShell 确认模型服务可访问：

   ```powershell
   Invoke-RestMethod http://localhost:1234/v1/models | ConvertTo-Json -Depth 5
   ```

3. 从输出复制两个实际 ID，填入 `.env`：

   ```text
   CHAT_MODEL=<DeepSeek 的实际 ID>
   EMBEDDING_MODEL=<Qwen3-Embedding 的实际 ID>
   EMBEDDING_FAMILY=qwen
   ```

4. 启动 Docker Desktop，再启动 Qdrant：

   ```powershell
   docker compose up -d qdrant
   ```

5. 在项目根目录启动 API：

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```

6. 打开 `http://localhost:8000`，导入 200 条 2024 年投诉。

## 第三步：观察一条真实 RAG 链路

输入：

> 我发现信用卡有一笔陌生扣款，应该先让客服确认什么？

你应该看到：

- `[S1]`、`[S2]`：CFPB 官方指导或法规；
- `[C1]`、`[C2]`：相似的真实消费者投诉；
- 每张证据卡片的来源、相似度和原始链接；
- 回答末尾的安全边界。

## 你的检查问题

在看答案前，先自己判断：

1. 官方指导为什么比投诉案例更适合支持“应该怎么做”？
2. 投诉案例为什么仍然有价值？
3. 如果 `[C1]` 的投诉和你的问题表面相似、但产品不同，应该怀疑检索还是生成？
4. 如果回答出现 `[S7]`，但页面没有 `[S7]` 卡片，系统的哪一个检查失败了？

完成后，把你的观察写给我。我们将据此决定 V0.2 的 BM25、过滤或 Reranker 是否有必要。
