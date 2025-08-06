
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

# Function calling
functions = [
    {
        "name": "advise_schedule",
        "description": "Tư vấn lập lịch cho người dùng dựa trên thời gian và loại công việc được đề cập.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Yêu cầu lập lịch của người dùng"
                }
            },
            "required": ["user_request"]
        }
    },
    {
        "name": "execute_schedule", 
        "description": "Thực hiện lập lịch sau khi đã tư vấn xong.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule_details": {
                    "type": "string",
                    "description": "Chi tiết lịch trình cần thực hiện"
                }
            },
            "required": ["schedule_details"]
        }
    },
    {
        "name": "notify_schedule_change",
        "description": "Gửi email thông báo khi có thay đổi lịch trình.",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Địa chỉ email người nhận"
                },
                "message": {
                    "type": "string",
                    "description": "Nội dung thông báo thay đổi"
                }
            },
            "required": ["email", "message"]
        }
    }
]

def handle_function_call(call, user_input):
    name = call.name
    args = call.args if hasattr(call, 'args') else {}
    advisor = ScheduleAdvisor()
    
    if name == "advise_schedule":
        user_request = args.get('user_request', user_input)
        result = advisor.advise_schedule(user_request)
        return advisor.format_response(result)
    elif name == "execute_schedule":
        schedule_details = args.get('schedule_details', user_input)
        return execute_schedule(schedule_details)
    elif name == "notify_schedule_change":
        email = args.get('email', "user@example.com")
        message = args.get('message', user_input)
        return notify_schedule_change(email, message)
    else:
        return "Chức năng không hỗ trợ."

def process_user_input(user_input):
    print("🔄 Đang xử lý yêu cầu...")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        system_prompt = f"""Phân tích yêu cầu và gọi function phù hợp:
        - Tư vấn lịch → advise_schedule
        - Yêu cầu: {user_input}"""
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.1, 
            max_output_tokens=100  
        )
        
        response = model.generate_content(
            system_prompt,
            tools=[{"function_declarations": functions}],
            tool_config={"function_calling_config": {"mode": "ANY"}},
            generation_config=generation_config
        )
        
        if hasattr(response.candidates[0].content.parts[0], 'function_call'):
            function_call = response.candidates[0].content.parts[0].function_call
            function_response = handle_function_call(function_call, user_input)
            print("🤖 Gemini AI Response:")
            print(function_response)
            return function_response
        else:
            print("📋 Timeout, không tìm thấy function call phù hợp.")
            
    except Exception as e:
        print(f"❌ Lỗi Gemini API: {e}")

if __name__ == "__main__":
    print("=== AI Agent Lập lịch ===")
    
    while True:
        user_input = input("\n📝 Nhập yêu cầu của bạn (hoặc 'exit' hoặc 'quit' để thoát): ")
        if user_input.lower() == "exit" or user_input.lower() == "quit":
            print("👋 Tạm biệt!")
            break
        process_user_input(user_input)
