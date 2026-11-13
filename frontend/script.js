(() => {
    const form = document.getElementById("chat-form");
    const chatBox = document.getElementById("chatBox");
    const input = document.getElementById("message-input");
    const sendButton = document.getElementById("send-button");
    const typingIndicator = document.getElementById("typing-indicator");
    const quickReplies = document.getElementById("quick-replies");
    const connectionStatus = document.getElementById("connection-status");
    const connectionLabel = document.getElementById("connection-label");
    const themeToggle = document.getElementById("theme-toggle");
    const conversationHistory = [];
    let isProcessing = false;

    function currentTime() {
        return new Intl.DateTimeFormat(undefined, {
            hour: "numeric",
            minute: "2-digit",
        }).format(new Date());
    }

    const welcomeTime = chatBox.querySelector(".message-time");
    welcomeTime.dateTime = new Date().toISOString();
    welcomeTime.textContent = currentTime();

    function scrollToLatest() {
        chatBox.scrollTo({ top: chatBox.scrollHeight, behavior: "smooth" });
    }

    function appendMessage(role, text) {
        const row = document.createElement("article");
        row.className = `message-row ${role}-row`;

        const bubble = document.createElement("div");
        bubble.className = `message ${role}-message`;
        bubble.append(document.createTextNode(text));

        const timestamp = document.createElement("time");
        timestamp.className = "message-time";
        timestamp.dateTime = new Date().toISOString();
        timestamp.textContent = currentTime();
        bubble.append(timestamp);

        row.append(bubble);
        chatBox.insertBefore(row, typingIndicator);
        scrollToLatest();
    }

    function setProcessing(processing) {
        isProcessing = processing;
        input.disabled = processing;
        sendButton.disabled = processing;
        quickReplies.querySelectorAll("button").forEach((button) => {
            button.disabled = processing;
        });
        typingIndicator.hidden = !processing;

        if (processing) {
            scrollToLatest();
        }
    }

    async function loadQuickReplies() {
        const fallbackQuestions = [
            { label: "Admissions", question: "How do I apply for an undergraduate program?" },
            { label: "Fees", question: "What is the annual B.Tech tuition fee?" },
            { label: "Exams", question: "When are the semester exams?" },
            { label: "Timetable", question: "What is the weekly class schedule?" },
            { label: "Events & Clubs", question: "What clubs and campus events are available?" },
            { label: "Contact Office", question: "How can I contact the Campus Helpdesk?" },
        ];

        try {
            const response = await fetch("/api/quick-questions", {
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                throw new Error("Quick questions unavailable.");
            }
            const items = await response.json();
            if (!Array.isArray(items) || !items.length) {
                throw new Error("Quick questions payload was empty.");
            }
            renderQuickReplies(items);
            return;
        } catch {
            renderQuickReplies(fallbackQuestions);
        }
    }

    function renderQuickReplies(items) {
        quickReplies.innerHTML = "";
        items.forEach((item) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "quick-reply";
            button.textContent = item.label;
            button.dataset.question = item.question || item.label;
            quickReplies.append(button);
        });
    }

    async function checkHealth() {
        try {
            const response = await fetch("/api/health", {
                headers: { Accept: "application/json" },
            });
            if (!response.ok) {
                throw new Error(`Health check failed with status ${response.status}.`);
            }

            const health = await response.json();
            if (health.status !== "ok") {
                throw new Error("Helpdesk health check returned an unexpected status.");
            }

            connectionStatus.classList.remove("checking", "offline");
            connectionStatus.classList.add("online");
            connectionLabel.textContent = "Online";
        } catch {
            connectionStatus.classList.remove("checking", "online");
            connectionStatus.classList.add("offline");
            connectionLabel.textContent = "Offline";
        }
    }

    async function sendMessage(message = input.value) {
        const question = message.trim();
        if (!question || isProcessing) {
            return;
        }

        appendMessage("user", question);
        input.value = "";
        setProcessing(true);

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({
                    message: question,
                    history: conversationHistory.slice(-5),
                }),
            });

            let payload;
            try {
                payload = await response.json();
            } catch {
                throw new Error("The helpdesk returned an unreadable response. Please try again.");
            }

            if (!response.ok) {
                throw new Error(
                    typeof payload.error === "string"
                        ? payload.error
                        : "Something went wrong. Please try again.",
                );
            }

            if (typeof payload.reply !== "string" || !payload.reply.trim()) {
                throw new Error("The helpdesk did not return an answer. Please try again.");
            }

            appendMessage("bot", payload.reply);
            conversationHistory.push(
                { role: "user", content: question },
                { role: "assistant", content: payload.reply },
            );
        } catch (error) {
            const errorMessage = error instanceof TypeError
                ? "I could not connect to Campus Helpdesk. Please check that the helpdesk is online and try again."
                : error instanceof Error
                    ? error.message
                    : "I could not connect to the helpdesk. Please try again.";
            appendMessage("bot", errorMessage);
        } finally {
            setProcessing(false);
            input.focus();
        }
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        sendMessage();
    });

    quickReplies.addEventListener("click", (event) => {
        const button = event.target.closest("button");
        if (button && quickReplies.contains(button)) {
            sendMessage(button.dataset.question || button.textContent);
        }
    });

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const isDark = document.documentElement.dataset.theme !== "dark";
            document.documentElement.dataset.theme = isDark ? "dark" : "light";
            themeToggle.setAttribute("aria-pressed", String(isDark));
            themeToggle.setAttribute(
                "aria-label",
                isDark ? "Switch to light theme" : "Switch to dark theme",
            );
            themeToggle.title = isDark ? "Switch to light theme" : "Switch to dark theme";
            const icon = themeToggle.querySelector("span");
            if (icon) {
                icon.textContent = isDark ? "☀" : "☾";
            }
        });
    }

    loadQuickReplies();
    checkHealth();
})();
