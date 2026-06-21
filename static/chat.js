const messagesContainer = document.getElementById("messages");
const userMessageInput = document.getElementById("user-message");
const chatForm = document.getElementById("chat-form");
const sendBtn = document.getElementById("send-btn");
const chatFeedback = document.getElementById("chat-feedback");
const clearBtn = document.getElementById("clear-btn");
const suggestionBtns = document.querySelectorAll(".suggestion-btn");

let conversationHistory = [];

function getConfidenceBadge(score) {
    if (score >= 0.7) {
        return { level: "high", label: "✓ High confidence", class: "confidence-high" };
    } else if (score >= 0.5) {
        return { level: "medium", label: "~ Medium confidence", class: "confidence-medium" };
    } else {
        return { level: "low", label: "⚠ Low confidence", class: "confidence-low" };
    }
}

function formatSourceInfo(retrievedContext) {
    if (!retrievedContext || retrievedContext.length === 0) {
        return 'From: Fallback response';
    }

    const topMatch = retrievedContext[0];
    const confidence = getConfidenceBadge(topMatch.score);

    return `From: FAQ match (${(topMatch.score * 100).toFixed(0)}% match)`;
}

function addMessage(text, isUser, metadata = {}) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${isUser ? "user" : "assistant"}`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;

    messageDiv.appendChild(bubble);

    if (!isUser && metadata.score !== undefined) {
        const confidence = getConfidenceBadge(metadata.score);
        const metaDiv = document.createElement("div");
        metaDiv.className = "message-meta";

        const badge = document.createElement("span");
        badge.className = `confidence-badge ${confidence.class}`;
        badge.textContent = confidence.label;

        const source = document.createElement("span");
        source.className = "source-link";
        source.textContent = metadata.sourceText || "View FAQ";

        metaDiv.appendChild(badge);
        metaDiv.appendChild(source);
        messageDiv.appendChild(metaDiv);
    }

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    conversationHistory.push({ role: isUser ? "user" : "assistant", text });
}

function showEmptyState() {
    if (conversationHistory.length === 0) {
        const empty = document.createElement("div");
        empty.className = "empty-state";
        empty.innerHTML = `
      <p>👋 Welcome! Ask me anything about our FAQs.</p>
      <p style="margin-top: 10px; font-size: 0.9rem; color: var(--text-tertiary);">Use the suggested questions on the left or type your own.</p>
    `;
        messagesContainer.appendChild(empty);
    }
}

async function sendMessage() {
    const message = userMessageInput.value.trim();

    if (!message) {
        chatFeedback.textContent = "Please enter a message.";
        chatFeedback.style.color = "var(--text-tertiary)";
        return;
    }

    userMessageInput.value = "";
    sendBtn.disabled = true;
    chatFeedback.textContent = "";

    addMessage(message, true);

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, top_k: 3 }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        const topScore = data.retrieved_context?.[0]?.score || 0;
        addMessage(data.answer, false, {
            score: topScore,
            sourceText: `Match: ${data.source}`,
        });

        chatFeedback.textContent = `Retrieved ${data.retrieved_context?.length || 0} FAQ(s) • Source: ${data.source}`;
        chatFeedback.style.color = "var(--text-tertiary)";
    } catch (error) {
        addMessage(`Sorry, something went wrong: ${error.message}`, false);
        chatFeedback.textContent = "Error occurred. Please try again.";
        chatFeedback.style.color = "#dc3545";
    } finally {
        sendBtn.disabled = false;
        userMessageInput.focus();
    }
}

chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage();
});

suggestionBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
        const question = btn.dataset.question;
        userMessageInput.value = question;
        userMessageInput.focus();
        sendMessage();
    });
});

clearBtn.addEventListener("click", () => {
    if (confirm("Clear conversation history?")) {
        messagesContainer.innerHTML = "";
        conversationHistory = [];
        showEmptyState();
    }
});

showEmptyState();
userMessageInput.focus();
