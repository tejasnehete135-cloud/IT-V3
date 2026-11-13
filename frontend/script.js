(() => {
  const form = document.querySelector("#chat-form");
  const input = document.querySelector("#message-input");
  const sendButton = document.querySelector("#send-button");
  const conversation = document.querySelector("#conversation");
  const typing = document.querySelector("#typing-indicator");
  const connectionStatus = document.querySelector("#connection-status");
  const connectionLabel = document.querySelector("#connection-label");
  const quickReplies = document.querySelector("#quick-replies");
  const themeToggle = document.querySelector("#theme-toggle");
  const welcomeTime = document.querySelector("#welcome-time");
  const history = [];
  let busy = false;

  const timeNow = () => new Intl.DateTimeFormat([], {
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date());

  welcomeTime.dateTime = new Date().toISOString();
  welcomeTime.textContent = timeNow();

  function appendInlineMarkdown(element, text) {
    const pattern = /\*\*(.+?)\*\*/g;
    let cursor = 0;
    let match;
    while ((match = pattern.exec(text)) !== null) {
      element.append(document.createTextNode(text.slice(cursor, match.index)));
      const strong = document.createElement("strong");
      strong.textContent = match[1];
      element.append(strong);
      cursor = pattern.lastIndex;
    }
    element.append(document.createTextNode(text.slice(cursor)));
  }

  function appendFormattedReply(container, text) {
    let list = null;
    let listType = "";
    text.split(/\r?\n/).forEach((line) => {
      const unordered = line.match(/^\s*[-*]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      const item = unordered || ordered;
      if (item) {
        const nextType = unordered ? "ul" : "ol";
        if (!list || listType !== nextType) {
          list = document.createElement(nextType);
          listType = nextType;
          container.append(list);
        }
        const listItem = document.createElement("li");
        appendInlineMarkdown(listItem, item[1]);
        list.append(listItem);
        return;
      }
      list = null;
      listType = "";
      if (!line.trim()) return;
      const paragraph = document.createElement("p");
      appendInlineMarkdown(paragraph, line);
      container.append(paragraph);
    });
  }

  function appendMessage(role, text, category = "", sources = [], source = "") {
    const article = document.createElement("article");
    article.className = `message ${role === "user" ? "user-message" : "bot-message"}`;
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = role === "user" ? "Y" : "C";

    const content = document.createElement("div");
    content.className = "message-content";
    const meta = document.createElement("div");
    meta.className = "message-meta";
    const name = document.createElement("strong");
    name.textContent = role === "user" ? "You" : "Campus";
    const time = document.createElement("time");
    time.dateTime = new Date().toISOString();
    time.textContent = timeNow();
    meta.append(name, time);

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    if (role === "assistant") appendFormattedReply(bubble, text);
    else {
      const paragraph = document.createElement("p");
      paragraph.textContent = text;
      bubble.append(paragraph);
    }
    if (role === "assistant" && category) {
      const tag = document.createElement("span");
      tag.className = "category-tag";
      tag.textContent = category.charAt(0).toUpperCase() + category.slice(1);
      bubble.append(tag);
    }
    if (role === "assistant" && source) {
      const sourceTag = document.createElement("span");
      sourceTag.className = `source-mode ${source}`;
      sourceTag.textContent = source === "fallback" ? "Campus data · offline answer" : "AI answer · Campus data";
      bubble.append(sourceTag);
    }
    if (role === "assistant" && sources.length) {
      const sourceList = document.createElement("div");
      sourceList.className = "source-list";
      sourceList.setAttribute("aria-label", "Answer sources");
      sources.forEach((source) => {
        const tag = document.createElement("span");
        tag.className = "source-tag";
        tag.textContent = source.title || source.category || "College data";
        sourceList.append(tag);
      });
      bubble.append(sourceList);
    }

    content.append(meta, bubble);
    article.append(...(role === "user" ? [content, avatar] : [avatar, content]));
    conversation.insertBefore(article, typing);
    conversation.scrollTop = conversation.scrollHeight;
  }

  function setBusy(value) {
    busy = value;
    sendButton.disabled = value || !input.value.trim();
    input.disabled = value;
    typing.hidden = !value;
    if (value) conversation.scrollTop = conversation.scrollHeight;
  }

  async function sendMessage(text) {
    const message = text.trim();
    if (!message || busy) return;
    appendMessage("user", message);
    quickReplies.remove();
    const requestHistory = history.slice(-5);
    history.push({ role: "user", content: message });
    input.value = "";
    input.style.height = "auto";
    setBusy(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history: requestHistory }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Something went wrong. Please try again.");
      appendMessage("assistant", payload.reply, payload.category, [], payload.source);
      history.push({ role: "assistant", content: payload.reply });
    } catch (error) {
      appendMessage(
        "assistant",
        error instanceof TypeError
          ? "I couldn't connect to the helpdesk server. Please make sure the backend is running and try again."
          : error.message,
      );
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(input.value);
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 110)}px`;
    sendButton.disabled = busy || !input.value.trim();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  quickReplies.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-question]");
    if (button) sendMessage(button.dataset.question);
  });
  document.querySelector("#clear-chat").addEventListener("click", () => window.location.reload());

  async function loadQuickQuestions() {
    try {
      const response = await fetch("/api/quick-questions");
      if (!response.ok) throw new Error(`Quick questions request failed (${response.status}).`);
      const questions = await response.json();
      questions.forEach(({ label, question }) => {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.question = question;
        const icon = document.createElement("span");
        icon.textContent = "›";
        button.append(icon, document.createTextNode(` ${label}`));
        quickReplies.append(button);
      });
    } catch (error) {
      console.error("Could not load quick questions:", error);
    }
  }
  loadQuickQuestions();

  function readThemePreference() {
    try {
      return localStorage.getItem("helpdesk-theme");
    } catch {
      return null;
    }
  }

  function saveThemePreference(theme) {
    try {
      localStorage.setItem("helpdesk-theme", theme);
    } catch {
      // Theme changes still apply for the current page view.
    }
  }

  if (readThemePreference() === "dark") document.body.classList.add("dark");
  function updateThemeButton() {
    const dark = document.body.classList.contains("dark");
    themeToggle.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    themeToggle.innerHTML = dark
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.2 15.1A8.3 8.3 0 0 1 8.9 3.8 8.5 8.5 0 1 0 20.2 15.1Z"/></svg>';
  }
  updateThemeButton();
  themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("dark");
    saveThemePreference(document.body.classList.contains("dark") ? "dark" : "light");
    updateThemeButton();
  });

  async function checkHealth() {
    try {
      const response = await fetch("/api/health", { cache: "no-store" });
      const health = await response.json();
      const online = health.lm_studio === "reachable";
      connectionStatus.classList.toggle("online", online);
      connectionStatus.classList.toggle("offline", !online);
      connectionLabel.textContent = online ? "Online" : "Offline · FAQ fallback available";
    } catch {
      connectionStatus.classList.remove("online");
      connectionStatus.classList.add("offline");
      connectionLabel.textContent = "Server unavailable";
    }
  }
  checkHealth();
  window.setInterval(checkHealth, 30000);
})();
