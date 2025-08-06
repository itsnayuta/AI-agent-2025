task_categories = {
    'meeting': {
        'keywords': ['họp', 'meeting', 'gặp mặt', 'thảo luận', 'trao đổi'],
        'duration': 60,
        'priority': 'Bình thường',
        'best_time': (9, 16)
    },
    'interview': {
        'keywords': ['phỏng vấn', 'interview', 'tuyển dụng'],
        'duration': 45,
        'priority': 'Cao',
        'best_time': (9, 11)
    },
    'client_meeting': {
        'keywords': ['gặp khách', 'khách hàng', 'client', 'tư vấn'],
        'duration': 90,
        'priority': 'Cao',
        'best_time': (9, 16)
    },
    'deadline': {
        'keywords': ['deadline', 'hạn chót', 'nộp bài', 'báo cáo'],
        'duration': 120,
        'priority': 'Cao',
        'best_time': (8, 11)
    },
    'training': {
        'keywords': ['đào tạo', 'training', 'học tập', 'workshop'],
        'duration': 180,
        'priority': 'Bình thường',
        'best_time': (9, 15)
    },
    'personal': {
        'keywords': ['cá nhân', 'bác sĩ', 'dentist', 'sức khỏe'],
        'duration': 30,
        'priority': 'Cao',
        'best_time': (8, 10)
    },
    'presentation': {
        'keywords': ['thuyết trình', 'presentation', 'báo cáo', 'demo', 'trình bày'],
        'duration': 75,
        'priority': 'Cao',
        'best_time': (9, 14)
    },
    'conference': {
        'keywords': ['hội thảo', 'conference', 'seminar', 'sự kiện', 'webinar'],
        'duration': 240,
        'priority': 'Bình thường',
        'best_time': (9, 16)
    },
    'review': {
        'keywords': ['đánh giá', 'review', 'kiểm tra', 'audit', 'assessment'],
        'duration': 90,
        'priority': 'Bình thường',
        'best_time': (10, 15)
    },
    'brainstorm': {
        'keywords': ['động não', 'brainstorm', 'sáng tạo', 'ý tưởng', 'planning'],
        'duration': 120,
        'priority': 'Bình thường',
        'best_time': (9, 12)
    },
    'negotiation': {
        'keywords': ['đàm phán', 'negotiation', 'thương lượng', 'hợp đồng'],
        'duration': 150,
        'priority': 'Cao',
        'best_time': (10, 16)
    },
    'phone_call': {
        'keywords': ['gọi điện', 'call', 'điện thoại', 'liên lạc'],
        'duration': 15,
        'priority': 'Bình thường',
        'best_time': (9, 17)
    },
    'travel': {
        'keywords': ['đi công tác', 'travel', 'chuyến đi', 'business trip'],
        'duration': 480,
        'priority': 'Bình thường',
        'best_time': (6, 18)
    },
    'team_building': {
        'keywords': ['team building', 'gắn kết', 'hoạt động nhóm', 'party'],
        'duration': 240,
        'priority': 'Thấp',
        'best_time': (14, 18)
    },
    'follow_up': {
        'keywords': ['follow up', 'theo dõi', 'kiểm tra tiến độ', 'check'],
        'duration': 30,
        'priority': 'Bình thường',
        'best_time': (9, 17)
    },
    'email': {
        'keywords': ['email', 'thư điện tử', 'gửi mail', 'phản hồi'],
        'duration': 15,
        'priority': 'Thấp',
        'best_time': (8, 18)
    },
    'research': {
        'keywords': ['nghiên cứu', 'research', 'tìm hiểu', 'khảo sát'],
        'duration': 180,
        'priority': 'Bình thường',
        'best_time': (9, 16)
    },
    'maintenance': {
        'keywords': ['bảo trì', 'maintenance', 'sửa chữa', 'cập nhật'],
        'duration': 120,
        'priority': 'Bình thường',
        'best_time': (8, 12)
    },
    'lunch': {
        'keywords': ['ăn trưa', 'lunch', 'cơm trưa', 'business lunch'],
        'duration': 90,
        'priority': 'Bình thường',
        'best_time': (11, 14)
    },
    'urgent': {
        'keywords': ['khẩn cấp', 'urgent', 'gấp', 'emergency', 'asap'],
        'duration': 60,
        'priority': 'Rất cao',
        'best_time': (8, 18)
    },
    'football': {
        'keywords': ['đá bóng', 'football', 'soccer', 'bóng đá', 'sân cỏ'],
        'duration': 120,
        'priority': 'Thấp',
        'best_time': (17, 20)
    },
    'badminton': {
        'keywords': ['cầu lông', 'badminton', 'đánh cầu', 'vợt cầu'],
        'duration': 90,
        'priority': 'Thấp',
        'best_time': (17, 21)
    },
    'tennis': {
        'keywords': ['tennis', 'quần vợt', 'đánh tennis'],
        'duration': 90,
        'priority': 'Thấp',
        'best_time': (6, 9)
    },
    'swimming': {
        'keywords': ['bơi lội', 'swimming', 'bể bơi', 'bơi'],
        'duration': 60,
        'priority': 'Thấp',
        'best_time': (6, 8)
    },
    'gym': {
        'keywords': ['tập gym', 'gym', 'fitness', 'tập thể hình', 'workout'],
        'duration': 75,
        'priority': 'Thấp',
        'best_time': (6, 8)
    },
    'running': {
        'keywords': ['chạy bộ', 'running', 'jogging', 'marathon'],
        'duration': 45,
        'priority': 'Thấp',
        'best_time': (6, 7)
    },
    'yoga': {
        'keywords': ['yoga', 'thiền', 'meditation', 'tập yoga'],
        'duration': 60,
        'priority': 'Thấp',
        'best_time': (6, 8)
    },
    'social_meetup': {
        'keywords': ['gặp gỡ', 'hẹn hò', 'meetup', 'tụ tập', 'gặp bạn'],
        'duration': 120,
        'priority': 'Thấp',
        'best_time': (18, 22)
    },
    'coffee': {
        'keywords': ['cà phê', 'coffee', 'uống cà phê', 'cafe'],
        'duration': 60,
        'priority': 'Thấp',
        'best_time': (9, 11)
    },
    'dinner': {
        'keywords': ['ăn tối', 'dinner', 'cơm tối', 'tiệc tối'],
        'duration': 90,
        'priority': 'Thấp',
        'best_time': (18, 21)
    },
    'basketball': {
        'keywords': ['bóng rổ', 'basketball', 'đánh bóng rổ'],
        'duration': 90,
        'priority': 'Thấp',
        'best_time': (17, 20)
    },
    'cycling': {
        'keywords': ['đạp xe', 'cycling', 'xe đạp', 'bike'],
        'duration': 90,
        'priority': 'Thấp',
        'best_time': (6, 8)
    },
    'entertainment': {
        'keywords': ['giải trí', 'xem phim', 'movie', 'entertainment', 'vui chơi'],
        'duration': 150,
        'priority': 'Thấp',
        'best_time': (19, 22)
    }
}