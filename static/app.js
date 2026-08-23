const ingestForm = document.querySelector('#ingest-form');
const queryForm = document.querySelector('#query-form');
const ingestStatus = document.querySelector('#ingest-status');
const result = document.querySelector('#result');
const answer = document.querySelector('#answer');
const sources = document.querySelector('#sources');
const guardrail = document.querySelector('#guardrail');
const traceContainer = document.querySelector('#trace');
const traceId = document.querySelector('#trace-id');
const evalRun = document.querySelector('#eval-run');
const answerEvalRun = document.querySelector('#answer-eval-run');
const evalSummary = document.querySelector('#eval-summary');
const answerEvalSummary = document.querySelector('#answer-eval-summary');
const retrievalMode = document.querySelector('#retrieval-mode');
const evalMode = document.querySelector('#eval-mode');
const evalVersion = document.querySelector('#eval-version');
const evalBenchmark = document.querySelector('#eval-benchmark');
const assemblyVersion = document.querySelector('#assembly-version');
const queryVersion = document.querySelector('#query-version');
const versionDelta = document.querySelector('#version-delta');
const statusGrid = document.querySelector('#status-grid');
const refreshStatus = document.querySelector('#refresh-status');
const questionInput = document.querySelector('#question');
const lifecycleGrid = document.querySelector('#lifecycle-grid');
const currentStage = document.querySelector('#current-stage');
const lifecyclePrinciple = document.querySelector('#lifecycle-principle');
const dataPipeline = document.querySelector('#data-pipeline');
const dataQualitySummary = document.querySelector('#data-quality-summary');
const dataQualityStatus = document.querySelector('#data-quality-status');
const frontierGrid = document.querySelector('#frontier-grid');
const componentInspector = document.querySelector('#component-inspector');
const previewButton = document.querySelector('#preview-button');
const standardsGrid = document.querySelector('#standards-grid');
const queryButton = queryForm.querySelector('button[type="submit"]');
const executionStatus = document.querySelector('#execution-status');
const pipeline = document.querySelector('#pipeline');
const agentForm = document.querySelector('#agent-form');
const agentResult = document.querySelector('#agent-result');
const buildContextualButton = document.querySelector('#build-contextual');
const contextualStatus = document.querySelector('#contextual-status');
let manualVersionSelection = false;

if (agentForm) {
  agentForm.addEventListener('submit', (event) => {
    event.preventDefault();
    if (agentResult) agentResult.innerHTML = '<span class="agent-status">V1 LOCKED</span><p class="hint">受控 Agent 会在 V0.4–V0.9 的数据、检索、引用、安全和运维 Gate 通过后开放。当前先使用上方 RAG Query Console 观察 V0.4 Trace。</p>';
  });
}

if (buildContextualButton) {
  buildContextualButton.addEventListener('click', async () => {
    buildContextualButton.disabled = true;
    contextualStatus.textContent = '正在从当前 Dense 索引拆分长 Chunk、生成上下文前缀并写入隔离集合…';
    try {
      const response = await fetch('/api/index/build-contextual', {method: 'POST'});
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'V0.5 构建失败');
      contextualStatus.textContent = `完成：${body.source_documents} 个源文档 → ${body.contextual_chunks} 个 Contextual Chunk；集合 ${body.collection_name}`;
      loadStatus();
    } catch (error) {
      contextualStatus.textContent = `失败：${error.message}`;
    } finally {
      buildContextualButton.disabled = false;
    }
  });
}

const versionCatalog = {
  v0_1: {label: 'V0.1 Dense', delta: 'V0.1 只有 Qwen Embedding + Qdrant Dense + 双证据；没有 BM25、RRF、Intent 或 Metadata 过滤。', diagram: 'v0_1'},
  v0_2: {label: 'V0.2 Hybrid', delta: 'V0.2 新增 BM25 和 RRF；用于比较语义召回与精确词项召回，不改变问题意图。', diagram: 'v0_2'},
  v0_3: {label: 'V0.3 Intent + Metadata', delta: 'V0.3 新增意图识别、audience/source URL Metadata 过滤，以及对应 Trace。', diagram: 'v0_3'},
  v0_4: {label: 'V0.4 Cross-Encoder 实验', delta: 'V0.4 在 Dense + Sparse/RRF 的高召回候选集上增加 Cross-Encoder 精排；只在候选集已包含正确来源且排名问题可复现时有价值。', diagram: 'v0_4'},
  v0_5: {label: 'V0.5 Contextual / Parent-Child', delta: 'V0.5 针对长 Chunk 和标题/来源丢失问题，建立隔离的 contextual parent-child 索引；先构建索引，再比较同集 Citation Support 和上下文完整性。', diagram: 'v0_5'},
  v0_6: {label: 'V0.6 Adaptive / Corrective', delta: 'V0.6 首次召回后做证据评分，最多执行一次受控查询变体；证据仍不足则停止并拒答，不允许无限 Agent 循环。', diagram: 'v0_6'},
  v0_8: {label: 'V0.8 PDF Page Baseline', delta: 'V0.8 使用页级 PDF 文本基线保留页码和来源；视觉表格/图表检索仍需独立数据集和模型实验。', diagram: 'v0_8'},
};

