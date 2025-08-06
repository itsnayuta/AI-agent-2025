
import os
import google.generativeai as genai 
from core.agents import ScheduleAdvisor
from core.tasks import execute_schedule, notify_schedule_change
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError('Vui lòng thiết lập biến môi trường GEMINI_API_KEY với API key của Gemini.')

# Khởi tạo Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Function calling - chuẩn Gemini API
functions = [
    {
        "name": "advise_schedule",
        "description": "Tư vấn lập lịch cho người dùng."
    },
    {
        "name": "execute_schedule", 
        "description": "Thực hiện lập lịch cho người dùng."
    },
    {
        "name": "notify_schedule_change",
        "description": "Gửi email khi có thay đổi thời gian biểu."
    }
]

def handle_function_call(call):
    name = call.name
    args = call.args if hasattr(call, 'args') else {}
    advisor = ScheduleAdvisor()
    if name == "advise_schedule":
        result = advisor.advise_schedule(user_input)
        return advisor.format_response(result)
    elif name == "execute_schedule":
        return execute_schedule(user_input)
    elif name == "notify_schedule_change":
        return notify_schedule_change("user@example.com", user_input)
    else:
        return "Chức năng không hỗ trợ."

def process_user_input(user_input):
    # Test trực tiếp logic AI trước
    advisor = ScheduleAdvisor()
    result = advisor.advise_schedule(user_input)
    response_text = advisor.format_response(result)
    print("Kết quả tư vấn:")
    print(response_text)
    
    # Sau này có thể thêm Gemini function calling
    # model = genai.GenerativeModel('gemini-1.5-flash')
    # response = model.generate_content(user_input, tools=functions)
    
    return result

if __name__ == "__main__":
    print("=== AI Agent Lập lịch với Gemini ===")
    while True:
        user_input = input("Nhập yêu cầu của bạn (hoặc 'exit' để thoát): ")
        if user_input.lower() == "exit":
            break
        process_user_input(user_input)
