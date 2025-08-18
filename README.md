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

### Bước 7: Thiết lập Email Notification (SMTP)
> 🔔 Cấu hình để nhận thông báo email 15 phút trước mỗi lịch hẹn

#### 7.1. Tạo Gmail App Password
1. **Bật 2-Factor Authentication** cho Gmail:
   - Vào [Google Account Settings](https://myaccount.google.com/)
   - Chọn **Security** → **2-Step Verification**
   - Bật **2-Step Verification** nếu chưa có

2. **Tạo App Password**:
   - Vào **Security** → **App passwords**
   - Chọn **Select app** → **Mail**
   - Chọn **Select device** → **Other (custom name)**
   - Nhập tên: `AI Agent Schedule`
   - Click **Generate**
   - **Sao chép** password 16 ký tự (ví dụ: `abcd efgh ijkl mnop`)

#### 7.2. Cập nhật file .env
Thêm cấu hình SMTP vào file `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here

# SMTP Configuration for Gmail
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_digit_app_password
```

**Lưu ý quan trọng:**
- `SMTP_USER`: Email Gmail của bạn
- `SMTP_PASSWORD`: App password 16 ký tự (KHÔNG phải password Gmail thường)
- Email nhận thông báo sẽ được setup qua API sau khi khởi động ứng dụng

#### 7.3. Test Email Configuration
Sau khi khởi động ứng dụng, bạn có thể test email:
1. Vào http://127.0.0.1:8000/docs
2. Sử dụng endpoint `POST /schedules/test-email`
3. Nhập email muốn test: `{"email": "your_test_email@gmail.com"}`

### Bước 8: Tạo thư mục database
```bash
mkdir database
```

## 🚀 Cách Sử Dụng

### Khởi chạy ứng dụng
```bash
uvicorn main:app --reload
```
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
📁 Agent-Schedule-Management/
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
│   ├── 📁 notification/         # Email notification system
│   │   ├── 📄 NotificationManager.py # Quản lý notification
│   │   ├── 📄 NotificationScheduler.py # Background scheduler
│   │   └── 📄 NotificationCore.py # Core services
│   ├── 📁 routers/              # FastAPI routers
│   │   └── 📄 schedule_router.py # API endpoints
│   └── 📁 OAuth/                # Google credentials
│       └── 📄 credentials.json  # (Bạn tự tạo)
├── 📁 utils/                    # Utilities
│   ├── 📄 time_patterns.py     # Pattern thời gian
│   └── 📄 task_categories.py   # Phân loại công việc
├── 📁 database/                 # SQLite database
├── 📁 test/                     # Test scripts
├── 📄 .env                      # Biến môi trường (bạn tự tạo)
├── 📄 SETUP_EMAIL.md           # Hướng dẫn setup email
└── 📄 requirements.txt          # Dependencies
```



