const API = Object.freeze({
  search: "/api/v1/search",
  qa: "/api/v1/qa",
  qaStream: "/api/v1/qa/stream",
  quiz: "/api/v1/quiz",
  reviewPlan: "/api/v1/review-plan",
  reviewLog: "/api/v1/review-log",
  reviewDue: "/api/v1/review-due",
  studySessions: "/api/v1/study-sessions",
  settings: "/api/v1/settings",
  settingsLlm: "/api/v1/settings/llm",
});

const state = { session: null };

function $(id) { return document.getElementById(id); }

function setStatus(msg, type) {
  const el = $("global-status");
  el.textContent = msg || "";
  el.className = "status" + (type ? " " + type : "");
}

function show(id, visible) { $(id).classList.toggle("hidden", !visible); }

async function readError(resp) {
  try {
    const data = await resp.json();
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data);
  } catch { return "请求失败（" + resp.status + "）"; }
}

async function api(url, opts) {
  const resp = await fetch(url, opts);
  if (!resp.ok) throw new Error(await readError(resp));
  return resp.json();
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ===== Tab Navigation =====
function initTabs() {
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      $("tab-" + tab.dataset.tab).classList.add("active");
    });
  });
}

// ===== Search =====
function initSearch() {
  $("search-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const q = $("search-q").value.trim();
    if (!q) return;
    const course = $("search-course").value;
    const topK = parseInt($("search-k").value, 10);
    const panel = $("search-results");
    panel.innerHTML = '<div class="loading">检索中</div>';
    show("search-results", true);
    try {
      const data = await api(API.search, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, top_k: topK, course: course || null, use_vector: false }),
      });
      renderSearchResults(data, panel);
      setStatus("检索完成，返回 " + (data.results || []).length + " 条结果", "success");
    } catch (err) {
      panel.innerHTML = '<div class="empty-state">检索失败：' + escapeHtml(err.message) + "</div>";
      setStatus(err.message, "error");
    }
  });
}

function renderSearchResults(data, panel) {
  const results = data.results || [];
  if (results.length === 0) {
    panel.innerHTML = '<div class="empty-state">未找到相关内容</div>';
    return;
  }
  let html = "";
  results.forEach((r, i) => {
    html += '<div class="result-item">' +
      '<div class="result-header">' +
        '<span class="result-title">#' + (i + 1) + " " + escapeHtml(r.title || r.file) + '</span>' +
        '<span><span class="result-score">score: ' + (r.score != null ? r.score.toFixed(3) : "-") + '</span>' +
        (r.course ? '<span class="result-course">' + escapeHtml(r.course) + "</span>" : "") +
        "</span>" +
      "</div>" +
      '<div class="result-file">' + escapeHtml(r.file || "") + "</div>" +
      '<div class="result-content">' + escapeHtml(r.content || "") + "</div>" +
    "</div>";
  });
  panel.innerHTML = html;
}

// ===== QA =====
function initQA() {
  $("qa-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = $("qa-question").value.trim();
    if (!question) return;
    const course = $("qa-course").value;
    const useStream = $("qa-stream").checked;
    const resultDiv = $("qa-result");
    const answerDiv = $("qa-answer");
    const sourcesDiv = $("qa-sources");
    const layerBadge = $("qa-layer");
    const modeBadge = $("qa-mode");

    show("qa-result", true);
    answerDiv.textContent = "";
    sourcesDiv.innerHTML = "";
    layerBadge.textContent = "";
    modeBadge.textContent = "";
    answerDiv.parentElement.classList.add("loading");
    answerDiv.textContent = "生成中";

    if (useStream) {
      await streamQA(question, course || null, answerDiv, sourcesDiv, layerBadge, modeBadge);
    } else {
      await normalQA(question, course || null, answerDiv, sourcesDiv, layerBadge, modeBadge);
    }
  });
}

