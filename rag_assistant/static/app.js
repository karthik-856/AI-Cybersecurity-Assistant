document.addEventListener("DOMContentLoaded", () => {
  const messagesList = document.getElementById("messages-list");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const clearBtn = document.getElementById("clear-chat-btn");
  const activeModelSpan = document.getElementById("active-model");
  const indexedChunksSpan = document.getElementById("indexed-chunks");

  // Fetch health and metadata
  async function fetchHealth() {
    try {
      const res = await fetch("/api/health");
      if (res.ok) {
        const data = await res.json();
        if (data.chat_model) activeModelSpan.textContent = data.chat_model;
        if (data.indexed_chunks !== undefined) {
          indexedChunksSpan.textContent = `${data.indexed_chunks} chunks`;
        }
      }
    } catch (e) {
      console.warn("Could not fetch server health:", e);
      indexedChunksSpan.textContent = "Connected";
    }
  }

  fetchHealth();

  // Auto-resize textarea
  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    userInput.style.height = Math.min(userInput.scrollHeight, 140) + "px";
  });

  // Enter to send (Shift+Enter for newline)
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event("submit"));
    }
  });

  // Clear chat button
  clearBtn.addEventListener("click", () => {
    messagesList.innerHTML = "";
    appendAssistantWelcome();
  });

  // Suggestion pill clicks
  document.addEventListener("click", (e) => {
    if (e.target.classList.contains("pill")) {
      const prompt = e.target.getAttribute("data-prompt");
      if (prompt) {
        userInput.value = prompt;
        chatForm.dispatchEvent(new Event("submit"));
      }
    }
  });

  // Handle message submission
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    // Append user message
    appendMessage(query, "user");
    userInput.value = "";
    userInput.style.height = "auto";
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Show typing indicator
    const loadingElem = showTypingIndicator();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query })
      });

      loadingElem.remove();

      if (!response.ok) {
        const err = await response.json();
        appendMessage(`Server error: ${err.detail || response.statusText}`, "assistant", ["Error"]);
        return;
      }

      const data = await response.json();
      appendMessage(data.answer, "assistant", data.sources, data.is_fallback);
    } catch (err) {
      loadingElem.remove();
      appendMessage(`Connection error: Failed to reach backend API. (${err.message})`, "assistant", ["Error"]);
    } finally {
      userInput.disabled = false;
      sendBtn.disabled = false;
      userInput.focus();
    }
  });

  function appendMessage(text, sender, sources = [], isFallback = false) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}-message`;

    const avatar = document.createElement("div");
    avatar.className = `avatar ${sender}-avatar`;
    avatar.textContent = sender === "assistant" ? "Z" : "U";

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    // Format paragraphs
    const paragraphs = text.split("\n\n").filter(p => p.trim());
    if (paragraphs.length > 0) {
      paragraphs.forEach(p => {
        const pElem = document.createElement("p");
        pElem.textContent = p.trim();
        pElem.style.marginBottom = "8px";
        bubble.appendChild(pElem);
      });
      // Remove margin on last child
      if (bubble.lastChild) bubble.lastChild.style.marginBottom = "0";
    } else {
      bubble.textContent = text;
    }

    contentDiv.appendChild(bubble);

    // Rule 6: Show source section title under each answer
    if (sender === "assistant") {
      const metaDiv = document.createElement("div");
      metaDiv.className = "message-meta";

      if (isFallback) {
        const tag = document.createElement("span");
        tag.className = "source-tag fallback-tag";
        tag.textContent = "Notice: Information Not in Document";
        metaDiv.appendChild(tag);
      } else if (sources && sources.length > 0) {
        sources.forEach(src => {
          const tag = document.createElement("span");
          tag.className = "source-tag";
          tag.textContent = `Source: ${src}`;
          metaDiv.appendChild(tag);
        });
      }

      contentDiv.appendChild(metaDiv);
    }

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    messagesList.appendChild(msgDiv);

    // Scroll to bottom
    messagesList.scrollTop = messagesList.scrollHeight;
  }

  function showTypingIndicator() {
    const msgDiv = document.createElement("div");
    msgDiv.className = "message assistant-message typing-indicator-msg";

    const avatar = document.createElement("div");
    avatar.className = "avatar assistant-avatar";
    avatar.textContent = "Z";

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.innerHTML = `
      <div class="typing-dots">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;

    contentDiv.appendChild(bubble);
    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    messagesList.appendChild(msgDiv);
    messagesList.scrollTop = messagesList.scrollHeight;

    return msgDiv;
  }

  function appendAssistantWelcome() {
    messagesList.innerHTML = `
      <div class="message assistant-message">
        <div class="avatar assistant-avatar">Z</div>
        <div class="message-content">
          <div class="message-bubble">
            <p>Welcome to <strong>ZUKA SOC Cyber Platform</strong> operations assistant. I am your grounded AI co-pilot. I answer inquiries strictly using our authoritative knowledge base and Standard Operating Procedures.</p>
            <div class="suggestions-container">
              <p class="suggestions-title">Try asking about:</p>
              <div class="suggestion-pills">
                <button class="pill" data-prompt="What machine learning architecture is used for IoT threat detection?">ML Architecture</button>
                <button class="pill" data-prompt="How does an analyst acknowledge an alert according to SOP-01?">SOP-01 Alert Ack</button>
                <button class="pill" data-prompt="Why can newly registered users not log in immediately?">Registration Security</button>
                <button class="pill" data-prompt="What countermeasures can be applied in the Defense Department?">Defense Countermeasures</button>
                <button class="pill" data-prompt="What is the monthly subscription price for ZUKA?">Pricing (Fallback Test)</button>
              </div>
            </div>
          </div>
          <div class="message-meta">
            <span class="source-tag">Source: 1. System Identity & Mission Overview</span>
          </div>
        </div>
      </div>
    `;
  }
});
