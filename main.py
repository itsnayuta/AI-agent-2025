
import os
import google.generativeai as genai
from core.ScheduleAdvisor import ScheduleAdvisor
from core.ExecuteSchedule import ExecuteSchedule
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
        "name": "smart_add_schedule",
        "description": "Thêm lịch thông minh - tự động phân tích thời gian từ ngôn ngữ tự nhiên rồi thêm vào hệ thống",
        "parameters": {
            "type": "object",
            "properties": {
                "user_request": {
                    "type": "string",
                    "description": "Yêu cầu thêm lịch bằng ngôn ngữ tự nhiên (VD: 'thêm lịch khám răng vào 7h tối thứ 7 tuần này, thời gian 2 tiếng')"
                }
            },
            "required": ["user_request"]
        }
    },
    {
        "name": "get_schedules",
        "description": "Lấy danh sách tất cả lịch đã lưu.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "update_schedule",
        "description": "Cập nhật thông tin lịch đã có.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "integer",
                    "description": "ID của lịch cần cập nhật"
                },
                "title": {
                    "type": "string",
                    "description": "Tiêu đề mới (tùy chọn)"
                },
                "description": {
                    "type": "string",
                    "description": "Mô tả mới (tùy chọn)"
                },
                "start_time": {
                    "type": "string", 
                    "description": "Thời gian bắt đầu mới (tùy chọn)"
                },
                "end_time": {
                    "type": "string",
                    "description": "Thời gian kết thúc mới (tùy chọn)"
                }
            },
            "required": ["schedule_id"]
        }
    },
    {
        "name": "delete_schedule",
        "description": "Xóa lịch khỏi hệ thống.",
        "parameters": {
            "type": "object",
            "properties": {
                "schedule_id": {
                    "type": "integer",
                    "description": "ID của lịch cần xóa"
                }
            },
            "required": ["schedule_id"]
        }
    }
]

def handle_function_call(call, user_input):
    name = call.name
    args = call.args if hasattr(call, 'args') else {}
    advisor = ScheduleAdvisor()
    executor = ExecuteSchedule()
    
    try:
        if name == "advise_schedule":
            user_request = args.get('user_request', user_input)
            result = advisor.advise_schedule(user_request)
            return advisor.format_response(result)
            
        elif name == "smart_add_schedule":
            user_request = args.get('user_request', user_input)
            
            print(f"🔍 DEBUG smart_add_schedule:")
            print(f"   user_request: {user_request}")
            
            # 1. Dùng ScheduleAdvisor để parse thời gian
            advisor_result = advisor.advise_schedule(user_request)
            
            if 'suggested_time' in advisor_result:
                suggested_time = advisor_result['suggested_time']
                print(f"   ✅ Parsed time: {suggested_time}")
                
                # 2. Extract title và description
                import re
                title_match = re.search(r'(khám răng|học|họp|đi|mua|gặp|làm)', user_request, re.IGNORECASE)
                title = title_match.group(0) if title_match else "Lịch mới"
                
                # 3. Extract duration
                duration_match = re.search(r'(\d+)\s*(tiếng|giờ|phút)', user_request)
                if duration_match:
                    duration_num = int(duration_match.group(1))
                    duration_unit = duration_match.group(2)
                    if 'tiếng' in duration_unit or 'giờ' in duration_unit:
                        end_time = suggested_time.replace(hour=suggested_time.hour + duration_num)
                    else:  # phút
                        end_time = suggested_time.replace(minute=suggested_time.minute + duration_num)
                else:
                    end_time = suggested_time.replace(hour=suggested_time.hour + 1)  # default 1h
                
                # 4. Format thời gian
                start_time_str = suggested_time.strftime('%Y-%m-%dT%H:%M:%S')
                end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
                
                print(f"   ✅ Final times: {start_time_str} - {end_time_str}")
                
                # 5. Thêm vào database
                result = executor.add_schedule(title, title, start_time_str, end_time_str)
                return result
            else:
                return "❌ Không thể phân tích thời gian từ yêu cầu của bạn."
            
        elif name == "get_schedules":
            schedules = executor.get_schedules()
            if not schedules:
                return "📋 Hiện tại chưa có lịch nào được lưu."
            
            result = "📋 **Danh sách lịch:**\n"
            for schedule in schedules:
                result += f"ID: {schedule[0]} | {schedule[1]} | {schedule[3]} - {schedule[4]}\n"
                result += f"   Mô tả: {schedule[2]}\n\n"
            return result
            
        elif name == "update_schedule":
            schedule_id = args.get('schedule_id')
            title = args.get('title')
            description = args.get('description')
            start_time = args.get('start_time')
            end_time = args.get('end_time')
            
            if not schedule_id:
                return "❌ Thiếu ID lịch cần cập nhật."
            
            result = executor.update_schedule(schedule_id, title, description, start_time, end_time)
            return result
            
        elif name == "delete_schedule":
            schedule_id = args.get('schedule_id')
            
            if not schedule_id:
                return "❌ Thiếu ID lịch cần xóa."
            
            result = executor.delete_schedule(schedule_id)
            return result         
        else:
            return "❌ Chức năng không hỗ trợ."
            
    except Exception as e:
        return f"❌ Lỗi khi thực hiện: {str(e)}"
    finally:
        executor.close()

def process_user_input(user_input):
    print("🔄 Đang xử lý yêu cầu...")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        system_prompt = f"""QUAN TRỌNG: Hôm nay là 2025-08-06 (Thứ 4).

Phân tích yêu cầu và gọi function phù hợp:
- Nếu user muốn TƯ VẤN/KIỂM TRA thời gian → advise_schedule
- Nếu user muốn THÊM LỊCH với thời gian cụ thể → add_schedule 
- Nếu user muốn THÊM LỊCH nhưng chưa rõ thời gian → advise_schedule TRƯỚC
- Xem danh sách lịch → get_schedules
- Cập nhật lịch → update_schedule (cần schedule_id)
- Xóa lịch → delete_schedule (cần schedule_id)

LƯU Ý: 
- Thứ 7 tuần này = 2025-08-09
- Chủ nhật tuần này = 2025-08-10
- KHÔNG tự tạo thời gian năm 2024!
- Ưu tiên dùng smart_add_schedule cho yêu cầu thêm lịch

Yêu cầu: {user_input}"""
        
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
            print(f"🔍 DEBUG Gemini function call:")
            print(f"   Function: {function_call.name}")
            print(f"   Args: {dict(function_call.args) if hasattr(function_call, 'args') else 'No args'}")
            function_response = handle_function_call(function_call, user_input)
            print("🤖 Gemini AI Response:")
            print(function_response)
            return function_response
        else:
            print("📋 Gemini không gọi function, sử dụng logic trực tiếp...")
            # Fallback: sử dụng logic trực tiếp
            advisor = ScheduleAdvisor()
            result = advisor.advise_schedule(user_input)
            formatted_response = advisor.format_response(result)
            print("🤖 Direct Response:")
            print(formatted_response)
            return formatted_response
            
    except Exception as e:
        print(f"❌ Lỗi Gemini API: {e}")

if __name__ == "__main__":
    print("=== AI Agent Lập lịch ===")
    
    while True:
        user_input = input("\n📝 Nhập yêu cầu của bạn (hoặc 'exit' hoặc 'quit' để thoát): ")
        if user_input.lower() in ["exit", "quit", "thoát"]:
            print("👋 Tạm biệt!")
            break
        process_user_input(user_input)
