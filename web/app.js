const $ = (selector) => document.querySelector(selector);
const form = $("#ask-form");
const question = $("#question");
const answer = $("#answer");
const sourceList = $("#source-list");
const dialog = $("#document-dialog");
let modelReady = false;
let loading = false;

async function request(path, options) {
  const response = await fetch(path, options);
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`服务响应异常 (${response.status})`);
  }
  if (!response.ok) throw new Error(data.error || `请求失败 (${response.status})`);
  return data;
}

function setFormMessage(message) {
  const element = $("#form-message");
  element.textContent = message;
  element.hidden = !message;
}

function updateMode() {
  const ai = form.elements.mode.value === "answer";
  $("#permission-wrap").hidden = !ai;
  $("#question-hint").textContent = ai ? "需要模型配置和明确的远端发送许可" : "检索模式仅在本地查找证据";
  $("#submit").firstChild.textContent = ai ? "生成回答 " : "开始检索 ";
  if (!ai) $("#allow-remote").checked = false;
  setFormMessage("");
}

function renderDocuments(documents) {
  const list = $("#document-list");
  list.replaceChildren();
  for (const entry of documents) {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    const icon = document.createElement("span");
    icon.className = "file-icon";
    icon.textContent = "MD";
    const name = document.createElement("span");
    name.className = "file-label";
    name.textContent = entry.path;
    const count = document.createElement("span");
    count.className = "file-count";
    count.textContent = entry.chunks;
    button.append(icon, name, count);
    button.addEventListener("click", () => openDocument(entry.path));
    item.append(button);
    list.append(item);
  }
}

async function loadLibrary() {
  try {
    const [status, documents] = await Promise.all([request("/api/status"), request("/api/documents")]);
    modelReady = status.model_ready;
    $("#library-name").textContent = status.name;
    $("#document-count").textContent = status.documents;
    $("#library-stats").textContent = `${status.documents} 份文档 · ${status.chunks} 个可检索片段`;
    $("#connection").innerHTML = '<span class="dot"></span> 本地已连接';
    $("#answer-option input").disabled = !modelReady;
    $("#answer-option").title = modelReady ? "" : "配置模型后可用";
    renderDocuments(documents);
  } catch (error) {
    const connection = $("#connection");
    connection.classList.add("offline");
    connection.innerHTML = '<span class="dot"></span> 连接失败';
    $("#library-stats").textContent = error.message;
    $("#document-count").textContent = "—";
    $("#answer-option input").disabled = true;
    setFormMessage(`无法载入知识库：${error.message}`);
  }
}

function renderSources(sources) {
  sourceList.replaceChildren();
  $("#source-count").textContent = sources.length;
  if (!sources.length) {
    const empty = document.createElement("p");
    empty.className = "aside-empty";
    empty.textContent = "没有可引用的文档片段。";
    sourceList.append(empty);
    return;
  }
  for (const source of sources) {
    const card = document.createElement("button");
    card.className = "source-card";
    card.type = "button";
    const title = document.createElement("span");
    title.className = "source-path";
    title.append(document.createTextNode(source.path));
    const arrow = document.createElement("span");
    arrow.textContent = "↗";
    title.append(arrow);
    const location = document.createElement("span");
    location.className = "source-location";
    location.textContent = `片段 ${source.chunk_id} · 字符 ${source.start}–${source.end}`;
    const preview = document.createElement("span");
    preview.className = "source-preview";
    preview.textContent = source.content;
    card.append(title, location, preview);
    card.addEventListener("click", () => openDocument(source.path, source));
    sourceList.append(card);
  }
}

async function openDocument(path, source) {
  $("#document-title").textContent = path;
  $("#document-meta").textContent = source ? `片段 ${source.chunk_id} · 字符 ${source.start}–${source.end}` : "文档全文";
  $("#document-content").textContent = "正在载入原文…";
  dialog.showModal();
  try {
    const entry = await request(`/api/document?path=${encodeURIComponent(path)}`);
    if (!dialog.open || $("#document-title").textContent !== path) return;
    const content = $("#document-content");
    content.replaceChildren();
    if (source && source.start >= 0 && source.end >= source.start && entry.content.slice(source.start, source.end + 1) === source.content) {
      content.append(entry.content.slice(0, source.start));
      const highlighted = document.createElement("mark");
      highlighted.textContent = source.content;
      content.append(highlighted, entry.content.slice(source.end + 1));
      highlighted.scrollIntoView({ block: "center" });
    } else {
      content.textContent = entry.content;
    }
  } catch (error) {
    $("#document-content").textContent = `无法读取文档：${error.message}`;
  }
}

form.addEventListener("change", (event) => {
  if (event.target.name === "mode") updateMode();
  if (event.target.id === "allow-remote") setFormMessage("");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (loading) return;
  const mode = form.elements.mode.value;
  const text = question.value.trim();
  if (!text) {
    setFormMessage("请输入问题。");
    question.focus();
    return;
  }
  if (mode === "answer" && (!modelReady || !$("#allow-remote").checked)) {
    setFormMessage(modelReady ? "请先确认允许向模型服务商发送问题和文档片段。" : "模型尚未配置，请使用本地检索。");
    return;
  }
  loading = true;
  setFormMessage("");
  $("#submit").disabled = true;
  $("#result-tag").textContent = "处理中";
  answer.classList.add("loading");
  answer.textContent = mode === "answer" ? "正在检索证据并生成回答…" : "正在检索文档…";
  try {
    const result = await request("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: text, mode, allow_remote: mode === "answer" && $("#allow-remote").checked }),
    });
    answer.textContent = result.answer;
    $("#result-title").textContent = result.mode === "answer" ? "模型回答" : "检索结果";
    $("#result-tag").textContent = result.sources.length ? `${result.sources.length} 条来源` : "未找到来源";
    renderSources(result.sources);
  } catch (error) {
    answer.textContent = "";
    $("#result-tag").textContent = "请求失败";
    setFormMessage(error.message);
  } finally {
    answer.classList.remove("loading");
    $("#submit").disabled = false;
    loading = false;
  }
});

$("#close-dialog").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});
loadLibrary();