async function normalQA(question, course, answerDiv, sourcesDiv, layerBadge, modeBadge) {
  try {
    const data = await api(API.qa, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, course, use_llm: true, use_vector: false }),
    });
    answerDiv.parentElement.classList.remove("loading");
    answerDiv.textContent = data.answer || "未生成回答";
    layerBadge.textContent = data.generation_layer || "-";
    layerBadge.className = "badge" + (data.generation_layer === "grounded_llm" ? " badge-success" : " badge-muted");
    modeBadge.textContent = data.mode || "-";
    renderQASources(data.sources || [], sourcesDiv);
    renderQAUsage(data);
    setStatus("回答生成完成", "success");
  } catch (err) {
    answerDiv.parentElement.classList.remove("loading");
    answerDiv.textContent = "生成失败：" + err.message;
    setStatus(err.message, "error");
  }
}

async function streamQA(question, course, answerDiv, sourcesDiv, layerBadge, modeBadge) {
  try {
    const resp = await fetch(API.qaStream, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, course, use_llm: true }),
    });
    if (!resp.ok) throw new Error(await readError(resp));

    answerDiv.parentElement.classList.remove("loading");
    answerDiv.textContent = "";
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") {
          setStatus("流式输出完成", "success");
          continue;
        }
        try {
          const obj = JSON.parse(payload);
          if (obj.sources) {
            layerBadge.textContent = obj.generation_layer || "note_summary";
            layerBadge.className = "badge badge-muted";
            modeBadge.textContent = obj.mode || "-";
            renderQASources(obj.sources, sourcesDiv);
          } else if (obj.delta) {
            fullText += obj.delta;
            answerDiv.textContent = fullText;
          }
        } catch { /* skip malformed */ }
      }
    }
    if (!fullText) answerDiv.textContent = "未收到内容";
  } catch (err) {
    answerDiv.parentElement.classList.remove("loading");
    answerDiv.textContent = "流式生成失败：" + err.message;
    setStatus(err.message, "error");
  }
}

function renderQASources(sources, container) {
  if (!sources.length) { container.innerHTML = ""; return; }
  let html = "<h4>出处</h4>";
  sources.forEach((s) => {
    html += '<div class="qa-source-item">' +
      escapeHtml(s.title || s.file || "") +
      (s.course ? " [" + escapeHtml(s.course) + "]" : "") +
      (s.file ? " — " + escapeHtml(s.file) : "") +
    "</div>";
  });
  container.innerHTML = html;
}

function renderQAUsage(data) {
  const usageDiv = $("qa-usage");
  if (data.model || data.usage) {
    let html = "";
    if (data.model) html += "模型：<span>" + escapeHtml(data.model) + "</span>";
    if (data.usage) {
      html += "Token：<span>" + data.usage.total_tokens + "</span>";
      html += "（输入 " + data.usage.prompt_tokens + " + 输出 " + data.usage.completion_tokens + "）";
    }
    usageDiv.innerHTML = html;
    usageDiv.classList.remove("hidden");
  } else {
    usageDiv.classList.add("hidden");
  }
}

// ===== Quiz =====
function initQuiz() {
  $("quiz-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const course = $("quiz-course").value;
    const count = parseInt($("quiz-count").value, 10);
    const difficulty = $("quiz-difficulty").value;
    const topicsRaw = $("quiz-topics").value.trim();
    const topics = topicsRaw ? topicsRaw.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : undefined;

    const container = $("quiz-results");
    container.innerHTML = '<div class="panel loading">生成中</div>';
    show("quiz-results", true);

    const body = { course, count };
    if (difficulty) body.difficulty = difficulty;
    if (topics) body.topics = topics;

    try {
      const data = await api(API.quiz, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      renderQuiz(data, container);
      setStatus("测验生成完成，共 " + (data.questions || []).length + " 题", "success");
    } catch (err) {
      container.innerHTML = '<div class="panel empty-state">生成失败：' + escapeHtml(err.message) + "</div>";
      setStatus(err.message, "error");
    }
  });
}