const pipelineCatalog = {
  query_received: ['01', '问题', '中文/英文输入'],
  route_intent: ['01a', '意图识别', '客服 Intent'],
  metadata_filter: ['01b', 'Metadata', '范围过滤'],
  embed_query: ['02', 'Embedding', 'Qwen3 · 向量'],
  retrieve_guidance: ['03', '官方检索', 'CFPB / Regulation'],
  retrieve_complaints: ['04', '案例检索', '真实投诉'],
  retrieve_dense_guidance: ['03d', 'Dense 官方', '语义候选'],
  retrieve_dense_complaints: ['04d', 'Dense 案例', '语义候选'],
  bm25_guidance: ['03b', 'BM25 官方', '精确词项'],
  bm25_complaints: ['04b', 'BM25 案例', '错误码/术语'],
  fusion_rrf: ['04c', 'RRF', '合并排名'],
  rerank_candidates: ['04d', 'Cross-Encoder', '候选精排'],
  contextual_backend: ['05c', 'Contextual Index', '父子索引'],
  expand_parent: ['05d', '父身份扩展', '标题/来源继承'],
  adaptive_route: ['06a', 'Adaptive Route', '证据评分'],
  evidence_grade: ['06b', 'Evidence Grade', '够不够回答'],
  query_translation: ['06c', 'Query Variant', '一次查询变体'],
  corrective_retry: ['06d', 'Corrective Retry', '有限纠错'],
  pdf_backend: ['08a', 'PDF Pages', '页级证据'],
  sparse_backend: ['02s', 'Sparse 后端', 'Qdrant 原生 BM25'],
  assemble_context: ['05', '上下文', '[S#] + [C#]'],
  generate_answer: ['06', 'LLM', 'DeepSeek-R1'],
  repair_citations: ['07a', 'R1 引用修复', '缺失时补引'],
  validate_citations: ['07', '校验', '引用 / 边界'],
  guardrail_review: ['08', '安全门', '引用覆盖/危险声明'],
  evidence_safety_scan: ['05s', '证据安全扫描', '注入/PII隔离'],
};

const versionPipelines = {
  v0_1: ['query_received', 'embed_query', 'retrieve_guidance', 'retrieve_complaints', 'evidence_safety_scan', 'assemble_context', 'generate_answer', 'validate_citations', 'guardrail_review'],
  v0_2: ['query_received', 'embed_query', 'sparse_backend', 'retrieve_dense_guidance', 'retrieve_dense_complaints', 'bm25_guidance', 'bm25_complaints', 'fusion_rrf', 'evidence_safety_scan', 'assemble_context', 'generate_answer', 'repair_citations', 'validate_citations', 'guardrail_review'],
  v0_3: ['query_received', 'route_intent', 'metadata_filter', 'embed_query', 'sparse_backend', 'retrieve_dense_guidance', 'retrieve_dense_complaints', 'bm25_guidance', 'bm25_complaints', 'fusion_rrf', 'evidence_safety_scan', 'assemble_context', 'generate_answer', 'repair_citations', 'validate_citations', 'guardrail_review'],
  v0_4: ['query_received', 'route_intent', 'metadata_filter', 'embed_query', 'sparse_backend', 'retrieve_dense_guidance', 'retrieve_dense_complaints', 'bm25_guidance', 'bm25_complaints', 'fusion_rrf', 'rerank_candidates', 'evidence_safety_scan', 'assemble_context', 'generate_answer', 'repair_citations', 'validate_citations', 'guardrail_review'],
  v0_5: ['query_received', 'route_intent', 'metadata_filter', 'contextual_backend', 'embed_query', 'sparse_backend', 'retrieve_dense_guidance', 'retrieve_dense_complaints', 'bm25_guidance', 'bm25_complaints', 'fusion_rrf', 'expand_parent', 'evidence_safety_scan', 'assemble_context', 'generate_answer', 'repair_citations', 'validate_citations', 'guardrail_review'],
  v0_6: ['query_received', 'adaptive_route', 'route_intent', 'metadata_filter', 'contextual_backend', 'embed_query', 'sparse_backend', 'retrieve_dense_guidance', 'retrieve_dense_complaints', 'bm25_guidance', 'bm25_complaints', 'fusion_rrf', 'expand_parent', 'evidence_grade', 'query_translation', 'corrective_retry', 'evidence_safety_scan', 'assemble_context', 'generate_answer', 'repair_citations', 'validate_citations', 'guardrail_review'],
  v0_8: ['query_received', 'route_intent', 'metadata_filter', 'pdf_backend', 'embed_query', 'sparse_backend', 'retrieve_dense_guidance', 'retrieve_dense_complaints', 'bm25_guidance', 'bm25_complaints', 'fusion_rrf', 'evidence_safety_scan', 'assemble_context', 'generate_answer', 'repair_citations', 'validate_citations', 'guardrail_review'],
};

function renderPipeline(version) {
  const nodes = versionPipelines[version] || versionPipelines.v0_3;
  pipeline.innerHTML = nodes.map((name, index) => {
    const [step, title, subtitle] = pipelineCatalog[name];
    const optional = ['route_intent', 'metadata_filter', 'contextual_backend', 'pdf_backend', 'sparse_backend', 'bm25_guidance', 'bm25_complaints', 'fusion_rrf', 'rerank_candidates', 'expand_parent', 'adaptive_route', 'evidence_grade', 'query_translation', 'corrective_retry', 'repair_citations', 'guardrail_review'].includes(name) ? ' optional' : '';
    const arrow = index < nodes.length - 1 ? '<span class="pipeline-arrow" aria-hidden="true">→</span>' : '';
    return `<button type="button" class="pipeline-node${optional}" data-component="${name}"><span>${step}</span><strong>${title}</strong><small>${subtitle}</small></button>${arrow}`;
  }).join('');
}

function selectAssemblyVersion(version) {
  if (!versionCatalog[version]) return;
  assemblyVersion.value = version;
  evalVersion.value = version;
  queryVersion.value = version;
  versionDelta.textContent = versionCatalog[version].delta;
  if (version === 'v0_1') {
    retrievalMode.value = 'dense';
    evalMode.value = 'dense';
  } else if (version === 'v0_2') {
    retrievalMode.value = 'hybrid';
    evalMode.value = 'hybrid';
  } else if (version === 'v0_4') {
    retrievalMode.value = 'hybrid';
    evalMode.value = 'hybrid';
  } else if (version === 'v0_5') {
    retrievalMode.value = 'hybrid';
    evalMode.value = 'hybrid';
  } else if (version === 'v0_6') {
    retrievalMode.value = 'hybrid';
    evalMode.value = 'hybrid';
  } else if (version === 'v0_8') {
    retrievalMode.value = 'hybrid';
    evalMode.value = 'hybrid';
  }
  document.querySelectorAll('.version-button').forEach((button) => button.classList.toggle('selected', button.dataset.version === version));
  document.querySelectorAll('.architecture-rail .diagram-card[data-version]').forEach((card) => card.classList.toggle('version-visible', card.dataset.version === version));
  renderPipeline(version);
}

