from typing import List, Dict, Any

def get_function_definitions() -> List[Dict[str, Any]]:
    """Định nghĩa các function cho Gemini AI"""
    return [
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
            "description": "Thêm lịch thông minh, tự động phân tích thời gian từ ngôn ngữ tự nhiên rồi thêm vào hệ thống",
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