function renderQuiz(data, container) {
  const questions = data.questions || [];
  const summary = data.summary || {};
  if (questions.length === 0) {
    container.innerHTML = '<div class="panel empty-state">未生成题目</div>';
    return;
  }

  let html = '<div class="panel">';
  html += '<div class="quiz-summary">';
  if (summary.total_pool != null) html += '<div class="quiz-stat">题库 <strong>' + summary.total_pool + "</strong></div>";
  if (summary.filtered != null) html += '<div class="quiz-stat">筛后 <strong>' + summary.filtered + "</strong></div>";
  const byType = summary.by_type || {};
  Object.keys(byType).forEach((t) => {
    html += '<div class="quiz-stat">' + escapeHtml(t) + ' <strong>' + byType[t] + "</strong></div>";
  });
  html += "</div></div>";

  questions.forEach((q, i) => {
    const typeClass = q.type === "example" ? "example" : q.type === "retrieval" ? "retrieval" : "concept";
    const typeLabel = q.type === "example" ? "经典例题" : q.type === "retrieval" ? "检索题" : "概念题";
    html += '<div class="panel quiz-card">';
    html += '<div class="quiz-card-header">';
    html += '<span>第 ' + (i + 1) + " 题</span>";
    html += '<span class="quiz-type ' + typeClass + '">' + typeLabel + "</span>";
    html += "</div>";
    html += '<div class="quiz-question">' + escapeHtml(q.question) + "</div>";
    html += '<div class="quiz-source">' + escapeHtml(q.source_file || "") + "</div>";
    if (q.tags && q.tags.length) {
      html += '<div class="quiz-tags">';
      q.tags.forEach((t) => { html += '<span class="quiz-tag">' + escapeHtml(t) + "</span>"; });
      html += "</div>";
    }
    if (q.type === "example" && q.answer) {
      const answerId = "quiz-answer-" + i;
      html += '<button class="quiz-answer-toggle" onclick="document.getElementById(\'' + answerId + '\').classList.toggle(\'hidden\')">显示/隐藏参考答案</button>';
      html += '<div id="' + answerId + '" class="quiz-answer hidden">' + escapeHtml(q.answer) + "</div>";
    }
    html += "</div>";
  });

  container.innerHTML = html;
}

// ===== Review Plan =====
function initPlan() {
  const dateInput = $("plan-date");
  const d = new Date();
  d.setDate(d.getDate() + 14);
  dateInput.value = d.toISOString().slice(0, 10);

  $("plan-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const course = $("plan-course").value;
    const targetDate = $("plan-date").value;
    const hoursPerDay = parseFloat($("plan-hours").value);

    const container = $("plan-results");
    container.innerHTML = '<div class="panel loading">生成中</div>';
    show("plan-results", true);

    try {
      const data = await api(API.reviewPlan, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ course, target_date: targetDate, hours_per_day: hoursPerDay }),
      });
      renderPlan(data, container);
      setStatus("计划生成完成", "success");
    } catch (err) {
      container.innerHTML = '<div class="panel empty-state">生成失败：' + escapeHtml(err.message) + "</div>";
      setStatus(err.message, "error");
    }
  });
}