const componentCatalog = {
  query_received: {title: '问题输入', input: '中文/英文自然语言问题', output: 'QueryRequest.question + retrieval_mode', dependency: '浏览器 → FastAPI', purpose: '接收问题，不修改用户原文。'},
  route_intent: {title: '意图识别', input: '问题文本', output: 'intent + confidence + audience', dependency: 'V0.3 rule baseline', purpose: '区分消费者提交投诉、企业响应、账单错误和陌生扣款。'},
  metadata_filter: {title: 'Metadata 过滤', input: 'intent + source URL family', output: '受限官方候选范围', dependency: 'Qdrant payload metadata', purpose: '先收窄业务范围，避免消费者流程和企业流程互相误召回。'},
  embed_query: {title: 'Embedding', input: '问题文本（Qwen 查询指令）', output: '1024 维向量', dependency: 'LM Studio Embedding API', purpose: '把语义问题变成可比较的向量；不负责回答。'},
  retrieve_guidance: {title: '官方 Dense 检索', input: '查询向量 + guidance/regulation 过滤', output: '[S#] 官方证据', dependency: 'Qdrant', purpose: '优先召回 CFPB 官方流程和法规。'},
  retrieve_dense_guidance: {title: '官方 Dense 候选', input: '查询向量 + 官方来源过滤', output: 'Dense candidates', dependency: 'Qdrant', purpose: 'Hybrid 模式的第一条候选分支。'},
  retrieve_complaints: {title: '投诉 Dense 检索', input: '查询向量 + complaint 过滤', output: '[C#] 案例证据', dependency: 'Qdrant', purpose: '召回相似消费者主张，不代表事实成立。'},
  retrieve_dense_complaints: {title: '投诉 Dense 候选', input: '查询向量 + complaint 过滤', output: 'Dense candidates', dependency: 'Qdrant', purpose: 'Hybrid 模式的案例候选分支。'},
  bm25_guidance: {title: '官方 BM25', input: '问题词项 + 官方文本', output: 'BM25 candidates', dependency: '本地稀疏检索', purpose: '补足机构名、术语和精确词匹配。'},
  bm25_complaints: {title: '投诉 BM25', input: '问题词项 + 投诉文本', output: 'BM25 candidates', dependency: '本地稀疏检索', purpose: '补足错误码、产品名和精确表达。'},
  fusion_rrf: {title: 'RRF 融合', input: 'Dense 排名 + BM25 排名', output: '统一候选排名', dependency: 'RRF 算法', purpose: '只有在实测质量/延迟收益成立时才接受。'},
  rerank_candidates: {title: 'Cross-Encoder 精排', input: '问题 + RRF 候选文本对', output: 'rerank_score + Top-k 证据', dependency: '可选 sentence-transformers · BAAI/bge-reranker-v2-m3', purpose: 'Bi-Encoder 负责全库高召回，Cross-Encoder 逐对阅读问题与候选，修复候选已命中但排名靠后的问题；不检索全库。'},
  contextual_backend: {title: 'Contextual / Parent-Child Index', input: '当前 Qdrant 派生索引', output: '隔离的 V0.5 Dense + Sparse 集合', dependency: 'POST /api/index/build-contextual · Qwen Embedding', purpose: '把标题、来源、权威和产品/问题元数据继承到子 Chunk，并拆分过长记录；不覆盖旧索引。'},
  expand_parent: {title: '父身份扩展', input: '子 Chunk 命中 + parent_chunk_id', output: '保留父文档、标题、来源和 child index', dependency: 'Qdrant payload metadata', purpose: '避免长文档被切碎后只剩孤立句子，帮助上下文和引用回溯。'},
  adaptive_route: {title: 'Adaptive Route', input: '装配版本 + 首次召回', output: '最多一次 corrective retry', dependency: '确定性预算控制', purpose: '把“证据不足”变成有限分支，不允许无限循环或盲目扩大上下文。'},
  evidence_grade: {title: 'Evidence Grade', input: '官方来源数量 + 分数语义 + 候选数', output: 'sufficient + reason codes', dependency: '确定性规则', purpose: '区分“检索没找到”与“生成没引用”，为纠错或拒答提供证据。'},
  query_translation: {title: 'Query Variant', input: '原始问题 + 领域术语映射', output: '一次安全查询变体', dependency: 'V0.6 deterministic term expansion', purpose: '只补充已知领域术语，不编造账户事实，且最多触发一次。'},
  corrective_retry: {title: 'Corrective Retry', input: '首轮证据 + 查询变体结果', output: '合并后的最终证据或停止', dependency: 'retry budget=1', purpose: '在证据不足时有限重试；仍不足就停下，避免成本失控。'},
  pdf_backend: {title: 'PDF Page Baseline', input: '本地 PDF + 页码', output: '带 page metadata 的证据页', dependency: 'pypdf + V0.8 isolated Qdrant collection', purpose: '先建立页级文本血缘，再决定是否引入视觉表格/图表模型。'},
  sparse_backend: {title: 'Sparse 后端', input: 'Qdrant collection + sparse model', output: 'native=true / fallback=true', dependency: 'Qdrant 1.17+ · qdrant/bm25', purpose: '让 BM25 从进程内全库扫描升级为持久化 Sparse 向量检索。'},
  assemble_context: {title: '上下文组装', input: '[S#] + [C#] evidence', output: '带引用的 Prompt', dependency: 'FastAPI 内存', purpose: '保持官方指导与消费者主张的权威边界。'},
  generate_answer: {title: 'Chat LLM', input: '问题 + 证据 Prompt', output: '中文/英文回答', dependency: 'LM Studio Chat API', purpose: '只根据证据生成，不执行外部动作。'},
  repair_citations: {title: 'R1 引用修复', input: '回答 + 已召回来源 ID', output: '只补充已有 [S#]/[C#] 引用', dependency: 'LM Studio Chat API', purpose: '仅在引用缺失时运行；不允许添加新事实或新来源。'},
  validate_citations: {title: '引用校验', input: '回答 + 可用引用 ID', output: 'citation_valid + invalid_citations', dependency: '确定性规则', purpose: '阻止引用不存在的来源。'},
  guardrail_review: {title: '安全门', input: '回答 + 引用覆盖率 + 危险声明', output: 'needs_human_review / fail-closed', dependency: '确定性 Guardrail', purpose: '引用 ID 正确不代表答案有证据；覆盖率不足或危险声明会降级人工。'},
  evidence_safety_scan: {title: '证据安全扫描', input: '候选证据文本', output: '隔离疑似 PII/提示注入', dependency: '确定性安全规则', purpose: '文档内容是不可信数据；命中注入模式的证据不会直接进入 Prompt。'},
};

