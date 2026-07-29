// AI-assisted disclosure (non-core): dashboard UI wiring, CSV loading,
// filtering, and local review-log helpers. Core modeling algorithms are in src/.
const DATASETS = {
  parsed: "../data/parsed_documents_index.csv",
  topics: "../outputs/topic_discovery/topic_summary_refined.csv",
  assignments: "../outputs/topic_discovery/topic_assignments.csv",
  classification: "../outputs/document_classification/classification_results.csv",
  classificationSummary: "../outputs/document_classification/classification_summary.csv",
  reviewQueue: "../outputs/document_classification/review_queue.csv",
  priority: "../outputs/review_prioritization/review_priority_results.csv",
  prioritySummary: "../outputs/review_prioritization/review_priority_summary.csv",
  resourcePlan: "../outputs/review_prioritization/resource_plan.csv",
  resourceAllocations: "../outputs/review_prioritization/resource_allocations.csv",
  auditSamples: "../notes/manual_review/problem2_k160_boundary_audit_samples.csv",
};

const requestedView = new URLSearchParams(window.location.search).get("view") || "overview";

const state = {
  view: requestedView,
  search: "",
  selected: null,
  sort: {},
  page: {},
  filters: {},
  data: {
    parsed: [],
    topics: [],
    assignments: [],
    classification: [],
    classificationSummary: [],
    reviewQueue: [],
    priority: [],
    prioritySummary: [],
    resourcePlan: [],
    resourceAllocations: [],
    auditSamples: [],
  },
  maps: {
    parsed: new Map(),
    classification: new Map(),
    priority: new Map(),
    audit: new Map(),
  },
  reviewLogs: [],
  topicsAll: [],
};

const pageSize = 25;
const titles = {
  overview: "总览",
  parse: "解析监控",
  topics: "主题发现",
  classification: "分类结果",
  review: "待复核队列",
  audit: "人工核查",
  resources: "资源场景",
};

const $ = (selector) => document.querySelector(selector);
const content = $("#content");
const drawer = $("#drawer");

// AI-assisted disclosure (non-core): browser-side CSV parsing for result display.
function parseCSV(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (inQuotes) {
      if (char === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        cell += char;
      }
    } else if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(cell);
      cell = "";
    } else if (char === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (char !== "\r") {
      cell += char;
    }
  }
  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }

  const headers = (rows.shift() || []).map((item) => item.replace(/^\ufeff/, ""));
  return rows
    .filter((items) => items.some((item) => item !== ""))
    .map((items) => {
      const record = {};
      headers.forEach((header, index) => {
        record[header] = items[index] ?? "";
      });
      return record;
    });
}

