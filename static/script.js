const chatBox = document.getElementById("chatBox");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

function addMessage(content, sender) {
  const msg = document.createElement("div");
  msg.classList.add("message", sender);
  msg.innerText = content;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function formatDateTime(isoString) {
  const d = new Date(isoString);
  const date = d.toLocaleDateString("vi-VN");
  const time = d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  return `${date} ${time}`;
}

async function sendMessage() {
  const content = userInput.value.trim();
  if (!content) return;

  addMessage(content, "user");
  userInput.value = "";

  try {
    const response = await fetch("http://127.0.0.1:8000/schedules/prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });

    if (!response.ok) throw new Error("API error: " + response.status);

    const data = await response.json();
    console.log("API trả về:", data); // 👈 Xem chính xác structure

    let message = "Không có phản hồi.";

    // Thử lấy trực tiếp
    if (data.message) {
      message = data.message;
    }
    // Nếu dữ liệu bọc trong result
    else if (data.result?.message) {
      message = data.result.message;
    }
    // Nếu dữ liệu bọc trong data
    else if (data.data?.message) {
      message = data.data.message;
    }

    if (data.schedules && data.schedules.length > 0) {
      message += "\n\n📅 Danh sách lịch:\n";
      data.schedules.forEach(sch => {
        message += `- ${sch.title}: ${formatDateTime(sch.start_time)} → ${formatDateTime(sch.end_time)}\n`;
      });
    } else if (data.result?.schedules) {
      message += "\n\n📅 Danh sách lịch:\n";
      data.result.schedules.forEach(sch => {
        message += `- ${sch.title}: ${formatDateTime(sch.start_time)} → ${formatDateTime(sch.end_time)}\n`;
      });
    }

    addMessage(message, "bot");
  } catch (error) {
    addMessage("Lỗi: " + error.message, "bot");
  }
}

sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});