function text(value) {
  const node = document.createElement('span');
  node.textContent = value ?? '—';
  return node.innerHTML;
}

function renderTrace(events, id) {
  traceId.textContent = id ? `trace_id: ${id}` : '';
  if (!events || events.length === 0) {
    traceContainer.innerHTML = '<p class="hint">提交一次查询后，这里会显示真实运行步骤。</p>';
    syncDiagramTrace([]);
    return;
  }
  traceContainer.innerHTML = events.map((event) => `
    <article class="trace-row" data-trace-name="${text(event.name)}">
      <button type="button" class="trace-main" aria-expanded="false">
        <span class="trace-step">${text(event.step)}</span>
        <span class="trace-status ${text(event.status)}"></span>
        <span class="trace-name">${text(event.name)}</span>
        <span class="trace-summary">${text(event.summary)}</span>
        <span class="trace-duration">${text(event.duration_ms)} ms</span>
      </button>
      <pre class="trace-details" hidden>${text(JSON.stringify(event.details, null, 2))}</pre>
    </article>
  `).join('');
  traceContainer.querySelectorAll('.trace-main').forEach((button) => {
    button.addEventListener('click', () => {
      const row = button.closest('.trace-row');
      const details = row.querySelector('.trace-details');
      const expanded = !details.hidden;
      details.hidden = expanded;
      button.setAttribute('aria-expanded', String(!expanded));
      document.querySelectorAll('.pipeline-node').forEach((node) => node.classList.remove('active'));
      const matching = document.querySelector(`[data-component="${row.dataset.traceName}"]`);
      if (matching) matching.classList.add('active');
    });
  });
  syncDiagramTrace(events);
}

function upsertTraceEvent(events, event) {
  const index = events.findIndex((item) => item.name === event.name);
  if (index >= 0) events[index] = event;
  else events.push(event);
  return events;
}

function updateExecutionStatus(event) {
  const item = componentCatalog[event.name];
  const title = item ? item.title : event.name;
  const state = event.status === 'running' ? '正在执行' : event.status === 'failed' ? '失败' : '已完成';
  executionStatus.innerHTML = `<strong>${text(state)}：${text(title)}</strong><span>${text(event.summary)}</span><small>${event.duration_ms ? `耗时 ${text(event.duration_ms)} ms` : '等待真实结果…'}${item ? ` · 功能：${text(item.purpose)}` : ''}</small>`;
}

function syncDiagramTrace(events) {
  const byName = new Map((events || []).map((event) => [event.name, event]));
  document.querySelectorAll('.diagram-node').forEach((node) => {
    const event = byName.get(node.dataset.component);
    const status = node.querySelector('em');
    node.classList.remove('diagram-completed', 'diagram-pending', 'diagram-failed');
    if (!event) {
      status.textContent = '未运行';
      return;
    }
    node.classList.add(`diagram-${event.status}`);
    status.textContent = event.status === 'pending' ? '等待中' : `Step ${event.step} · ${event.duration_ms}ms`;
  });
}

function renderComponentInspector(name) {
  const item = componentCatalog[name] || componentCatalog.query_received;
  const traceRow = document.querySelector(`[data-trace-name="${name}"]`);
  componentInspector.innerHTML = `<div class="inspector-heading"><strong>${text(item.title)}</strong><span>${traceRow ? `Trace step ${text(traceRow.querySelector('.trace-step')?.textContent)}` : '尚未运行'}</span></div><dl><dt>输入</dt><dd>${text(item.input)}</dd><dt>输出</dt><dd>${text(item.output)}</dd><dt>依赖</dt><dd>${text(item.dependency)}</dd><dt>作用</dt><dd>${text(item.purpose)}</dd></dl>`;
}

