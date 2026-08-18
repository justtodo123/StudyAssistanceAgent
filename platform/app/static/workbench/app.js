const WORKBENCH_API = Object.freeze({
  reviewDue: "/api/v1/review-due",
  studySessions: "/api/v1/study-sessions",
});

const state = {
  session: null,
};

function $(id) {
  return document.getElementById(id);
}

function setStatus(message, isError) {
  const node = $("status");
  node.textContent = message || "";
  node.classList.toggle("error", Boolean(isError && message));
}

function show(id, visible) {
  $(id).classList.toggle("hidden", !visible);
}

async function readError(response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    return JSON.stringify(payload.detail || payload);
  } catch (_error) {
    return `请求失败（${response.status}）`;
  }
}

async function requestJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json();
}

function dueQuery(course) {
  const params = new URLSearchParams();
  if (course) {
    params.set("course", course);
  }
  const query = params.toString();
  return query ? `${WORKBENCH_API.reviewDue}?${query}` : WORKBENCH_API.reviewDue;
}

function sessionUrl(sessionId, suffix) {
  const base = `${WORKBENCH_API.studySessions}/${encodeURIComponent(sessionId)}`;
  return suffix ? `${base}/${suffix}` : base;
}

async function loadDueReviews() {
  const course = $("due-course").value;
  const data = await requestJson(dueQuery(course));
  renderDue(data);
}

function renderDue(data) {
  const summary = data.summary || {};
  $("due-summary").textContent = `待复习 ${data.total_due || 0} 条，逾期 ${summary.overdue || 0} 条。`;
  const list = $("due-list");
  list.replaceChildren();
  if (!data.entries || data.entries.length === 0) {
    const empty = document.createElement("li");
    empty.className = "muted";
    empty.textContent = "今日没有待复习条目。";
    list.append(empty);
    return;
  }
  data.entries.forEach((entry) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "due-item";
    const overdue =
      entry.days_overdue > 0 ? `逾期 ${entry.days_overdue} 天` : "今日到期";
    button.textContent = `${entry.title || entry.file} · ${entry.course} · ${overdue}`;
    button.addEventListener("click", () => {
      $("course").value = entry.course || "os";
      $("topic").value = entry.title || "";
      $("topic").focus();
      setStatus(`已填入待复习主题：${$("topic").value}`);
    });
    item.append(button);
    list.append(item);
  });
}

async function startSession(event) {
  event.preventDefault();
  const topic = $("topic").value.trim();
  const course = $("course").value;
  if (!topic) {
    setStatus("请输入学习主题。", true);
    return;
  }
  $("start-button").disabled = true;
  setStatus("正在创建学习会话…");
  try {
    const session = await requestJson(WORKBENCH_API.studySessions, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic,
        course,
        question_count: 1,
        use_llm: false,
      }),
    });
    renderSession(session);
    setStatus("已生成讲解和题目。");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    $("start-button").disabled = false;
  }
}

async function submitAnswer(event) {
  event.preventDefault();
  if (!state.session) {
    setStatus("请先开始一个学习会话。", true);
    return;
  }
  const answer = $("answer").value.trim();
  if (!answer) {
    setStatus("请先填写答案。", true);
    return;
  }
  $("answer-button").disabled = true;
  setStatus("正在评估答案…");
  try {
    const session = await requestJson(sessionUrl(state.session.session_id, "answers"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        answer,
        question_id: state.session.current_question_id,
      }),
    });
    $("answer").value = "";
    renderSession(session);
    setStatus(session.state === "completed" ? "本轮学习已完成。" : "请根据反馈继续作答。");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    $("answer-button").disabled = false;
  }
}

function currentQuestion(session) {
  if (!session.questions || session.questions.length === 0) {
    return null;
  }
  return (
    session.questions.find((item) => item.id === session.current_question_id) ||
    session.questions[0]
  );
}

function renderSession(session) {
  state.session = session;
  show("session-panel", true);
  $("session-meta").textContent = `${session.course} · ${session.topic} · ${session.state}`;
  $("explanation").textContent = session.explanation || "暂无讲解。";

  const sources = $("sources");
  sources.replaceChildren();
  (session.sources || []).forEach((source) => {
    const item = document.createElement("li");
    item.className = "source-item";
    item.textContent = `${source.title || source.file} · ${source.file}`;
    sources.append(item);
  });
  if (!session.sources || session.sources.length === 0) {
    const item = document.createElement("li");
    item.className = "muted";
    item.textContent = "没有返回来源。";
    sources.append(item);
  }

  const question = currentQuestion(session);
  const canAnswer = session.state !== "completed" && question;
  show("question-panel", Boolean(canAnswer));
  if (question) {
    $("question-text").textContent = question.question;
  }

  const evaluation = session.last_evaluation;
  const hasFeedback = Boolean(evaluation || session.remediation);
  show("feedback-panel", hasFeedback);
  $("feedback").textContent = evaluation
    ? `${evaluation.correct ? "回答正确" : "回答需要补充"}。${evaluation.feedback || ""}`
    : "";
  $("remediation").textContent = session.remediation || "";

  const completed = session.state === "completed";
  show("completion-panel", completed);
  if (completed) {
    const score = session.score == null ? "未评分" : session.score;
    $("completion-result").textContent = `掌握度评分：${score}`;
    const review = session.review || {};
    $("next-review").textContent =
      review.message ||
      (review.next_review ? `下次复习：${review.next_review}` : "本次未返回下次复习日期。");
  }

  const trace = $("tool-trace");
  trace.replaceChildren();
  (session.tool_trace || []).forEach((step) => {
    const item = document.createElement("li");
    item.textContent = `${step.step} · ${step.service} · ${step.status} · ${step.state_after}`;
    trace.append(item);
  });
}

function resetWorkbench() {
  state.session = null;
  $("answer").value = "";
  show("session-panel", false);
  setStatus("可以开始下一个主题。");
  $("topic").focus();
}

function bindWorkbench() {
  $("start-form").addEventListener("submit", startSession);
  $("answer-form").addEventListener("submit", submitAnswer);
  $("refresh-due").addEventListener("click", () => {
    loadDueReviews().catch((error) => setStatus(error.message, true));
  });
  $("due-course").addEventListener("change", () => {
    loadDueReviews().catch((error) => setStatus(error.message, true));
  });
  $("reset-button").addEventListener("click", resetWorkbench);
  loadDueReviews().catch((error) => setStatus(error.message, true));
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bindWorkbench);
} else {
  bindWorkbench();
}