function renderPlan(data, container) {
  const days = data.days || [];
  const summary = data.summary || {};
  if (days.length === 0) {
    container.innerHTML = '<div class="panel empty-state">未生成计划</div>';
    return;
  }

  let html = '<div class="panel">';
  html += '<div class="plan-summary">';
  if (data.total_hours != null) html += '<div class="plan-stat"><strong>' + data.total_hours.toFixed(1) + "</strong>总学时</div>";
  if (summary.total_entries != null) html += '<div class="plan-stat"><strong>' + summary.total_entries + "</strong>条目</div>";
  const byDiff = summary.by_difficulty || {};
  Object.keys(byDiff).forEach((d) => {
    html += '<div class="plan-stat">' + escapeHtml(d) + ' <strong>' + byDiff[d] + "</strong></div>";
  });
  html += "</div>";

  days.forEach((day) => {
    html += '<div class="plan-day">';
    html += '<div class="plan-day-header">Day ' + (day.day || "?") + "（" + (day.tasks ? day.tasks.length : 0) + " 个任务）</div>";
    (day.tasks || []).forEach((task) => {
      html += '<div class="plan-task">';
      html += '<span class="plan-task-title">' + escapeHtml(task.title || task.topic || task.file) + "</span>";
      html += '<span class="plan-task-meta">';
      if (task.difficulty) html += "<span>" + escapeHtml(task.difficulty) + "</span>";
      if (task.estimated_minutes) html += "<span>" + task.estimated_minutes + " 分钟</span>";
      if (task.priority) html += "<span>" + escapeHtml(task.priority) + "</span>";
      html += "</span></div>";
    });
    html += "</div>";
  });

  if (summary.tip) {
    html += '<div class="plan-tip">' + escapeHtml(summary.tip) + "</div>";
  }
  html += "</div>";
  container.innerHTML = html;
}

// ===== Study Session =====
function initSession() {
  $("start-form").addEventListener("submit", startSession);
  $("answer-form").addEventListener("submit", submitAnswer);
  $("reset-button").addEventListener("click", resetSession);
}

async function startSession(e) {
  e.preventDefault();
  const topic = $("topic").value.trim();
  const course = $("course").value;
  if (!topic) { setStatus("请输入学习主题", "error"); return; }
  $("start-button").disabled = true;
  setStatus("正在创建学习会话…");
  try {
    const session = await api(API.studySessions, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, course, question_count: 1, use_llm: false }),
    });
    renderSession(session);
    setStatus("已生成讲解和题目", "success");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    $("start-button").disabled = false;
  }
}

async function submitAnswer(e) {
  e.preventDefault();
  if (!state.session) { setStatus("请先开始学习会话", "error"); return; }
  const answer = $("answer").value.trim();
  if (!answer) { setStatus("请先填写答案", "error"); return; }
  $("answer-button").disabled = true;
  setStatus("正在评估…");
  try {
    const session = await api(API.studySessions + "/" + encodeURIComponent(state.session.session_id) + "/answers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer, question_id: state.session.current_question_id }),
    });
    $("answer").value = "";
    renderSession(session);
    setStatus(session.state === "completed" ? "本轮学习已完成" : "请根据反馈继续作答", session.state === "completed" ? "success" : "");
  } catch (err) {
    setStatus(err.message, "error");
  } finally {
    $("answer-button").disabled = false;
  }
}

function currentQuestion(session) {
  if (!session.questions || !session.questions.length) return null;
  return session.questions.find((q) => q.id === session.current_question_id) || session.questions[0];
}

function renderSession(session) {
  state.session = session;
  show("session-panel", true);
  $("session-meta").textContent = session.course + " · " + session.topic + " · " + session.state;
  $("explanation").textContent = session.explanation || "暂无讲解";

  const sources = $("sources");
  sources.replaceChildren();
  (session.sources || []).forEach((s) => {
    const li = document.createElement("li");
    li.className = "source-item";
    li.textContent = (s.title || s.file) + " · " + s.file;
    sources.append(li);
  });
  if (!session.sources || !session.sources.length) {
    const li = document.createElement("li");
    li.className = "source-item";
    li.textContent = "没有返回来源";
    sources.append(li);
  }

  const question = currentQuestion(session);
  const canAnswer = session.state !== "completed" && question;
  show("question-panel", Boolean(canAnswer));
  if (question) $("question-text").textContent = question.question;

  const evaluation = session.last_evaluation;
  show("feedback-panel", Boolean(evaluation || session.remediation));
  $("feedback").textContent = evaluation
    ? (evaluation.correct ? "回答正确。" : "回答需要补充。") + (evaluation.feedback || "")
    : "";
  $("remediation").textContent = session.remediation || "";

  show("completion-panel", session.state === "completed");
  if (session.state === "completed") {
    $("completion-result").textContent = "掌握度评分：" + (session.score == null ? "未评分" : session.score);
    const review = session.review || {};
    $("next-review").textContent = review.message || (review.next_review ? "下次复习：" + review.next_review : "");
  }

  const trace = $("tool-trace");
  trace.replaceChildren();
  (session.tool_trace || []).forEach((step) => {
    const li = document.createElement("li");
    li.textContent = step.step + " · " + step.service + " · " + step.status + " · " + step.state_after;
    trace.append(li);
  });
}

