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
                        "description": "Yêu cầu lập lịch của người dùng, ví dụ: 'Họp team vào tuần sau'.",
                    },
                    "preferred_time_of_day": {
                        "type": "string",
                        "enum": ["sáng", "chiều", "tối"],
                        "description": "Khung thời gian mong muốn (nếu có).",
                    },
                    "duration": {
                        "type": "string",
                        "description": "Thời lượng ước tính của lịch (ví dụ: '2 tiếng', '30 phút').",
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["cao", "trung bình", "thấp"],
                        "description": "Mức độ ưu tiên (nếu người dùng đề cập).",
                    },
                },
                "required": ["user_request"],
            },
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
            "description": "Lấy danh sách tất cả lịch đã lưu.",
            "parameters": {"type": "object", "properties": {}, "required": []},
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
                        "description": "ID của lịch cần xóa",
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
        }
    ]