function renderEval(summary) {
  if (!summary || summary.status === 'not_run') {
    evalSummary.innerHTML = `<p class="hint">${text(summary?.message || '尚未运行。')}</p>`;
    return;
  }
  if (summary.retrieval_mode) evalMode.value = summary.retrieval_mode;
  if (summary.assembly_version && !manualVersionSelection) selectAssemblyVersion(summary.assembly_version);
  const overall = summary.overall_passed ? 'PASS' : 'FAIL';
  const gates = (summary.gates || []).map((gate) => `
    <article class="gate ${gate.passed ? 'passed' : 'failed'}">
      <div><strong>${text(gate.label)}</strong><span>${gate.passed ? '通过' : '未通过'}</span></div>
      <p>实际 <b>${text(gate.actual)}</b> · 目标 <b>${text(gate.target)}</b></p>
      <small>${text(gate.note)}</small>
    </article>`).join('');
  const cases = (summary.cases || []).map((item) => `
    <article class="eval-case ${item.hit ? 'case-hit' : 'case-miss'}">
      <div class="case-head"><strong>${text(item.case_id)}</strong><span>${item.hit ? `Hit@3 · rank ${text(item.rank)}` : 'MISS'}</span></div>
      <p>${text(item.question)}</p>
      <small>检索 ${text(item.retrieval_ms)} ms · ${text(item.top_sources?.map((source) => source.citation + ' ' + source.source_type).join(' · '))}</small>
    </article>`).join('');
  const sliceMetrics = Object.entries(summary.metrics?.slice_metrics || {}).map(([slice, metric]) => `<span class="slice-metric"><b>${text(slice)}</b> · n=${text(metric.case_count)} · Hit@3 ${text(metric.hit_at_3)} · MRR ${text(metric.mrr)}</span>`).join('');
  evalSummary.innerHTML = `
    <div class="eval-overview"><strong class="eval-result ${summary.overall_passed ? 'passed' : 'failed'}">${overall}</strong>
      <span><b>${text(summary.assembly_version || '—')}</b> · Hit@3 <b>${text(summary.metrics.hit_at_3)}</b> · MRR <b>${text(summary.metrics.mrr)}</b> · Retrieval p95 <b>${text(summary.metrics.retrieval_p95_ms)} ms</b></span>
    </div>
    <div class="gate-grid">${gates}</div>
    ${sliceMetrics ? `<details class="eval-details"><summary>按问题切片查看指标</summary><div class="slice-metrics">${sliceMetrics}</div></details>` : ''}
    <details class="eval-details" open><summary>评测案例与检索分支</summary><div class="eval-case-grid">${cases}</div></details>
    <p class="hint">索引事实：${text(summary.index_inventory.qdrant_points)} points · Sparse ${text(summary.index_inventory.sparse_qdrant_points)} · ${text(summary.index_inventory.complaint_chunks)} 投诉 · ${text(summary.index_inventory.official_chunks)} 官方 Chunk · Manifest ${text(summary.index_inventory.manifest_indexed_documents)}</p>
    ${summary.benchmark_version?.includes('golden-draft') ? '<p class="hint">注意：50 条 Golden Draft 仍需两位人工复核；当前结果不能直接作为上线 Gate。</p>' : ''}`;
}

function renderAnswerEval(summary) {
  if (!summary || summary.status === 'not_run') {
    answerEvalSummary.innerHTML = `<p class="hint">${text(summary?.message || '尚未运行回答 Eval。')}</p>`;
    return;
  }
  const gates = (summary.gates || []).map((gate) => `<article class="gate ${gate.passed ? 'passed' : 'failed'}"><div><strong>${text(gate.label)}</strong><span>${gate.passed ? '通过' : '未通过'}</span></div><p>实际 <b>${text(gate.actual)}</b> · 目标 <b>${text(gate.target)}</b></p><small>${text(gate.note)}</small></article>`).join('');
  answerEvalSummary.innerHTML = `<div class="eval-overview"><strong class="eval-result ${summary.overall_passed ? 'passed' : 'failed'}">${summary.overall_passed ? 'PASS' : 'FAIL'}</strong><span>${text(summary.benchmark_version)} · ${text(summary.case_count)} cases · p95 ${text(summary.metrics?.p95_ms)} ms</span></div><div class="gate-grid">${gates}</div><p class="hint">引用覆盖 ${text(summary.metrics?.citation_coverage)} · 拒答正确率 ${text(summary.metrics?.refusal_correctness)} · 危险声明 ${text(summary.metrics?.forbidden_claim_count)}</p>`;
}

function statusPill(value) {
  const ready = value === 'ready';
  return `<span class="health-pill ${ready ? 'ready' : 'offline'}">${ready ? 'READY' : text(value || 'UNKNOWN')}</span>`;
}

function renderStatus(health, lastEval) {
  if (!health) {
    statusGrid.innerHTML = '<p class="error">无法读取运行状态。</p>';
    return;
  }
  const evalText = lastEval?.status === 'not_run'
    ? '尚未运行'
    : `${lastEval?.overall_passed ? 'PASS' : 'FAIL'} · Hit@3 ${text(lastEval?.metrics?.hit_at_3)} · MRR ${text(lastEval?.metrics?.mrr)}`;
  statusGrid.innerHTML = `
    <article class="status-item"><span>LM Studio</span><strong>${statusPill(health.lm_studio)}</strong><small>${text(health.chat_model)}</small></article>
    <article class="status-item"><span>Qdrant</span><strong>${statusPill(health.qdrant)}</strong><small>${text(health.collection_name)} · Sparse ${text(health.sparse_indexed_documents ?? '—')}</small></article>
    <article class="status-item"><span>Embedding</span><strong>${text(health.embedding_model)}</strong><small>${text(health.embedding_family)} · ${text(health.embedding_base_url)}</small></article>
    <article class="status-item"><span>索引</span><strong>${text(health.indexed_documents)} points</strong><small>真实向量库记录数</small></article>
    <article class="status-item"><span>V0.5 Contextual</span><strong>${text(health.contextual_indexed_documents ?? 0)} points</strong><small>${health.contextual_ready ? 'parent-child ready' : '尚未构建隔离索引'}</small></article>
    <article class="status-item"><span>Data Foundation</span><strong>${statusPill(health.data_pipeline || 'not_run')}</strong><small>${text(health.data_snapshot_id || '尚未生成快照')}</small></article>
    <article class="status-item"><span>生产依赖</span><strong>${text(Object.entries(health.storage || {}).map(([key, value]) => `${key}:${value}`).join(' · ') || '未探测')}</strong><small>Postgres · MinIO · Redis</small></article>
    <article class="status-item"><span>Reranker</span><strong>${text(health.reranker?.state || 'disabled')}</strong><small>${text(health.reranker?.model || 'V0.4 locked')}</small></article>
    <article class="status-item"><span>Graph profile</span><strong>${text(health.graph?.state || 'locked')}</strong><small>${text(health.graph?.url || 'V0.7 optional')}</small></article>
    <article class="status-item"><span>Index Alias</span><strong>${text(health.active_collection || health.collection_name)}</strong><small>${text(health.index_alias?.status || 'implicit default')}</small></article>
    <article class="status-item"><span>最近 Eval</span><strong>${text(evalText)}</strong><small>${text(lastEval?.assembly_version || '—')} · ${text(lastEval?.retrieval_mode || '—')}</small></article>`;
}

