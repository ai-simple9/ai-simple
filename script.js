const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatBox = document.getElementById("chatBox");

const trainQuestion = document.getElementById("trainQuestion");
const trainAnswers = document.getElementById("trainAnswers");
const trainTags = document.getElementById("trainTags");
const trainBtn = document.getElementById("trainBtn");
const trainStatus = document.getElementById("trainStatus");

const knowledgeList = document.getElementById("knowledgeList");
const refreshKnowledgeBtn = document.getElementById("refreshKnowledgeBtn");
const searchInput = document.getElementById("searchInput");
const tagInput = document.getElementById("tagInput");

const importData = document.getElementById("importData");
const importBtn = document.getElementById("importBtn");

const backupBtn = document.getElementById("backupBtn");
const backupStatus = document.getElementById("backupStatus");
const backupsList = document.getElementById("backupsList");

const editModal = document.getElementById("editModal");
const editId = document.getElementById("editId");
const editQuestion = document.getElementById("editQuestion");
const editAnswers = document.getElementById("editAnswers");
const editTags = document.getElementById("editTags");
const editActive = document.getElementById("editActive");
const saveEditBtn = document.getElementById("saveEditBtn");
const closeEditBtn = document.getElementById("closeEditBtn");

function scrollBottom() {
  chatBox.scrollTop = chatBox.scrollHeight;
}

function splitLines(text) {
  return text.split("\n").map(v => v.trim()).filter(Boolean);
}

function splitTags(text) {
  return text.split(",").map(v => v.trim().toLowerCase()).filter(Boolean);
}

function addMessage(text, sender, pairId = null) {
  const wrap = document.createElement("div");
  wrap.classList.add("message-wrap");

  const div = document.createElement("div");
  div.classList.add("message", sender);
  div.textContent = text;
  wrap.appendChild(div);

  if (sender === "bot" && pairId) {
    const actions = document.createElement("div");
    actions.classList.add("message-actions");

    const likeBtn = document.createElement("button");
    likeBtn.classList.add("small-btn");
    likeBtn.textContent = "Полезно";

    const dislikeBtn = document.createElement("button");
    dislikeBtn.classList.add("small-btn");
    dislikeBtn.textContent = "Бесполезно";

    likeBtn.addEventListener("click", () => rateAnswer(pairId, "up"));
    dislikeBtn.addEventListener("click", () => rateAnswer(pairId, "down"));

    actions.appendChild(likeBtn);
    actions.appendChild(dislikeBtn);
    wrap.appendChild(actions);
  }

  chatBox.appendChild(wrap);
  scrollBottom();
}

async function rateAnswer(pairId, vote) {
  try {
    const res = await fetch("/rate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pair_id: pairId, vote })
    });

    const data = await res.json();
    alert(data.message || "Оценка отправлена.");
    loadKnowledge();
  } catch {
    alert("Ошибка оценки.");
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/history");
    const data = await res.json();

    chatBox.innerHTML = "";

    if (data.dialog && data.dialog.length) {
      data.dialog.forEach(item => {
        addMessage(item.user, "user");
        addMessage(item.bot, "bot", item.pair_id);
      });
    } else {
      addMessage("Привет. Я demo railway bot. Пиши.", "bot");
    }
  } catch {
    addMessage("Не удалось загрузить историю.", "bot");
  }
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const message = messageInput.value.trim();
  if (!message) return;

  addMessage(message, "user");
  messageInput.value = "";

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const data = await res.json();
    addMessage(data.reply || "Кривой ответ от сервера.", "bot", data.pair_id || null);
  } catch {
    addMessage("Ошибка подключения к серверу.", "bot");
  }
});

trainBtn.addEventListener("click", async () => {
  const question = trainQuestion.value.trim();
  const answers = splitLines(trainAnswers.value.trim());
  const tags = splitTags(trainTags.value.trim());

  if (!question || !answers.length) {
    trainStatus.textContent = "Нужен вопрос и хотя бы один ответ.";
    return;
  }

  try {
    const res = await fetch("/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answers, tags })
    });

    const data = await res.json();
    trainStatus.textContent = data.message || "Готово.";

    if (data.status === "success") {
      trainQuestion.value = "";
      trainAnswers.value = "";
      trainTags.value = "";
      loadKnowledge();
      loadBackups();
    }
  } catch {
    trainStatus.textContent = "Ошибка обучения.";
  }
});

async function deleteKnowledge(id) {
  if (!confirm(`Удалить запись ${id}?`)) return;

  try {
    const res = await fetch("/knowledge/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id })
    });

    const data = await res.json();
    alert(data.message || "Удалено.");
    loadKnowledge();
    loadBackups();
  } catch {
    alert("Ошибка удаления.");
  }
}

