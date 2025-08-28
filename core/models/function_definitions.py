from typing import List, Dict, Any

def get_function_definitions() -> List[Dict[str, Any]]:
    """Định nghĩa các function cho Gemini AI"""
    return [
        {
            "name": "advise_schedule",
            "description": "Tư vấn lập lịch, trả về ngày/thời gian cụ thể hoặc yêu cầu thêm thông tin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "Yêu cầu lập lịch của người dùng, ví dụ: 'Họp team vào thứ 6 tuần này'."
                    },
                    "preferred_time_of_day": {
                        "type": "string",
                        "enum": ["sáng", "chiều", "tối"],
                        "description": "Khung thời gian mong muốn."
                    },
                    "preferred_date": {
                        "type": "string",
                        "description": "Ngày cụ thể người dùng yêu cầu, format YYYY-MM-DD (nếu xác định được)."
                    },
                    "preferred_weekday": {
                        "type": "string",
                        "enum": ["Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật"],
                        "description": "Ngày trong tuần mà người dùng yêu cầu (nếu có)."
                    },
                    "duration": {
                        "type": "string",
                        "description": "Thời lượng ước tính của lịch (ví dụ: '2 tiếng', '30 phút')."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["cao", "trung bình", "thấp"],
                        "description": "Mức độ ưu tiên (nếu có)."
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
                    "title": {
                        "type": "string",
                        "description": "Tiêu đề ngắn gọn của lịch trình, ví dụ: 'Đi ăn cua' hoặc 'Họp team'",
                    },
                    "description": {
                        "type": "string",
                        "description": "Mô tả chi tiết của lịch trình, có thể bao gồm địa điểm, chi tiết công việc, v.v.",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Thời gian bắt đầu của lịch trình theo định dạng ISO 8601 (VD: 2025-08-08T19:00:00). Nếu không tìm thấy, để trống.",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Thời gian kết thúc của lịch trình theo định dạng ISO 8601 (VD: 2025-08-08T21:00:00). Nếu không tìm thấy, để trống.",
                    },
                },
                "required": ["title", "start_time"],
            },
        },
        {
            "name": "get_schedules",
            "description": "Lấy danh sách lịch đã lưu. Có thể lọc theo ngày, tháng, hoặc năm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Ngày cụ thể để lọc lịch, định dạng YYYY-MM-DD."
                    },
                    "month": {
                        "type": "integer",
                        "description": "Tháng để lọc lịch (số từ 1-12). Cần có 'year'."
                    },
                    "year": {
                        "type": "integer",
                        "description": "Năm để lọc lịch."
                    }
                },
                "required": []
            },
        },
        {
            "name": "update_schedule",
            "description": "Cập nhật thông tin lịch đã có.",
            "parameters": {
                "type": "object",
                "properties": {
                    "schedule_id": {
                        "type": "integer",
                        "description": "ID của lịch cần cập nhật",
                    },
                    "title": {
                        "type": "string",
                        "description": "Tiêu đề mới (tùy chọn)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Mô tả mới (tùy chọn)",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Thời gian bắt đầu mới (tùy chọn)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Thời gian kết thúc mới (tùy chọn)",
                    },
                },
                "required": ["schedule_id"],
            },
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
        },
        {
            "name": "setup_notification_email",
            "description": "Thiết lập email nhận thông báo lịch trình.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Địa chỉ email để nhận thông báo"
                    }
                },
                "required": ["email"]
            }
        },
        {
            "name": "handle_greeting_goodbye",
            "description": "Xử lý các chủ đề hội thoại cơ bản như chào hỏi, cảm ơn, tạm biệt, exit/quit, hoặc các câu hỏi đơn giản như 'bạn là ai', 'bạn khỏe không'. CHỈ sử dụng khi KHÔNG THỂ trả lời từ context có sẵn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Nội dung hội thoại của người dùng (ví dụ: 'Chào bạn', 'Cảm ơn', 'Bạn là ai?', 'exit', 'quit', 'thoát')."
                    },
                    "is_exit": {
                        "type": "boolean",
                        "description": "True nếu người dùng muốn thoát/kết thúc cuộc trò chuyện (exit, quit, thoát, bye)."
                    }
                },
                "required": ["message"]
            }
        },
        {
            "name": "handle_off_topic_query",
            "description": "Phản hồi khi yêu cầu của người dùng không liên quan đến việc lập lịch hoặc các chức năng có sẵn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Câu hỏi hoặc yêu cầu không liên quan của người dùng (ví dụ: 'Thời tiết hôm nay thế nào?', 'Bạn có thể kể chuyện cười không?')."
                    }
                },
                "required": ["query"]
            }
        }
    ]