function renderDataQuality(report) {
  if (!report || report.status === 'not_run') {
    dataQualityStatus.textContent = '尚未运行';
    const failure = report?.last_failure;
    dataPipeline.innerHTML = `<p class="hint">尚未生成 Data Quality 报告。完成一次真实 CFPB 导入后，这里会显示每个生命周期状态。</p>${failure ? `<div class="quality-issues"><b>最近数据源故障：</b> ${text(failure.error || failure.message)}<br><small>${text(failure.next_action || '')}</small></div>` : ''}`;
    dataQualitySummary.innerHTML = '';
    return;
  }
  const stages = ['discovered', 'downloaded', 'validated', 'normalized', 'deduplicated', 'quarantined', 'embedded', 'indexed', 'active'];
  const labels = {discovered: '发现', downloaded: '下载', validated: '校验', normalized: '规范化', deduplicated: '去重', quarantined: '隔离', embedded: '向量化', indexed: '索引', active: 'Active'};
  const counts = report.stage_counts || {};
  dataQualityStatus.textContent = `快照 ${report.snapshot_id}`;
  dataPipeline.innerHTML = stages.map((stage) => {
    const count = Number(counts[stage] || 0);
    const blocked = stage === 'quarantined' && count > 0;
    const ready = ['indexed', 'active'].includes(stage) ? count > 0 : count >= Number(report.accepted_documents || 0);
    const state = blocked ? 'data-blocked' : ready ? 'data-ready' : 'data-warning';
    return `<article class="data-stage ${state}"><strong>${text(labels[stage])}</strong><small>${text(stage)}</small><b>${text(count)}</b></article>`;
  }).join('');
  const issues = (report.issues || []).slice(0, 5).map((issue) => `${issue.code}: ${issue.message}`).join(' · ');
  dataQualitySummary.innerHTML = `
    <article class="quality-stat"><span>原始文档</span><strong>${text(report.raw_documents)}</strong></article>
    <article class="quality-stat"><span>接受文档</span><strong>${text(report.accepted_documents)}</strong></article>
    <article class="quality-stat"><span>重复</span><strong>${text(report.duplicate_documents)}</strong></article>
    <article class="quality-stat"><span>隔离</span><strong>${text(report.quarantined_documents)}</strong></article>
    <article class="quality-stat"><span>已索引</span><strong>${text(report.indexed_documents)}</strong></article>
    <article class="quality-stat"><span>语言</span><strong>${text(Object.entries(report.languages || {}).map(([key, value]) => `${key}:${value}`).join(' · '))}</strong></article>
    <article class="quality-stat"><span>来源类型</span><strong>${text(Object.entries(report.source_types || {}).map(([key, value]) => `${key}:${value}`).join(' · '))}</strong></article>
    ${issues ? `<div class="quality-issues"><b>最近质量问题：</b> ${text(issues)}</div>` : ''}`;
}

function renderFrontier(payload) {
  if (!payload?.modules) return;
  const statusLabel = {implemented: '已实现', experimental: '实验开关', planned: '计划实验', locked: '质量门锁定'};
  frontierGrid.innerHTML = payload.modules.map((module) => `<article class="frontier-item ${text(module.status)}"><div class="frontier-meta"><span>${text(module.version)}</span><span>${text(statusLabel[module.status] || module.status)}</span></div><h3>${text(module.name)}</h3><p>${text(module.problem)}</p>${module.implementation ? `<small>实现状态：${text(module.implementation)}</small><br>` : ''}${module.last_eval ? `<small>最近实测：${text(module.last_eval)}</small><br>` : ''}<small>Trace：${text((module.trace_added || []).join(' → '))}</small><br><small>进入 Gate：${text(module.entry_gate)}</small><br><a href="${text(module.source)}" target="_blank" rel="noreferrer">查看原理来源</a>${module.secondary_source ? ` · <a href="${text(module.secondary_source)}" target="_blank" rel="noreferrer">工程指南</a>` : ''}</article>`).join('');
}

function renderLifecycle(payload) {
  if (!payload || !payload.stages) {
    lifecycleGrid.innerHTML = '<p class="error">无法读取项目阶段状态。</p>';
    return;
  }
  currentStage.textContent = `${text(payload.current_stage)} · ${text(payload.current_label)}`;
  lifecyclePrinciple.textContent = payload.principle;
  const statusClass = {completed: 'stage-completed', in_progress: 'stage-progress', experimental: 'stage-experimental', next: 'stage-next', locked: 'stage-locked', blocked: 'stage-blocked'};
  lifecycleGrid.innerHTML = payload.stages.map((stage) => `
    <article class="lifecycle-stage ${statusClass[stage.status] || 'stage-next'}">
      <div class="stage-top"><span class="stage-id">${text(stage.id)}</span><span class="stage-status">${text(stage.status_label)}</span></div>
      <h3>${text(stage.name)}</h3>
      <p class="stage-scope">${text(stage.scope)}</p>
      <dl><dt>当前证据</dt><dd>${text(stage.evidence)}</dd><dt>质量门</dt><dd>${text(stage.gate)}</dd><dt>下一步</dt><dd>${text(stage.next_action)}</dd></dl>
    </article>`).join('');
  renderStandards(payload.eval_standards);
}

