## Hướng Dẫn Cài đặt
1. Clone dự án:
   ```
   git clone https://github.com/itsnayuta/AI-agent-2025.git
   cd AI-agent-2025
   ```
2. Tạo và kích hoạt môi trường ảo (venv):
   ```
   python -m venv .venv
   .venv\Scripts\activate 
   ```
3. Cài đặt package:
   ```
   pip install -r requirements.txt
   ```
4. Thiết lập API key:
   - Đổi tên file `.env.example` thành `.env`, hoàn thiện các nội dung yêu cầu:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

## Sử dụng
Chạy ứng dụng:
```
python main.py
```
Nhập yêu cầu bằng tiếng Việt, ví dụ:
- "Tôi muốn đặt lịch họp quan trọng vào chiều mai"
- "Gửi email cho tôi nếu có thay đổi lịch"

Để thoát, nhập `exit`.

## Cấu trúc dự án
- `main.py`: Khởi động agent, xử lý function calling với Gemini
- `core/agents.py`: Logic AI tư vấn lập lịch
- `core/tasks.py`: Thực hiện lập lịch, gửi email
- `api/routes.py`: (dự phòng cho API mở rộng)
- `tools/`: (dự phòng cho các tiện ích mở rộng)

## Ghi chú
- Để mở rộng, bạn có thể tích hợp Google Calendar, gửi email thực tế qua SMTP hoặc dịch vụ thứ 3.
- Đảm bảo bảo mật API key, không commit file `.env` lên repo công khai.
