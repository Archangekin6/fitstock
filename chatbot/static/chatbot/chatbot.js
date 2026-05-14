document.addEventListener("DOMContentLoaded", function () {
  console.log("Chatbot JS chargé !");

  const icon = document.getElementById("chatbot-icon");
  const windowChat = document.getElementById("chatbot-window");
  const closeBtn = document.getElementById("chatbot-close");
  const sendBtn = document.getElementById("chatbot-send");
  const input = document.getElementById("chatbot-input");
  const messages = document.getElementById("chatbot-body");

  if (!icon || !windowChat || !closeBtn || !sendBtn || !input || !messages) {
    console.error("Erreur : éléments chatbot introuvables !");
    return;
  }

  function toggleChatbot() {
    if (windowChat.style.display === "none" || windowChat.style.display === "") {
      windowChat.style.display = "flex";
    } else {
      windowChat.style.display = "none";
    }
  }

  icon.addEventListener("click", toggleChatbot);
  closeBtn.addEventListener("click", toggleChatbot);

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    // Afficher le message utilisateur
    messages.innerHTML += `<div class="user-msg">${text}</div>`;
    input.value = "";
    messages.scrollTop = messages.scrollHeight;

    // Indicateur de chargement
    const loadingDiv = document.createElement("div");
    loadingDiv.id = "chatbot-loading";
    loadingDiv.className = "bot-msg";
    loadingDiv.textContent = "⏳ En cours...";
    messages.appendChild(loadingDiv);
    messages.scrollTop = messages.scrollHeight;

    try {
      const response = await fetch("/chatbot/ai/?message=" + encodeURIComponent(text), {
        method: "GET",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      });

      const data = await response.json();
      loadingDiv.remove();
      messages.innerHTML += `<div class="bot-msg">${data.response}</div>`;
    } catch (err) {
      console.error("Erreur:", err);
      loadingDiv.remove();
      messages.innerHTML += `<div class="bot-msg">⚠️ Erreur serveur</div>`;
    }

    messages.scrollTop = messages.scrollHeight;
  }

  sendBtn.addEventListener("click", sendMessage);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") sendMessage();
  });
});

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + "=")) {
        cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