function renderStandards(items) {
  if (!items) return;
  const statusClass = {passed: 'standard-passed', partial: 'standard-partial', blocked: 'standard-blocked', not_started: 'standard-not-started'};
  standardsGrid.innerHTML = items.map((item) => `
    <article class="standard-item ${statusClass[item.status] || 'standard-not-started'}">
      <div class="standard-top"><span class="standard-id">${text(item.id)}</span><span class="standard-status">${text(item.status_label)}</span></div>
      <h3>${text(item.name)}</h3>
      <dl><dt>当前</dt><dd>${text(item.actual)}</dd><dt>企业目标</dt><dd>${text(item.target)}</dd></dl>
      <p>${text(item.enterprise_value)}</p>
    </article>`).join('');
}

async function loadStatus() {
  try {
    const [healthResponse, evalResponse, lifecycleResponse, qualityResponse, answerEvalResponse, frontierResponse] = await Promise.all([fetch('/api/health'), fetch('/api/eval/last'), fetch('/api/lifecycle'), fetch('/api/data-quality'), fetch('/api/eval/answer-last'), fetch('/api/frontier/modules')]);
    const health = await healthResponse.json();
    const lastEval = await evalResponse.json();
    const lifecycle = await lifecycleResponse.json();
    const quality = await qualityResponse.json();
    const answerEval = await answerEvalResponse.json();
    const frontier = await frontierResponse.json();
    renderStatus(health, lastEval);
    renderEval(lastEval);
    renderLifecycle(lifecycle);
    renderDataQuality(quality);
    renderAnswerEval(answerEval);
    renderFrontier(frontier);
  } catch (error) {
    statusGrid.innerHTML = `<p class="error">读取状态失败：${text(error.message)}</p>`;
  }
}

document.querySelectorAll('.pipeline-node').forEach((node) => {
  node.addEventListener('click', () => {
    renderComponentInspector(node.dataset.component);
    const row = document.querySelector(`[data-trace-name="${node.dataset.component}"]`);
    if (row) {
      row.scrollIntoView({behavior: 'smooth', block: 'center'});
      row.querySelector('.trace-main').click();
    }
  });
});

pipeline.addEventListener('click', (event) => {
  const node = event.target.closest('.pipeline-node');
  if (!node) return;
  renderComponentInspector(node.dataset.component);
  const row = document.querySelector(`[data-trace-name="${node.dataset.component}"]`);
  if (row) {
    row.scrollIntoView({behavior: 'smooth', block: 'center'});
    row.querySelector('.trace-main').click();
  }
});

document.querySelectorAll('.diagram-node').forEach((node) => {
  node.addEventListener('click', () => {
    renderComponentInspector(node.dataset.component);
    const row = document.querySelector(`[data-trace-name="${node.dataset.component}"]`);
    if (row) {
      row.scrollIntoView({behavior: 'smooth', block: 'center'});
      row.querySelector('.trace-main').click();
    }
  });
});

function renderSources(items) {
  sources.innerHTML = items.map((source) => `
    <article class="source-card ${text(source.authority_level)}">
      <div class="source-title"><strong>[${text(source.citation)}] ${text(source.source_type)}</strong><span>分数 ${text(source.score)}</span></div>
      <h3>${text(source.title)}</h3>
      <p>${text(source.text)}</p>
      <dl><dt>Authority</dt><dd>${text(source.authority_level)}</dd><dt>Issue</dt><dd>${text(source.metadata.issue)}</dd><dt>Response</dt><dd>${text(source.metadata.company_response)}</dd><dt>Published</dt><dd>${text(source.published_at)}</dd></dl>
      <a href="${text(source.source_url)}" target="_blank" rel="noreferrer">查看 CFPB 原始来源${source.complaint_id ? ` ${text(source.complaint_id)}` : ''}</a>
    </article>`).join('');
}

async function runRetrievePreview() {
  previewButton.disabled = true;
  previewButton.textContent = '检索中…';
  answer.textContent = '正在运行 Embedding 和检索分支（不会调用 Chat LLM）…';
  sources.innerHTML = '';
  result.classList.remove('hidden');
  renderTrace([], '');
  try {
    const body = await streamRetrievePreview(questionInput.value, retrievalMode.value);
    answer.textContent = `检索预览完成：召回 ${body.sources.length} 条证据。此模式没有调用 Chat LLM。`;
    guardrail.textContent = `Trace: ${body.trace_id} · 模式：${body.retrieval_mode} · 现在可以展开下方 Trace。`;
    executionStatus.innerHTML = `<strong>检索完成：${text(body.retrieval_mode)}</strong><span>已召回 ${text(body.sources.length)} 条证据，未调用 Chat LLM。</span><small>现在可以点击右侧节点对照每一步 Trace。</small>`;
    renderTrace(body.trace, body.trace_id);
    renderSources(body.sources);
  } catch (error) {
    answer.textContent = `失败：${error.message}`;
  } finally {
    previewButton.disabled = false;
    previewButton.textContent = '只运行检索 Trace';
  }
}

async function streamRetrievePreview(question, mode) {
  const response = await fetch('/api/retrieve-stream', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question, retrieval_mode: mode, assembly_version: assemblyVersion.value})});
  if (!response.ok || !response.body) throw new Error('检索流无法启动');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let traceIdValue = '';
  let events = [];
  let resultBody = null;
  const handleLine = (line) => {
    if (!line.trim()) return;
    const message = JSON.parse(line);
    if (message.type === 'meta') {
      traceIdValue = message.trace_id;
      renderTrace([], traceIdValue);
      executionStatus.textContent = `开始执行 ${message.assembly_version || assemblyVersion.value} · ${message.retrieval_mode === 'hybrid' ? 'Hybrid Dense + BM25 + RRF' : 'Dense'} 检索…`;
    } else if (message.type === 'trace') {
      events = upsertTraceEvent(events, message.event);
      renderTrace(events, traceIdValue);
      updateExecutionStatus(message.event);
      answer.textContent = `${message.event.status === 'running' ? '正在执行' : '已完成'}：${message.event.summary}`;
    } else if (message.type === 'result') {
      resultBody = message;
    } else if (message.type === 'error') {
      throw new Error(message.detail || '检索流失败');
    }
  };
  while (true) {
    const {value, done} = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), {stream: !done});
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    lines.forEach(handleLine);
    if (done) break;
  }
  if (buffer.trim()) handleLine(buffer);
  if (!resultBody) throw new Error('检索流结束但没有结果');
  resultBody.trace = resultBody.trace || events;
  return resultBody;
}

