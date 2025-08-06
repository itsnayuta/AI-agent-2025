
import os
import google.generativeai as genai
from core.agents import advise_schedule
from core.tasks import execute_schedule, notify_schedule_change

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError('Vui lòng thiết lập biến môi trường GEMINI_API_KEY với API key của Gemini.')

# Khởi tạo Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Function calling
functions = [
    {
        "name": "advise_schedule",
        "description": "Tư vấn lập lịch cho người dùng.",
        "parameters": {"type": "object", "properties": {"user_info": {"type": "string"}}}
    },
    {
        "name": "execute_schedule",
        "description": "Thực hiện lập lịch cho người dùng.",
        "parameters": {"type": "object", "properties": {"schedule_info": {"type": "string"}}}
    },
    {
        "name": "notify_schedule_change",
        "description": "Gửi email khi có thay đổi thời gian biểu.",
        "parameters": {"type": "object", "properties": {"user_email": {"type": "string"}, "change_info": {"type": "string"}}}
    }
]

def handle_function_call(call):
    name = call["name"]
    args = call["args"]
    if name == "advise_schedule":
        return advise_schedule(args.get("user_info", ""))
    elif name == "execute_schedule":
        return execute_schedule(args.get("schedule_info", ""))
    elif name == "notify_schedule_change":
        return notify_schedule_change(args.get("user_email", ""), args.get("change_info", ""))
    else:
        return "Chức năng không hỗ trợ."

def process_user_input(user_input):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(
        user_input,
        tools=functions,
        tool_config={"function_calling": "auto"}
    )
    print("Gemini trả lời:", response.text)
    # Nếu Gemini yêu cầu gọi hàm
    if hasattr(response, "function_calls") and response.function_calls:
        for call in response.function_calls:
            result = handle_function_call(call)
            print(f"Kết quả thực thi hàm {call['name']}: {result}")

if __name__ == "__main__":
    print("=== AI Agent Lập lịch với Gemini ===")
    while True:
        user_input = input("Nhập yêu cầu của bạn (hoặc 'exit' để thoát): ")
        if user_input.lower() == "exit":
            break
        process_user_input(user_input)
