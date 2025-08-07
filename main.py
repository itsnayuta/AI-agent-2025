from core.ai_agent import AIAgent
from core.exceptions import GeminiAPIError


def main():
    print("=== AI Agent Lập lịch ===")
    
    try:
        agent = AIAgent()
    except GeminiAPIError as e:
        print(f"Lỗi khởi tạo: {e}")
        return
    
    while True:
        user_input = input("\nNhập yêu cầu của bạn (hoặc 'exit' hoặc 'quit' để thoát): ")
        if user_input.lower() in ["exit", "quit", "thoát"]:
            print("Tạm biệt!")
            break
        
        try:
            response = agent.process_user_input(user_input)
        except KeyboardInterrupt:
            print("\nĐã hủy yêu cầu.")
        except Exception as e:
            print(f"Lỗi không mong muốn: {e}")


if __name__ == "__main__":
    main()