previewButton.addEventListener('click', runRetrievePreview);

refreshStatus.addEventListener('click', loadStatus);
document.querySelectorAll('.example-question').forEach((button) => {
  button.addEventListener('click', () => {
    questionInput.value = button.dataset.question;
    questionInput.focus();
  });
});

document.querySelectorAll('.version-button').forEach((button) => {
  button.addEventListener('click', () => { manualVersionSelection = true; selectAssemblyVersion(button.dataset.version); });
});
evalVersion.addEventListener('change', () => { manualVersionSelection = true; selectAssemblyVersion(evalVersion.value); });
queryVersion.addEventListener('change', () => { manualVersionSelection = true; selectAssemblyVersion(queryVersion.value); });
selectAssemblyVersion(assemblyVersion.value || 'v0_3');

evalRun.addEventListener('click', async () => {
  evalRun.disabled = true;
  evalRun.textContent = '评测中…';
  evalSummary.innerHTML = `<p class="hint">正在使用 ${evalBenchmark.value === 'v0_3' ? '50 条 Golden Draft' : 'Seed'} 运行检索问题；不会调用慢速 Chat LLM。</p>`;
  try {
    selectAssemblyVersion(evalVersion.value);
    const response = await fetch(`/api/eval/run?retrieval_mode=${encodeURIComponent(evalMode.value)}&assembly_version=${encodeURIComponent(evalVersion.value)}&benchmark_version=${encodeURIComponent(evalBenchmark.value)}`, {method: 'POST'});
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || 'Eval 失败');
    renderEval(body);
  } catch (error) {
    evalSummary.innerHTML = `<p class="error">失败：${text(error.message)}</p>`;
  } finally {
    evalRun.disabled = false;
    evalRun.textContent = '运行检索评测';
  }
});

answerEvalRun.addEventListener('click', async () => {
  answerEvalRun.disabled = true;
  answerEvalRun.textContent = 'R1 评测中…';
  answerEvalSummary.innerHTML = '<p class="hint">正在调用本地 DeepSeek-R1，逐条检查引用覆盖、拒答和危险声明；这一步可能比检索 Eval 慢。</p>';
  try {
    const response = await fetch(`/api/eval/answer-run?assembly_version=${encodeURIComponent(evalVersion.value)}&benchmark_version=${encodeURIComponent(evalBenchmark.value)}`, {method: 'POST'});
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || '回答 Eval 失败');
    renderAnswerEval(body);
  } catch (error) {
    answerEvalSummary.innerHTML = `<p class="error">失败：${text(error.message)}</p>`;
  } finally {
    answerEvalRun.disabled = false;
    answerEvalRun.textContent = '运行回答/安全 Eval';
  }
});

loadStatus();

ingestForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  ingestStatus.textContent = '正在下载真实 CFPB 投诉、抓取官方指导，请 LM Studio 生成向量并写入 Qdrant…';
  try {
    const response = await fetch('/api/ingest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        limit: Number(document.querySelector('#limit').value),
        year: Number(document.querySelector('#year').value),
      }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || '导入失败');
    ingestStatus.textContent = `完成：取得 ${body.fetched_complaints} 条有公开叙述的真实投诉、${body.guidance_documents} 个官方指导 Chunk，共索引 ${body.indexed_documents} 条可追溯证据。`;
  } catch (error) {
    ingestStatus.textContent = `失败：${error.message}`;
  }
});

queryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  queryButton.disabled = true;
  previewButton.disabled = true;
  answer.textContent = '正在先运行 Embedding 和检索，完成后再交给 Chat LLM…';
  sources.innerHTML = '';
  renderTrace([], '');
  result.classList.remove('hidden');
  try {
    const previewBody = await streamRetrievePreview(questionInput.value, retrievalMode.value);
    renderSources(previewBody.sources);
    guardrail.textContent = `检索已完成 · Trace: ${previewBody.trace_id} · 正在等待 Chat LLM 生成…`;
    const pendingTrace = [...previewBody.trace, {
      step: previewBody.trace.length + 1,
      name: 'generate_answer',
      status: 'pending',
      duration_ms: 0,
      summary: '等待 Chat LLM 返回正文…',
      details: {model: 'LM Studio Chat', status: 'pending'},
    }];
    renderTrace(pendingTrace, previewBody.trace_id);
    answer.textContent = '检索已完成，证据卡片已经显示；现在等待 Chat LLM 生成回答（本地模型可能需要 1–3 分钟）…';
    const response = await fetch('/api/query', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: document.querySelector('#question').value, retrieval_mode: retrievalMode.value, assembly_version: assemblyVersion.value}),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || '查询失败');
    answer.textContent = body.answer;
    const safetyText = body.safety_flags?.length ? ` · 安全标记：${body.safety_flags.join(', ')}` : '';
    guardrail.textContent = `${body.guardrail} Trace: ${body.trace_id} · 引用 ID：${body.citation_valid ? '通过' : '需要人工复核'} · 事实句引用覆盖率：${body.citation_coverage ?? '—'}${body.needs_human_review ? ' · 已降级人工复核' : ''}${safetyText}`;
    renderTrace(body.trace, body.trace_id);
    renderSources(body.sources);
  } catch (error) {
    answer.textContent = `失败：${error.message}`;
    guardrail.textContent = '检索 Trace 仍然保留在下方；如果 Chat LLM 失败，可以先使用“只运行检索 Trace”。';
  } finally {
    queryButton.disabled = false;
    previewButton.disabled = false;
  }
});