function resetSession() {
  state.session = null;
  $("answer").value = "";
  show("session-panel", false);
  setStatus("可以开始下一个主题", "success");
  $("topic").value = "";
  $("topic").focus();
}

// ===== Review Due =====
function initDue() {
  $("refresh-due").addEventListener("click", loadDue);
  $("due-course").addEventListener("change", loadDue);
  loadDue();
}

async function loadDue() {
  const course = $("due-course").value;
  const params = course ? "?course=" + encodeURIComponent(course) : "";
  try {
    const data = await api(API.reviewDue + params);
    renderDue(data);
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function renderDue(data) {
  const summary = data.summary || {};
  $("due-summary").textContent = "待复习 " + (data.total_due || 0) + " 条，逾期 " + (summary.overdue || 0) + " 条";
  const list = $("due-list");
  list.replaceChildren();
  if (!data.entries || !data.entries.length) {
    const li = document.createElement("li");
    li.className = "empty-state";
    li.textContent = "今日没有待复习条目";
    list.append(li);
    return;
  }
  data.entries.forEach((entry) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "due-item-btn";
    const overdue = entry.days_overdue > 0 ? "逾期 " + entry.days_overdue + " 天" : "今日到期";
    btn.textContent = (entry.title || entry.file) + " · " + entry.course + " · " + overdue;
    btn.addEventListener("click", () => {
      $("course").value = entry.course || "os";
      $("topic").value = entry.title || "";
      document.querySelector('[data-tab="session"]').click();
      setStatus("已填入待复习主题：" + $("topic").value, "success");
    });
    li.append(btn);
    list.append(li);
  });
}

// ===== Settings =====
function initSettings() {
  loadSettings();
  $("settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const apiKey = $("settings-api-key").value.trim();
    const baseUrl = $("settings-base-url").value.trim();
    const model = $("settings-model").value.trim();

    const body = {};
    if (apiKey) body.api_key = apiKey;
    if (baseUrl) body.base_url = baseUrl;
    if (model) body.model = model;

    if (Object.keys(body).length === 0) {
      setStatus("未填写任何配置", "error");
      return;
    }

    try {
      await api(API.settingsLlm, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setStatus("配置已保存", "success");
      $("settings-api-key").value = "";
      await loadSettings();
    } catch (err) {
      setStatus(err.message, "error");
    }
  });
}

async function loadSettings() {
  try {
    const data = await api(API.settings);
    $("settings-key-hint").textContent = "当前：" + (data.llm.api_key_masked || "未配置");
    $("settings-base-url").value = data.llm.base_url || "";
    $("settings-model").value = data.llm.model || "";
    $("settings-index-size").textContent = data.index_size;
    $("settings-courses").textContent = data.courses.join(", ") || "-";
    $("settings-llm-status").textContent = data.llm.configured
      ? "已配置 (" + (data.llm.model || "default") + ")"
      : "未配置";
  } catch (err) {
    setStatus("加载配置失败：" + err.message, "error");
  }
}

// ===== Init =====
function init() {
  initTabs();
  initSearch();
  initQA();
  initQuiz();
  initPlan();
  initSession();
  initDue();
  initSettings();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
