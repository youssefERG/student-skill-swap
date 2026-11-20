"use strict";

document.addEventListener("submit", (event) => {
  const button = event.submitter;
  const message = button?.dataset.confirm;

  if (message && !window.confirm(message)) {
    event.preventDefault();
  }
});

const messageList = document.querySelector("#message-list");

if (messageList) {
  const conversationId = messageList.dataset.conversationId;
  const updatesUrl = messageList.dataset.updatesUrl;
  const userId = Number(messageList.dataset.userId);
  const countLabel = document.querySelector("#message-count-label");

  let lastMessageId = Number(messageList.dataset.lastMessageId || 0);
  let isCheckingForMessages = false;

  async function checkForNewMessages() {
    if (isCheckingForMessages) {
      return;
    }

    isCheckingForMessages = true;

    try {
      const response = await fetch(
        `${updatesUrl}?after_id=${lastMessageId}`,
        {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      if (data.messages.length > 0) {
        const emptyMessage = messageList.querySelector("[data-empty-message]");
        if (emptyMessage) {
          emptyMessage.remove();
        }

        for (const message of data.messages) {
          const article = document.createElement("article");
          article.className =
            message.sender_id === userId
              ? "message message-own"
              : "message message-other";
          article.dataset.messageId = String(message.id);

          const meta = document.createElement("p");
          meta.className = "message-meta";

          const senderName = document.createTextNode(
            message.sender_id === userId ? "You" : message.sender_name
          );

          const timestamp = document.createElement("span");
          timestamp.textContent = message.created_at;

          meta.appendChild(senderName);
          meta.appendChild(timestamp);

          const body = document.createElement("p");
          body.className = "message-body";
          body.textContent = message.body;

          article.appendChild(meta);
          article.appendChild(body);
          messageList.appendChild(article);

          lastMessageId = Math.max(lastMessageId, Number(message.id));
        }

        messageList.dataset.lastMessageId = String(lastMessageId);
        messageList.scrollTop = messageList.scrollHeight;
      }

      if (countLabel) {
        const count = Number(data.message_count);
        countLabel.textContent =
          `You have shared ${count} message${count === 1 ? "" : "s"} in this exchange.`;
      }
    } catch {
      // A temporary connection issue will be retried at the next interval.
    } finally {
      isCheckingForMessages = false;
    }
  }

  checkForNewMessages();
  window.setInterval(checkForNewMessages, 3000);
}