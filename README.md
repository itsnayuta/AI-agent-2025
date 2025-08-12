## 🛠️ Hướng Dẫn Cài Đặt Chi Tiết

### Bước 1: Clone dự án
```bash
git clone https://github.com/itsnayuta/AI-agent-2025.git
cd AI-agent-2025
```

### Bước 2: Tạo môi trường ảo
```bash
# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
.venv\Scripts\activate

# Kích hoạt (macOS/Linux)
source .venv/bin/activate
```

### Bước 3: Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Bước 4: Thiết lập biến môi trường
1. Sao chép file `.env.example` thành `.env`:
   ```bash
   copy .env.example .env
   ```

2. Chỉnh sửa file `.env` với thông tin của bạn:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

### Bước 5: Lấy Gemini API Key
1. Truy cập [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Đăng nhập với tài khoản Google
3. Nhấn **"Create API Key"**
4. Sao chép API key và dán vào file `.env`

### Bước 6: Thiết lập Google Calendar
> ⚠️ Tạo file theo đường dẫn: `core/OAuth/credentials.json`

#### 6.1. Tạo Google Cloud Project
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới hoặc chọn project có sẵn
3. Bật Google Calendar API:
   - Vào **APIs & Services** > **Library**
   - Tìm "Google Calendar API" và nhấn **Enable**

#### 6.2. Tạo OAuth 2.0 Credentials
1. Vào **APIs & Services** > **Credentials**
2. Nhấn **+ CREATE CREDENTIALS** > **OAuth client ID**
3. Chọn **Application type**: Desktop application
4. Đặt tên (ví dụ: "AI Agent Schedule")
5. Nhấn **Create**

#### 6.3. Tải và đặt credentials
1. Nhấn biểu tượng **Download** bên cạnh credential vừa tạo
2. Tạo thư mục `core/OAuth/` (nếu chưa có):
   ```bash
   mkdir -p core/OAuth
   ```
3. Đổi tên file tải về thành `credentials.json`
4. Di chuyển vào `core/OAuth/credentials.json`

#### 6.4. Thiết lập OAuth Consent Screen
1. Vào **APIs & Services** > **OAuth consent screen**
2. Chọn **External** > **Create**
3. Điền thông tin cơ bản:
   - **App name**: AI Agent Schedule
   - **User support email**: email của bạn
   - **Developer contact**: email của bạn
4. Thêm **Scopes**: `../auth/calendar`
5. Vào **Audience** để publish app 
6. Thêm **Test users**: email tài khoản Google bạn muốn test

### Bước 7: Tạo thư mục database
```bash
mkdir database
```

## 🚀 Cách Sử Dụng

### Khởi chạy ứng dụng
```bash
uvicorn main:app --reload
```

Khi máy chủ đang chạy, bạn có thể truy cập tài liệu API tương tác tại http://localhost:8000/docs để kiểm tra tất cả các endpoint.

### Các lệnh mẫu bằng tiếng Việt

#### Xem lịch hiện tại
```
xem lịch hiện tại
danh sách lịch
```

#### Thêm lịch mới
```
thêm lịch họp vào 9h sáng mai
đặt lịch khám răng lúc 2h chiều thứ 7
tạo lịch học tiếng anh 7h tối thứ 3 tuần sau
```

#### Tư vấn thời gian
```
khi nào phù hợp để họp với khách hàng?
thời gian tốt nhất để phỏng vấn là khi nào?
```

#### Thoát chương trình
```
exit
quit
thoát
```

## 📁 Cấu Trúc Dự Án

```
📁 AI-agent-2025/
├── 📄 main.py                    # Entry point chính
├── 📁 core/                      # Core modules
│   ├── 📄 config.py             # Cấu hình tập trung
│   ├── 📄 exceptions.py         # Custom exceptions
│   ├── 📄 ai_agent.py          # AI Agent chính
│   ├── 📁 services/             # Business logic
│   │   ├── 📄 gemini_service.py # Xử lý Gemini API
│   │   ├── 📄 ScheduleAdvisor.py # Tư vấn lập lịch
│   │   └── 📄 ExecuteSchedule.py # Thực thi lịch
│   ├── 📁 handlers/             # Request handlers
│   │   └── 📄 function_handler.py # Xử lý function calls
│   ├── 📁 models/               # Data models
│   │   └── 📄 function_definitions.py # AI function schemas
│   └── 📁 OAuth/                # Google credentials
│       └── 📄 credentials.json  # (Bạn tự tạo)
├── 📁 utils/                    # Utilities
│   ├── 📄 time_patterns.py     # Pattern thời gian
│   └── 📄 task_categories.py   # Phân loại công việc
├── 📁 database/                 # SQLite database
├── 📁 test/                     # Test scripts
└── 📄 requirements.txt          # Dependencies
```

## 🔧 Xử Lý Sự Cố

### Lỗi Gemini API
```
❌ Lỗi Gemini API: 429 You exceeded your current quota
```
**Giải pháp**: Đợi 24h hoặc nâng cấp gói Gemini API

### Lỗi Google Calendar
```
🔶 Đồng bộ Google Calendar thất bại: access_denied
```
**Giải pháp**: 
1. Kiểm tra file `credentials.json` có đúng vị trí
2. Thêm email vào Test users trong OAuth consent screen
3. Xóa file `token.pickle` và đăng nhập lại

### Lỗi Database
```
❌ Lỗi khi thêm lịch: Cannot operate on a closed database
```
**Giải pháp**: Khởi động lại ứng dụng