async function loadCSV(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} ${response.status}`);
  }
  return parseCSV(await response.text());
}

async function loadData() {
  $("#loadState").textContent = "正在加载数据...";
  const entries = Object.entries(DATASETS);
  const results = await Promise.all(entries.map(([key, path]) => loadCSV(path).then((rows) => [key, rows])));
  results.forEach(([key, rows]) => {
    state.data[key] = rows;
  });
  buildMaps();
  $("#loadState").textContent = `已加载 ${formatInt(state.data.classification.length)} 条分类记录`;
}

function buildMaps() {
  state.maps.parsed = new Map(state.data.parsed.map((row) => [row.doc_id, row]));
  state.maps.classification = new Map(state.data.classification.map((row) => [row.doc_id, row]));
  state.maps.priority = new Map(state.data.priority.map((row) => [row.doc_id, row]));
  state.maps.audit = new Map(state.data.auditSamples.map((row) => [row.doc_id, row]));
  state.data.classificationView = state.data.classification.map((row) => ({
    ...(state.maps.parsed.get(row.doc_id) || {}),
    ...row,
    review_local_status: getLatestLog(row.doc_id)?.status || "pending",
  }));
  state.data.priorityView = state.data.priority.map((row) => ({
    ...(state.maps.classification.get(row.doc_id) || {}),
    ...row,
    review_local_status: getLatestLog(row.doc_id)?.status || "pending",
  }));
  state.data.auditView = state.data.auditSamples.map((row) => ({
    ...(state.maps.parsed.get(row.doc_id) || {}),
    ...(state.maps.classification.get(row.doc_id) || {}),
    ...(state.maps.priority.get(row.doc_id) || {}),
    ...row,
    title: row.title_snippet || row.title || row.file_name || row.doc_id,
    review_local_status: getLatestLog(row.doc_id)?.status || row.manual_decision || "pending",
  }));
  state.topicsAll = unique(
    [...state.data.classification.map((row) => row.topic_name), ...state.data.priority.map((row) => row.topic_name)]
      .filter(Boolean)
  ).sort((a, b) => a.localeCompare(b, "zh-CN"));
}

// AI-assisted disclosure (non-core): localStorage helpers for manual review notes.
function loadLogs() {
  try {
    state.reviewLogs = JSON.parse(localStorage.getItem("bdocReviewLogs") || "[]");
  } catch {
    state.reviewLogs = [];
  }
}

function saveLog(log, options = { openDrawer: true }) {
  state.reviewLogs.unshift(log);
  localStorage.setItem("bdocReviewLogs", JSON.stringify(state.reviewLogs.slice(0, 2000)));
  buildMaps();
  render();
  if (options.openDrawer) {
    openDrawer(log.doc_id);
  }
}

function getLatestLog(docId) {
  return state.reviewLogs.find((item) => item.doc_id === docId);
}

function unique(values) {
  return [...new Set(values.map((item) => String(item || "").trim()).filter(Boolean))];
}

function num(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function formatInt(value) {
  return Math.round(num(value)).toLocaleString("zh-CN");
}

function score(value) {
  return num(value).toFixed(3);
}

function percent(value) {
  return `${(num(value) * 100).toFixed(1)}%`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function labelFor(value) {
  const map = {
    assigned: "已归类",
    multi_class: "多类待判",
    unclassifiable: "无法归类",
    auto_archive: "自动归档",
    review_if_capacity: "容量允许复核",
    must_review: "必须复核",
    high: "高",
    medium: "中",
    low: "低",
    pending: "待处理",
    confirmed: "已确认",
    changed: "已改类",
    rejected: "已驳回",
    noise: "噪声无效",
    uncertain: "暂不确定",
    education_dataset3_assigned: "教育已归类",
    education_dataset3_multiclass: "教育多类",
    government_dataset2_assigned: "政府已归类",
    government_dataset3_multiclass: "政府多类",
    fallback_comprehensive_nonempty: "综合待判",
    multiclass_highrisk: "高风险多类",
    unclassifiable_all: "无法归类",
  };
  return map[value] || value || "-";
}

function badge(value) {
  const normalized = String(value || "").trim();
  const colors = {
    assigned: "green",
    auto_archive: "green",
    confirmed: "green",
    low: "green",
    multi_class: "amber",
    review_if_capacity: "blue",
    medium: "amber",
    changed: "blue",
    pending: "gray",
    high: "red",
    unclassifiable: "red",
    must_review: "red",
    rejected: "red",
    noise: "red",
    uncertain: "amber",
    education_dataset3_assigned: "blue",
    education_dataset3_multiclass: "amber",
    government_dataset2_assigned: "teal",
    government_dataset3_multiclass: "amber",
    fallback_comprehensive_nonempty: "gray",
    multiclass_highrisk: "red",
    unclassifiable_all: "red",
    ok: "green",
    needs_ocr: "amber",
    empty: "gray",
    error: "red",
  };
  return `<span class="badge ${colors[normalized] || "gray"}">${escapeHtml(labelFor(normalized))}</span>`;
}

function badges(value) {
  const values = String(value || "")
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean);
  if (!values.length) {
    return badge("");
  }
  return `<div class="badge-list">${values.map((item) => badge(item)).join("")}</div>`;
}

function scoreBar(value) {
  const width = Math.max(0, Math.min(100, num(value) * 100));
  return `<div class="score"><small>${score(value)}</small><div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div></div>`;
}

function rowMatchesSearch(row) {
  if (!state.search) {
    return true;
  }
  const text = [
    row.doc_id,
    row.title,
    row.file_name,
    row.topic_name,
    row.topic_parent_name,
    row.classification_status,
    row.risk_level,
    row.priority_level,
    row.primary_audit_bucket,
    row.audit_bucket,
    row.title_snippet,
    row.content_snippet,
    row.topic_split_reason,
    row.review_reason,
  ].join(" ").toLowerCase();
  return text.includes(state.search.toLowerCase());
}

function getFilter(view, key) {
  return state.filters[view]?.[key] || "";
}

function setFilter(view, key, value) {
  state.filters[view] = { ...(state.filters[view] || {}), [key]: value };
  state.page[view] = 1;
  render();
}

// AI-assisted disclosure (non-core): table search/filter helpers for the dashboard.
function applyFilters(view, rows, filters) {
  return rows.filter((row) => {
    if (!rowMatchesSearch(row)) {
      return false;
    }
    return filters.every(({ key, value, type }) => {
      if (!value) {
        return true;
      }
      if (type === "min") {
        return num(row[key]) >= num(value);
      }
      if (type === "max") {
        return num(row[key]) <= num(value);
      }
      return String(row[key] || "") === String(value);
    });
  });
}

function sortRows(view, rows) {
  const sortState = state.sort[view];
  if (!sortState?.key) {
    return rows;
  }
  const { key, dir } = sortState;
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    const an = Number(av);
    const bn = Number(bv);
    if (Number.isFinite(an) && Number.isFinite(bn)) {
      return (an - bn) * sign;
    }
    return String(av || "").localeCompare(String(bv || ""), "zh-CN") * sign;
  });
}

function countBy(rows, key) {
  const map = new Map();
  rows.forEach((row) => {
    const value = String(row[key] || "未标注");
    map.set(value, (map.get(value) || 0) + 1);
  });
  return [...map.entries()].sort((a, b) => b[1] - a[1]);
}

function bars(title, subtitle, entries, color = "var(--blue)") {
  const max = Math.max(1, ...entries.map((item) => item[1]));
  return `
    <div class="panel">
      <div class="panel-head"><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(subtitle)}</p></div></div>
      <div class="bars">
        ${entries
          .map(([name, value]) => `
            <div class="bar-row">
              <span class="truncate narrow">${escapeHtml(labelFor(name))}</span>
              <div class="bar-track"><div class="bar-fill" style="width:${(value / max) * 100}%;background:${color}"></div></div>
              <span class="num">${formatInt(value)}</span>
            </div>
          `)
          .join("")}
      </div>
    </div>
  `;
}

function kpi(label, value, hint) {
  return `<div class="kpi"><span>${escapeHtml(label)}</span><strong>${formatInt(value)}</strong><small>${escapeHtml(hint || "")}</small></div>`;
}

function renderOverview() {
  const parsed = state.data.parsed;
  const cls = state.data.classificationView || [];
  const priority = state.data.priorityView || [];
  const overviewQueue = applyFilters("overview", priority, [
    { key: "priority_level", value: getFilter("overview", "priority_level") },
    { key: "recommended_action", value: getFilter("overview", "recommended_action") },
    { key: "dataset", value: getFilter("overview", "dataset") },
  ]);
  const queuePreview = sortRows("overview", overviewQueue).slice(0, 12);
  const reviewCount = cls.filter((row) => row.review_flag === "1").length || state.data.reviewQueue.length;
  const autoCount = cls.filter((row) => row.review_decision === "auto_archive").length;
  const highRisk = cls.filter((row) => row.risk_level === "high").length;
  const confirmed = state.reviewLogs.filter((row) => row.status !== "pending").length;
  const resourceCards = state.data.resourcePlan
    .map(
      (row) => `
        <article class="mini-scenario">
          <b>${escapeHtml(row.scenario_id)}</b>
          <span>人工复核 ${formatInt(row.manual_review_selected)} / 延期 ${formatInt(row.deferred_review_count)}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, (num(row.used_manual_hours) / Math.max(1, num(row.manual_hours))) * 100)}%"></div></div>
          <small>已用 ${score(row.used_manual_hours)}h / ${score(row.manual_hours)}h</small>
        </article>
      `
    )
    .join("");

  content.innerHTML = `
    <div class="section">
      <div class="kpi-grid">
        ${kpi("总解析文档数", parsed.length, "含数据集 3 行展开记录")}
        ${kpi("历史主题簇数", state.data.topics.length, "问题一主题体系")}
        ${kpi("新数据分类总数", cls.length, "数据集 2 + 数据集 3")}
        ${kpi("自动归档数量", autoCount, "review_decision = auto_archive")}
        ${kpi("待复核数量", reviewCount, "模型建议进入人工复核")}
        ${kpi("高风险数量", highRisk, "risk_level = high")}
      </div>
      <div class="panel">
        <div class="panel-head"><div><h3>业务流程</h3><p>模型输出到人工复核和资源调度</p></div><span>${formatInt(confirmed)} 条本地复核日志</span></div>
        <div class="flow">
          <div class="flow-step"><b>多源文件解析</b><span>Word、PDF、Excel、图片、文本统一抽取</span></div>
          <div class="flow-step"><b>历史主题体系</b><span>数据集 1 聚类并校准内容主题族</span></div>
          <div class="flow-step"><b>新数据归类</b><span>数据集 2/3 匹配主题原型</span></div>
          <div class="flow-step"><b>风险分级</b><span>错分风险、紧急程度、复核必要性</span></div>
          <div class="flow-step"><b>人工复核</b><span>确认、改类、无法归类、驳回</span></div>
          <div class="flow-step"><b>资源调度</b><span>S1/S2/S3 场景下排序分配</span></div>
        </div>
      </div>
      <div class="grid-2 focus-grid">
        <div class="panel review-console">
          <div class="panel-head">
            <div><h3>一屏复核控制台</h3><p>按优先级排序，可在总览页直接处理人工审查队列</p></div>
            <span>${formatInt(overviewQueue.length)} 条匹配</span>
          </div>
          <div class="filters compact-filters">
            ${filterSelect("overview", "priority_level", "优先级", priority)}
            ${filterSelect("overview", "recommended_action", "建议动作", priority)}
            ${filterSelect("overview", "dataset", "数据集", priority)}
          </div>
          <div class="table-wrap compact-table">
            <table>
              <thead>
                <tr>
                  <th>排序</th>
                  <th>文档</th>
                  <th>优先级</th>
                  <th>综合分</th>
                  <th>快速处理</th>
                </tr>
              </thead>
              <tbody>
                ${
                  queuePreview.length
                    ? queuePreview
                        .map(
                          (row) => `
                            <tr class="row-click" data-doc-id="${escapeHtml(row.doc_id || "")}">
                              <td class="num">${formatInt(row.priority_rank)}</td>
                              <td>
                                <div class="truncate overview-title">${escapeHtml(row.title || row.doc_id)}</div>
                                <small>${escapeHtml(row.doc_id)} · ${escapeHtml(row.dataset)} · ${escapeHtml(row.topic_name)}</small>
                              </td>
                              <td>${badge(row.priority_level)}</td>
                              <td>${scoreBar(row.priority_score)}</td>
                              <td>
                                <div class="quick-actions">
                                  <button type="button" data-quick-action="confirmed" data-doc-id="${escapeHtml(row.doc_id)}">确认</button>
                                  <button type="button" data-quick-action="unclassifiable" data-doc-id="${escapeHtml(row.doc_id)}">待判</button>
                                  <button type="button" data-quick-action="rejected" data-doc-id="${escapeHtml(row.doc_id)}">驳回</button>
                                </div>
                              </td>
                            </tr>
                          `
                        )
                        .join("")
                    : `<tr><td colspan="5"><div class="empty">没有匹配的复核记录</div></td></tr>`
                }
              </tbody>
            </table>
          </div>
          <div class="console-foot">
            <span>点击行可打开详情抽屉进行改类和备注；快速按钮会直接写入本地复核日志。</span>
            <button class="action-btn" data-view-jump="review" type="button">查看完整队列</button>
          </div>
        </div>
        <div class="panel">
          <div class="panel-head"><div><h3>资源场景摘要</h3><p>问题三 S1/S2/S3 资源约束结果</p></div></div>
          <div class="mini-scenario-list">${resourceCards}</div>
          <div class="recent-logs">
            <h4>最近复核留痕</h4>
            ${
              state.reviewLogs.length
                ? state.reviewLogs
                    .slice(0, 5)
                    .map((log) => `<div class="log-item"><b>${escapeHtml(labelFor(log.status))}</b> · ${escapeHtml(log.doc_id)}<br />${escapeHtml(log.original_topic)} → ${escapeHtml(log.final_topic || "-")}</div>`)
                    .join("")
                : `<div class="empty">暂无人工复核操作</div>`
            }
          </div>
        </div>
      </div>
      <div class="grid-2">
        ${bars("数据集分布", "解析索引表 parsed_documents_index.csv", countBy(parsed, "dataset"))}
        ${bars("分类状态分布", "classification_status", countBy(cls, "classification_status"), "var(--teal)")}
      </div>
      <div class="grid-2">
        ${bars("风险等级分布", "risk_level", countBy(cls, "risk_level"), "var(--amber)")}
        ${bars("复核优先级分布", "priority_level", countBy(priority, "priority_level"), "var(--blue)")}
      </div>
    </div>
  `;
}

function filterSelect(view, key, label, rows, field = key) {
  const options = unique(rows.map((row) => row[field])).sort((a, b) => a.localeCompare(b, "zh-CN"));
  return `
    <label class="filter"><span>${escapeHtml(label)}</span>
      <select data-filter-view="${view}" data-filter-key="${key}">
        <option value="">全部</option>
        ${options.map((item) => `<option value="${escapeHtml(item)}" ${getFilter(view, key) === item ? "selected" : ""}>${escapeHtml(labelFor(item))}</option>`).join("")}
      </select>
    </label>
  `;
}

function numericFilter(view, key, label, type) {
  return `
    <label class="filter"><span>${escapeHtml(label)}</span>
      <input data-filter-view="${view}" data-filter-key="${key}" data-filter-type="${type}" type="number" step="0.01" value="${escapeHtml(getFilter(view, key))}" />
    </label>
  `;
}

function renderTable({ view, rows, columns, filtersHtml = "", empty = "没有匹配记录" }) {
  const currentPage = state.page[view] || 1;
  const sorted = sortRows(view, rows);
  const pages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const page = Math.min(currentPage, pages);
  state.page[view] = page;
  const visible = sorted.slice((page - 1) * pageSize, page * pageSize);
  const sortState = state.sort[view] || {};

  return `
    <div class="panel">
      ${filtersHtml ? `<div class="filters">${filtersHtml}</div>` : ""}
      <div class="table-wrap">
        <table>
          <thead><tr>
            ${columns
              .map((column) => `<th class="${column.sortable === false ? "" : "sortable"}" data-sort-view="${view}" data-sort-key="${column.key}">
                ${escapeHtml(column.label)}${sortState.key === column.key ? (sortState.dir === "asc" ? " ↑" : " ↓") : ""}
              </th>`)
              .join("")}
          </tr></thead>
          <tbody>
            ${
              visible.length
                ? visible
                    .map((row) => `<tr class="row-click" data-doc-id="${escapeHtml(row.doc_id || "")}">
                      ${columns.map((column) => `<td>${column.render ? column.render(row) : escapeHtml(row[column.key] || "")}</td>`).join("")}
                    </tr>`)
                    .join("")
                : `<tr><td colspan="${columns.length}"><div class="empty">${escapeHtml(empty)}</div></td></tr>`
            }
          </tbody>
        </table>
      </div>
      <div class="pager">
        <span>共 ${formatInt(sorted.length)} 条，当前第 ${formatInt(page)} / ${formatInt(pages)} 页</span>
        <div class="pager-actions">
          <button data-page-view="${view}" data-page-delta="-1" ${page <= 1 ? "disabled" : ""}>上一页</button>
          <button data-page-view="${view}" data-page-delta="1" ${page >= pages ? "disabled" : ""}>下一页</button>
        </div>
      </div>
    </div>
  `;
}

function renderParse() {
  const view = "parse";
  const rows = applyFilters(view, state.data.parsed, [
    { key: "dataset", value: getFilter(view, "dataset") },
    { key: "suffix", value: getFilter(view, "suffix") },
    { key: "parse_status", value: getFilter(view, "parse_status") },
    { key: "char_count", value: getFilter(view, "min_char"), type: "min" },
  ]);

  content.innerHTML = renderTable({
    view,
    rows,
    filtersHtml: [
      filterSelect(view, "dataset", "数据集", state.data.parsed),
      filterSelect(view, "suffix", "格式", state.data.parsed),
      filterSelect(view, "parse_status", "解析状态", state.data.parsed),
      numericFilter(view, "min_char", "最小字符数", "min"),
    ].join(""),
    columns: [
      { key: "doc_id", label: "doc_id" },
      { key: "dataset", label: "数据集", render: (row) => badge(row.dataset) },
      { key: "file_name", label: "文件名", render: (row) => `<div class="truncate narrow">${escapeHtml(row.file_name)}</div>` },
      { key: "suffix", label: "格式" },
      { key: "title", label: "标题", render: (row) => `<div class="truncate">${escapeHtml(row.title)}</div>` },
      { key: "parse_status", label: "状态", render: (row) => badge(row.parse_status) },
      { key: "char_count", label: "字符数", render: (row) => `<span class="num">${formatInt(row.char_count)}</span>` },
      { key: "parse_notes", label: "解析备注", render: (row) => `<div class="truncate narrow">${escapeHtml(row.parse_notes)}</div>` },
    ],
  });
}

function renderTopics() {
  const rows = state.data.topics.filter(rowMatchesSearch);
  const maxSize = Math.max(1, ...state.data.topics.map((row) => num(row.size)));
  content.innerHTML = `
    <div class="section">
      <div class="grid-2">
        <div class="panel">
          <div class="panel-head"><div><h3>主题簇列表</h3><p>问题一：历史文件内容主题体系</p></div></div>
          <div class="topic-list">
            ${rows
              .map((row) => `
                <article class="topic-card row-click" data-doc-id="${escapeHtml(row.representatives || row.cluster_id)}" data-topic-id="${escapeHtml(row.cluster_id)}">
                  <h4>${escapeHtml(row.cluster_id)} · ${escapeHtml(row.topic_name)}</h4>
                  <div class="topic-meta">
                    <span>规模 ${formatInt(row.size)}</span>
                    <span>占比 ${percent(row.share)}</span>
                    <span>均值置信 ${score(row.mean_confidence)}</span>
                  </div>
                  <div class="bar-track" style="margin-top:10px"><div class="bar-fill" style="width:${(num(row.size) / maxSize) * 100}%"></div></div>
                  <div class="keyword-line">${escapeHtml(row.top_terms || row.family_reason || "")}</div>
                </article>
              `)
              .join("")}
          </div>
        </div>
        ${bars("主题规模", "topic_summary_refined.csv", state.data.topics.map((row) => [row.topic_name, num(row.size)]), "var(--teal)")}
      </div>
      ${renderTable({
        view: "topics",
        rows,
        columns: [
          { key: "cluster_id", label: "簇 ID" },
          { key: "topic_name", label: "内容主题" },
          { key: "raw_topic_name", label: "原始主题" },
          { key: "size", label: "规模", render: (row) => `<span class="num">${formatInt(row.size)}</span>` },
          { key: "share", label: "占比", render: (row) => percent(row.share) },
          { key: "top_terms", label: "关键词", render: (row) => `<div class="truncate">${escapeHtml(row.top_terms)}</div>` },
          { key: "representatives", label: "代表文档", render: (row) => `<div class="truncate">${escapeHtml(row.representatives)}</div>` },
        ],
      })}
    </div>
  `;
}

function renderClassification() {
  const view = "classification";
  const source = state.data.classificationView || [];
  const rows = applyFilters(view, source, [
    { key: "dataset", value: getFilter(view, "dataset") },
    { key: "topic_name", value: getFilter(view, "topic_name") },
    { key: "classification_status", value: getFilter(view, "classification_status") },
    { key: "risk_level", value: getFilter(view, "risk_level") },
    { key: "review_decision", value: getFilter(view, "review_decision") },
    { key: "confidence_score", value: getFilter(view, "min_conf"), type: "min" },
  ]);

  content.innerHTML = renderTable({
    view,
    rows,
    filtersHtml: [
      filterSelect(view, "dataset", "数据集", source),
      filterSelect(view, "topic_name", "主题", source),
      filterSelect(view, "classification_status", "分类状态", source),
      filterSelect(view, "risk_level", "风险", source),
      filterSelect(view, "review_decision", "复核建议", source),
      numericFilter(view, "min_conf", "最低置信度", "min"),
    ].join(""),
    columns: [
      { key: "doc_id", label: "doc_id" },
      { key: "dataset", label: "数据集", render: (row) => badge(row.dataset) },
      { key: "title", label: "标题", render: (row) => `<div class="truncate">${escapeHtml(row.title)}</div>` },
      { key: "topic_name", label: "类别", render: (row) => `<div class="truncate narrow">${escapeHtml(row.topic_name)}</div>` },
      { key: "classification_status", label: "状态", render: (row) => badge(row.classification_status) },
      { key: "confidence_score", label: "置信度", render: (row) => scoreBar(row.confidence_score) },
      { key: "score_margin", label: "分差", render: (row) => `<span class="num">${score(row.score_margin)}</span>` },
      { key: "risk_level", label: "风险", render: (row) => badge(row.risk_level) },
      { key: "review_decision", label: "建议", render: (row) => badge(row.review_decision) },
      { key: "review_local_status", label: "人工状态", render: (row) => badge(row.review_local_status) },
      { key: "evidence_terms", label: "证据词", render: (row) => `<div class="truncate narrow">${escapeHtml(row.evidence_terms)}</div>` },
    ],
  });
}

function renderReview() {
  const view = "review";
  const source = state.data.priorityView || [];
  if (!state.sort[view]) {
    state.sort[view] = { key: "priority_rank", dir: "asc" };
  }
  const rows = applyFilters(view, source, [
    { key: "priority_level", value: getFilter(view, "priority_level") },
    { key: "recommended_action", value: getFilter(view, "recommended_action") },
    { key: "dataset", value: getFilter(view, "dataset") },
    { key: "topic_name", value: getFilter(view, "topic_name") },
    { key: "risk_level", value: getFilter(view, "risk_level") },
  ]);

  content.innerHTML = renderTable({
    view,
    rows,
    filtersHtml: [
      filterSelect(view, "priority_level", "优先级", source),
      filterSelect(view, "recommended_action", "动作", source),
      filterSelect(view, "dataset", "数据集", source),
      filterSelect(view, "topic_name", "主题", source),
      filterSelect(view, "risk_level", "风险", source),
    ].join(""),
    columns: [
      { key: "priority_rank", label: "排序", render: (row) => `<span class="num">${formatInt(row.priority_rank)}</span>` },
      { key: "doc_id", label: "doc_id" },
      { key: "dataset", label: "数据集", render: (row) => badge(row.dataset) },
      { key: "title", label: "标题", render: (row) => `<div class="truncate">${escapeHtml(row.title)}</div>` },
      { key: "topic_name", label: "类别", render: (row) => `<div class="truncate narrow">${escapeHtml(row.topic_name)}</div>` },
      { key: "priority_level", label: "优先级", render: (row) => badge(row.priority_level) },
      { key: "priority_score", label: "综合分", render: (row) => scoreBar(row.priority_score) },
      { key: "misclassification_risk_score", label: "错分风险", render: (row) => score(row.misclassification_risk_score) },
      { key: "urgency_score", label: "紧急", render: (row) => score(row.urgency_score) },
      { key: "review_necessity_score", label: "必要性", render: (row) => score(row.review_necessity_score) },
      { key: "recommended_action", label: "建议", render: (row) => badge(row.recommended_action) },
      { key: "estimated_review_hours", label: "工时", render: (row) => `<span class="num">${score(row.estimated_review_hours)}</span>` },
      { key: "review_local_status", label: "人工状态", render: (row) => badge(row.review_local_status) },
    ],
  });
}

function renderAudit() {
  const view = "audit";
  const source = state.data.auditView || [];
  if (!state.sort[view]) {
    state.sort[view] = { key: "risk_score", dir: "desc" };
  }
  const rows = applyFilters(view, source, [
    { key: "primary_audit_bucket", value: getFilter(view, "primary_audit_bucket") },
    { key: "dataset", value: getFilter(view, "dataset") },
    { key: "classification_status", value: getFilter(view, "classification_status") },
    { key: "risk_level", value: getFilter(view, "risk_level") },
    { key: "review_local_status", value: getFilter(view, "review_local_status") },
  ]);
  const completed = source.filter((row) => row.review_local_status && row.review_local_status !== "pending").length;
  const highRisk = source.filter((row) => row.risk_level === "high").length;
  const boundary = source.filter((row) => row.classification_status === "multi_class").length;
  const unresolved = source.filter((row) => row.classification_status === "unclassifiable").length;

  content.innerHTML = `
    <div class="section">
      <div class="kpi-grid audit-kpis">
        ${kpi("核查样本", source.length, "按 doc_id 去重")}
        ${kpi("已人工处理", completed, "本地留痕状态")}
        ${kpi("待处理", source.length - completed, "pending")}
        ${kpi("高风险样本", highRisk, "risk_level = high")}
        ${kpi("多类边界", boundary, "classification_status")}
        ${kpi("无法归类", unresolved, "unclassifiable")}
      </div>
      <div class="grid-2">
        ${bars("抽样来源", "primary_audit_bucket", countBy(source, "primary_audit_bucket"), "var(--blue)")}
        ${bars("人工处理状态", "localStorage review logs", countBy(source, "review_local_status"), "var(--teal)")}
      </div>
      ${renderTable({
        view,
        rows,
        filtersHtml: [
          filterSelect(view, "primary_audit_bucket", "抽样来源", source),
          filterSelect(view, "dataset", "数据集", source),
          filterSelect(view, "classification_status", "分类状态", source),
          filterSelect(view, "risk_level", "风险", source),
          filterSelect(view, "review_local_status", "人工状态", source),
        ].join(""),
        columns: [
          { key: "primary_audit_bucket", label: "来源", render: (row) => badges(row.audit_bucket) },
          { key: "doc_id", label: "doc_id" },
          { key: "dataset", label: "数据集", render: (row) => badge(row.dataset) },
          {
            key: "content_snippet",
            label: "正文片段",
            render: (row) => `<div class="audit-snippet"><b>${escapeHtml(row.title_snippet || row.file_name || row.doc_id)}</b><span>${escapeHtml(row.content_snippet || "")}</span></div>`,
          },
          {
            key: "topic_name",
            label: "当前分类",
            render: (row) => `<div class="topic-stack"><b>${escapeHtml(row.topic_name)}</b><span>${escapeHtml(row.topic_parent_name || row.topic_broad_name || "")}</span></div>`,
          },
          { key: "classification_status", label: "状态", render: (row) => badge(row.classification_status) },
          { key: "risk_level", label: "风险", render: (row) => badge(row.risk_level) },
          { key: "confidence_score", label: "置信度", render: (row) => scoreBar(row.confidence_score) },
          { key: "topic_split_reason", label: "归类依据", render: (row) => `<div class="truncate narrow">${escapeHtml(row.topic_split_reason || row.review_reason)}</div>` },
          { key: "review_local_status", label: "人工状态", render: (row) => badge(row.review_local_status) },
          {
            key: "actions",
            label: "快速处理",
            sortable: false,
            render: (row) => `
              <div class="quick-actions audit-actions">
                <button type="button" data-quick-action="confirmed" data-doc-id="${escapeHtml(row.doc_id)}">确认</button>
                <button type="button" data-quick-action="uncertain" data-doc-id="${escapeHtml(row.doc_id)}">存疑</button>
                <button type="button" data-quick-action="noise" data-doc-id="${escapeHtml(row.doc_id)}">噪声</button>
                <button type="button" data-quick-action="unclassifiable" data-doc-id="${escapeHtml(row.doc_id)}">无法归类</button>
              </div>
            `,
          },
        ],
      })}
    </div>
  `;
}

function renderResources() {
  const plan = state.data.resourcePlan;
  content.innerHTML = `
    <div class="section">
      <div class="grid-3">
        ${plan
          .map((row) => `
            <article class="scenario-card">
              <h4>${escapeHtml(row.scenario_id)} 资源约束场景</h4>
              <div class="scenario-meta">
                <span>人工工时 ${score(row.manual_hours)}</span>
                <span>复核上限 ${formatInt(row.manual_review_limit)}</span>
                <span>自动归档 ${formatInt(row.auto_archive_limit)}</span>
              </div>
              <div class="bars" style="padding:12px 0 0">
                ${resourceProgress("已用工时", row.used_manual_hours, row.manual_hours, "var(--blue)")}
                ${resourceProgress("人工复核", row.manual_review_selected, row.manual_review_limit, "var(--teal)")}
                ${resourceProgress("延期复核", row.deferred_review_count, Math.max(num(row.deferred_review_count), num(row.manual_review_selected)), "var(--amber)")}
              </div>
              <div class="scenario-meta">
                <span>高优先级覆盖 ${formatInt(row.high_priority_selected)}</span>
                <span>中优先级覆盖 ${formatInt(row.medium_priority_selected)}</span>
                <span>剩余工时 ${score(row.remaining_manual_hours)}</span>
              </div>
            </article>
          `)
          .join("")}
      </div>
      <div class="grid-2">
        ${bars("人工复核入选数", "manual_review_selected", plan.map((row) => [row.scenario_id, num(row.manual_review_selected)]), "var(--teal)")}
        ${bars("延期复核数量", "deferred_review_count", plan.map((row) => [row.scenario_id, num(row.deferred_review_count)]), "var(--amber)")}
      </div>
      ${renderTable({
        view: "resources",
        rows: plan.filter(rowMatchesSearch),
        columns: [
          { key: "scenario_id", label: "场景" },
          { key: "manual_hours", label: "人工工时", render: (row) => score(row.manual_hours) },
          { key: "manual_review_limit", label: "人工复核上限", render: (row) => formatInt(row.manual_review_limit) },
          { key: "auto_archive_limit", label: "自动归档上限", render: (row) => formatInt(row.auto_archive_limit) },
          { key: "manual_review_selected", label: "已选复核", render: (row) => formatInt(row.manual_review_selected) },
          { key: "high_priority_selected", label: "高优先级", render: (row) => formatInt(row.high_priority_selected) },
          { key: "medium_priority_selected", label: "中优先级", render: (row) => formatInt(row.medium_priority_selected) },
          { key: "auto_archive_selected", label: "已自动归档", render: (row) => formatInt(row.auto_archive_selected) },
          { key: "deferred_review_count", label: "延期复核", render: (row) => formatInt(row.deferred_review_count) },
          { key: "used_manual_hours", label: "已用工时", render: (row) => score(row.used_manual_hours) },
          { key: "remaining_manual_hours", label: "剩余工时", render: (row) => score(row.remaining_manual_hours) },
        ],
      })}
    </div>
  `;
}

function resourceProgress(label, value, total, color) {
  const width = Math.max(0, Math.min(100, (num(value) / Math.max(1, num(total))) * 100));
  return `
    <div class="bar-row" style="grid-template-columns:82px minmax(0,1fr)74px">
      <span>${escapeHtml(label)}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${width}%;background:${color}"></div></div>
      <span class="num">${score(value)}</span>
    </div>
  `;
}

function render() {
  if (!titles[state.view]) {
    state.view = "overview";
  }
  $("#viewTitle").textContent = titles[state.view];
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.view);
  });

  if (state.view === "overview") renderOverview();
  if (state.view === "parse") renderParse();
  if (state.view === "topics") renderTopics();
  if (state.view === "classification") renderClassification();
  if (state.view === "review") renderReview();
  if (state.view === "audit") renderAudit();
  if (state.view === "resources") renderResources();
}

function findRow(docId) {
  return (
    state.data.auditView?.find((row) => row.doc_id === docId) ||
    state.data.priorityView?.find((row) => row.doc_id === docId) ||
    state.data.classificationView?.find((row) => row.doc_id === docId) ||
    state.data.parsed.find((row) => row.doc_id === docId)
  );
}

function openDrawer(docId) {
  const row = findRow(docId);
  if (!row) {
    return;
  }
  state.selected = row;
  $("#drawerTitle").textContent = row.title || row.title_snippet || row.doc_id || "文档详情";
  $("#drawerBody").innerHTML = drawerHtml(row);
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
}

function drawerHtml(row) {
  const logs = state.reviewLogs.filter((item) => item.doc_id === row.doc_id);
  return `
    <section class="detail-section">
      <h4>基本信息</h4>
      ${kv({
        doc_id: row.doc_id,
        dataset: row.dataset,
        file_name: row.file_name,
        file_path: row.file_path,
        title: row.title || row.title_snippet,
        time_info: row.time_info,
        parse_status: labelFor(row.parse_status),
        char_count: formatInt(row.char_count),
      })}
      ${
        row.file_path
          ? `<div class="file-actions">
              <button class="action-btn primary" type="button" data-file-action="open" data-doc-id="${escapeHtml(row.doc_id)}">打开原文件</button>
              <button class="action-btn" type="button" data-file-action="show" data-doc-id="${escapeHtml(row.doc_id)}">打开所在目录</button>
              <button class="action-btn" type="button" data-file-action="copy" data-path="${escapeHtml(row.file_path)}">复制路径</button>
            </div>
            <div id="fileActionStatus" class="file-action-status"></div>`
          : ""
      }
    </section>
    ${
      row.audit_bucket || row.content_snippet
        ? `<section class="detail-section">
            <h4>人工核查样本</h4>
            ${kv({
              primary_audit_bucket: labelFor(row.primary_audit_bucket),
              audit_bucket: row.audit_bucket,
              audit_hint: row.audit_hint,
              manual_decision: labelFor(getLatestLog(row.doc_id)?.status || row.manual_decision || "pending"),
            })}
            <div class="snippet-box">${escapeHtml(row.content_snippet || row.title_snippet || "")}</div>
          </section>`
        : ""
    }
    <section class="detail-section">
      <h4>分类结果</h4>
      ${kv({
        topic_parent_name: row.topic_parent_name,
        topic_broad_name: row.topic_broad_name,
        topic_name: row.topic_name,
        topic_prototype_name: row.topic_prototype_name,
        classification_status: labelFor(row.classification_status),
        candidate_topics: row.candidate_topics,
        confidence_score: row.confidence_score ? score(row.confidence_score) : "",
        score_margin: row.score_margin ? score(row.score_margin) : "",
        evidence_terms: row.evidence_terms,
        boundary_reason: row.boundary_reason,
        topic_split_reason: row.topic_split_reason,
      })}
    </section>
    <section class="detail-section">
      <h4>复核信息</h4>
      ${kv({
        risk_level: labelFor(row.risk_level),
        risk_score: row.risk_score ? score(row.risk_score) : "",
        priority_level: labelFor(row.priority_level),
        priority_score: row.priority_score ? score(row.priority_score) : "",
        misclassification_risk_score: row.misclassification_risk_score ? score(row.misclassification_risk_score) : "",
        urgency_score: row.urgency_score ? score(row.urgency_score) : "",
        review_necessity_score: row.review_necessity_score ? score(row.review_necessity_score) : "",
        recommended_action: labelFor(row.recommended_action || row.review_decision),
        review_reason: row.review_reason,
      })}
    </section>
    <section class="detail-section">
      <h4>人工操作</h4>
      <div class="review-actions">
        <label>最终类别
          <select id="finalTopic">
            ${state.topicsAll.map((item) => `<option value="${escapeHtml(item)}" ${item === row.topic_name ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
            <option value="综合内容待判别类">综合内容待判别类</option>
          </select>
        </label>
        <label>复核备注
          <textarea id="reviewNote" placeholder="填写复核依据或处理说明"></textarea>
        </label>
        <label>操作员
          <input id="reviewOperator" value="reviewer" />
        </label>
        <div class="action-grid">
          <button class="action-btn primary" data-review-action="confirmed">确认分类</button>
          <button class="action-btn" data-review-action="changed">修改类别</button>
          <button class="action-btn" data-review-action="uncertain">暂不确定</button>
          <button class="action-btn" data-review-action="noise">标记噪声</button>
          <button class="action-btn" data-review-action="unclassifiable">标记无法归类</button>
          <button class="action-btn" data-review-action="rejected">驳回自动归档</button>
        </div>
      </div>
    </section>
    <section class="detail-section">
      <h4>操作历史</h4>
      <div class="log-list">
        ${
          logs.length
            ? logs.map((log) => `<div class="log-item"><b>${escapeHtml(labelFor(log.status))}</b> · ${escapeHtml(log.updated_at)}<br />${escapeHtml(log.original_topic)} → ${escapeHtml(log.final_topic || "-")}<br />${escapeHtml(log.note || "")}</div>`).join("")
            : `<div class="empty">暂无操作记录</div>`
        }
      </div>
    </section>
  `;
}

function kv(items) {
  return `<dl class="kv">${Object.entries(items)
    .map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${value ? escapeHtml(value) : "-"}</dd>`)
    .join("")}</dl>`;
}

function closeDrawer() {
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
}

function handleSort(view, key) {
  if (!key) return;
  const current = state.sort[view];
  state.sort[view] = current?.key === key
    ? { key, dir: current.dir === "asc" ? "desc" : "asc" }
    : { key, dir: "desc" };
  render();
}

function exportLogs() {
  const blob = new Blob([JSON.stringify(state.reviewLogs, null, 2)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `review_logs_${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

async function handleFileAction(target) {
  const status = $("#fileActionStatus");
  const action = target.dataset.fileAction;
  if (action === "copy") {
    const path = target.dataset.path || "";
    try {
      await navigator.clipboard.writeText(path);
      if (status) status.textContent = "已复制文件路径。";
    } catch {
      if (status) status.textContent = `复制失败，请手动复制：${path}`;
    }
    return;
  }

  const docId = target.dataset.docId;
  const endpoint = action === "show" ? "/api/show-file" : "/api/open-file";
  try {
    const response = await fetch(`${endpoint}?doc_id=${encodeURIComponent(docId)}`);
    const payload = await response.json();
    if (!payload.ok) {
      throw new Error(payload.error || "操作失败");
    }
    if (status) {
      status.textContent = action === "show" ? `已打开所在目录：${payload.path}` : `已请求打开原文件：${payload.path}`;
    }
  } catch (error) {
    if (status) {
      status.textContent = `无法打开文件。请使用 dashboard_server.py 启动平台，或复制路径手动打开。错误：${error.message}`;
    }
  }
}

function quickReview(docId, status) {
  const row = findRow(docId);
  if (!row) {
    return;
  }
  const finalTopic = status === "unclassifiable"
    ? "无法归类"
    : status === "noise"
      ? "噪声无效"
      : row.topic_name || "";
  saveLog(
    {
      doc_id: row.doc_id,
      status,
      original_topic: row.topic_name || "",
      final_topic: finalTopic,
      note: `快速处理：${labelFor(status)}`,
      operator: "reviewer",
      updated_at: new Date().toLocaleString("zh-CN", { hour12: false }),
    },
    { openDrawer: false }
  );
}

function attachEvents() {
  document.addEventListener("click", (event) => {
    const target = event.target.closest("button, tr, th, article");
    if (!target) return;

    if (target.matches(".nav-item")) {
      state.view = target.dataset.view;
      state.page[state.view] = state.page[state.view] || 1;
      render();
    } else if (target.matches("[data-sort-key]")) {
      handleSort(target.dataset.sortView, target.dataset.sortKey);
    } else if (target.matches("[data-page-delta]")) {
      const view = target.dataset.pageView;
      state.page[view] = Math.max(1, (state.page[view] || 1) + Number(target.dataset.pageDelta));
      render();
    } else if (target.matches("[data-view-jump]")) {
      state.view = target.dataset.viewJump;
      render();
    } else if (target.matches("[data-file-action]")) {
      handleFileAction(target);
    } else if (target.matches("[data-quick-action]")) {
      quickReview(target.dataset.docId, target.dataset.quickAction);
    } else if (target.matches(".row-click") && target.dataset.docId && target.dataset.docId.includes(":")) {
      openDrawer(target.dataset.docId);
    } else if (target.matches("[data-review-action]")) {
      const selected = state.selected;
      if (!selected) return;
      const finalTopic = $("#finalTopic")?.value || selected.topic_name;
      const status = target.dataset.reviewAction;
      const resolvedTopic = status === "unclassifiable"
        ? "无法归类"
        : status === "noise"
          ? "噪声无效"
          : status === "uncertain"
            ? "暂不确定"
            : finalTopic;
      saveLog({
        doc_id: selected.doc_id,
        status,
        original_topic: selected.topic_name || "",
        final_topic: resolvedTopic,
        note: $("#reviewNote")?.value || "",
        operator: $("#reviewOperator")?.value || "reviewer",
        updated_at: new Date().toLocaleString("zh-CN", { hour12: false }),
      });
    }
  });

  document.addEventListener("change", (event) => {
    const target = event.target;
    if (target.matches("[data-filter-key]")) {
      setFilter(target.dataset.filterView, target.dataset.filterKey, target.value);
    }
  });

  $("#globalSearch").addEventListener("input", (event) => {
    state.search = event.target.value.trim();
    state.page[state.view] = 1;
    render();
  });
  $("#closeDrawerBtn").addEventListener("click", closeDrawer);
  $("#refreshBtn").addEventListener("click", init);
  $("#exportLogsBtn").addEventListener("click", exportLogs);
}

async function init() {
  try {
    loadLogs();
    await loadData();
    render();
  } catch (error) {
    $("#loadState").textContent = "数据加载失败";
    content.innerHTML = `<div class="error">数据加载失败：${escapeHtml(error.message)}。请从 b_solution 目录启动本地服务，并访问 /dashboard/index.html。</div>`;
  }
}

attachEvents();
init();
