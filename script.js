(() => {
  "use strict";

  const log = document.getElementById("log");
  const form = document.getElementById("form");
  const input = document.getElementById("input");
  const chips = document.getElementById("chips");
  const clearBtn = document.getElementById("clearBtn");
  const sendBtn = form.querySelector("button[type=submit]");

  const WELCOME = "Hi! I'm the ShopEase assistant. Ask me about orders, shipping, returns, or payments.";

  function scrollToEnd() {
    log.scrollTop = log.scrollHeight;
  }

  function addMessage(role, text, extras = {}) {
    const wrap = document.createElement("div");
    wrap.className = `msg msg--${role}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);

    if (extras.matched) {
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `Matched FAQ: ${extras.matched} (${Math.round(extras.confidence * 100)}% similar)`;
      wrap.appendChild(meta);
    }

    if (extras.suggestions && extras.suggestions.length) {
      const box = document.createElement("div");
      box.className = "suggest";
      extras.suggestions.forEach((q) => box.appendChild(makeChip(q)));
      wrap.appendChild(box);
    }

    log.appendChild(wrap);
    scrollToEnd();
    return wrap;
  }

  function makeChip(question) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = question;
    btn.addEventListener("click", () => send(question));
    return btn;
  }

  function showTyping() {
    const wrap = document.createElement("div");
    wrap.className = "msg msg--bot";
    wrap.innerHTML = '<div class="bubble typing" aria-label="Assistant is typing"><span></span><span></span><span></span></div>';
    log.appendChild(wrap);
    scrollToEnd();
    return wrap;
  }

  async function send(text) {
    text = text.trim();
    if (!text) return;

    addMessage("user", text);
    input.value = "";
    sendBtn.disabled = true;
    const typing = showTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const data = await res.json();
      typing.remove();
      addMessage("bot", data.answer, {
        matched: data.type === "answer" ? data.matched_question : null,
        confidence: data.confidence,
        suggestions: data.suggestions,
      });
    } catch (err) {
      typing.remove();
      addMessage("bot", "I can't reach the server right now. Check that the app is running and try again.");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  async function loadSuggestions() {
    chips.innerHTML = "";
    try {
      const res = await fetch("/api/suggestions");
      const data = await res.json();
      data.suggestions.forEach((q) => chips.appendChild(makeChip(q)));
    } catch (_) { /* chips are optional */ }
  }

  function reset() {
    log.innerHTML = "";
    addMessage("bot", WELCOME);
    loadSuggestions();
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    send(input.value);
  });
  clearBtn.addEventListener("click", reset);

  reset();
})();