function openEditModal(pair) {
  editId.value = pair.id;
  editQuestion.value = pair.question;
  editAnswers.value = (pair.answers || []).join("\n");
  editTags.value = (pair.tags || []).join(", ");
  editActive.checked = !!pair.is_active;
  editModal.classList.remove("hidden");
}

closeEditBtn.addEventListener("click", () => {
  editModal.classList.add("hidden");
});

saveEditBtn.addEventListener("click", async () => {
  const id = Number(editId.value);
  const question = editQuestion.value.trim();
  const answers = splitLines(editAnswers.value.trim());
  const tags = splitTags(editTags.value.trim());
  const is_active = editActive.checked;

  if (!id || !question || !answers.length) {
    alert("Неверные данные для сохранения.");
    return;
  }

  try {
    const res = await fetch("/knowledge/update", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, question, answers, tags, is_active })
    });

    const data = await res.json();
    alert(data.message || "Сохранено.");
    editModal.classList.add("hidden");
    loadKnowledge();
    loadBackups();
  } catch {
    alert("Ошибка сохранения.");
  }
});

async function loadKnowledge() {
  try {
    const q = encodeURIComponent(searchInput.value.trim());
    const tag = encodeURIComponent(tagInput.value.trim());
    const res = await fetch(`/knowledge?q=${q}&tag=${tag}`);
    const data = await res.json();

    knowledgeList.innerHTML = "";

    const pairs = (data.custom_pairs || []).slice().sort((a, b) => b.id - a.id);

    if (!pairs.length) {
      knowledgeList.innerHTML = "<p>База пока пустая.</p>";
      return;
    }

    pairs.forEach(pair => {
      const item = document.createElement("div");
      item.classList.add("knowledge-item");

      const tagsHtml = (pair.tags || []).map(tag => `<span class="tag">${tag}</span>`).join("");
      const answersHtml = (pair.answers || []).map(answer => `<li>${answer}</li>`).join("");

      item.innerHTML = `
        <div><strong>#${pair.id}</strong> ${pair.is_active ? "" : '<span class="tag">inactive</span>'}</div>
        <div><strong>Вопрос:</strong> ${pair.question}</div>
        <div><strong>Ответы:</strong><ul>${answersHtml}</ul></div>
        <div>${tagsHtml}</div>
        <div class="knowledge-meta">
          👍 ${pair.rating_up || 0} | 👎 ${pair.rating_down || 0}<br>
          Создано: ${pair.created_at || ""}<br>
          Обновлено: ${pair.updated_at || ""}
        </div>
      `;

      const actions = document.createElement("div");
      actions.classList.add("knowledge-actions");

      const editBtn = document.createElement("button");
      editBtn.classList.add("small-btn");
      editBtn.textContent = "Редактировать";
      editBtn.addEventListener("click", () => openEditModal(pair));

      const delBtn = document.createElement("button");
      delBtn.classList.add("small-btn", "danger");
      delBtn.textContent = "Удалить";
      delBtn.addEventListener("click", () => deleteKnowledge(pair.id));

      actions.appendChild(editBtn);
      actions.appendChild(delBtn);
      item.appendChild(actions);

      knowledgeList.appendChild(item);
    });
  } catch {
    knowledgeList.innerHTML = "<p>Не удалось загрузить базу.</p>";
  }
}

importBtn.addEventListener("click", async () => {
  const raw = importData.value.trim();
  if (!raw) {
    alert("Поле импорта пустое.");
    return;
  }

  try {
    const parsed = JSON.parse(raw);

    const res = await fetch("/knowledge/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ custom_pairs: parsed })
    });

    const data = await res.json();
    alert(data.message || "Импорт завершён.");
    loadKnowledge();
    loadBackups();
  } catch {
    alert("Кривой JSON для импорта.");
  }
});

backupBtn.addEventListener("click", async () => {
  try {
    const res = await fetch("/knowledge/backup", { method: "POST" });
    const data = await res.json();
    backupStatus.textContent = data.message || "Backup создан.";
    loadBackups();
  } catch {
    backupStatus.textContent = "Ошибка создания backup.";
  }
});

async function loadBackups() {
  try {
    const res = await fetch("/backups");
    const data = await res.json();

    backupsList.innerHTML = "";
    (data.files || []).forEach(file => {
      const div = document.createElement("div");
      div.classList.add("backup-item");
      div.textContent = file;
      backupsList.appendChild(div);
    });

    if (!data.files || !data.files.length) {
      backupsList.innerHTML = "<div class='backup-item'>Пока нет backup.</div>";
    }
  } catch {
    backupsList.innerHTML = "<div class='backup-item'>Ошибка загрузки backup.</div>";
  }
}

searchInput.addEventListener("input", loadKnowledge);
tagInput.addEventListener("input", loadKnowledge);
refreshKnowledgeBtn.addEventListener("click", loadKnowledge);

loadHistory();
loadKnowledge();
loadBackups();
