# Dịch vụ Gemini AI
import google.generativeai as genai
import threading
import queue
from typing import Any
from google.generativeai.types import GenerateContentResponse
from core.config import Config
from core.exceptions import GeminiAPIError


class GeminiService:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise GeminiAPIError('Vui lòng thiết lập biến môi trường GEMINI_API_KEY')

        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=100
        )

    def _call_gemini_api(self, q: queue.Queue, system_prompt: str, functions: list, generation_config):
        """Gọi API Gemini an toàn với thread"""
        try:
            response = self.model.generate_content(
                system_prompt,
                tools=[{"function_declarations": functions}],
                tool_config={"function_calling_config": {"mode": "ANY"}},
                generation_config=generation_config
            )
            q.put(response)
        except Exception as e:
            q.put(e)
    
    def generate_with_timeout(self, system_prompt: str, functions: list) -> Any:
        """Tạo nội dung với xử lý timeout"""
        q = queue.Queue()
        thread = threading.Thread(
            target=self._call_gemini_api, 
            args=(q, system_prompt, functions, self.generation_config)
        )
        
        thread.start()
        thread.join(timeout=Config.GEMINI_TIMEOUT)
        
        if thread.is_alive():
            raise GeminiAPIError("Gemini API quá chậm hoặc không phản hồi")
        
        response = q.get()
        if isinstance(response, Exception):
            raise GeminiAPIError(f"Lỗi Gemini API: {response}")
        
        return response
    
    def extract_function_call(self, response):
        """Trích xuất function call từ phản hồi Gemini"""
        try:
            if hasattr(response.candidates[0].content.parts[0], 'function_call'):
                return response.candidates[0].content.parts[0].function_call
            return None
        except (IndexError, AttributeError):
            return None

    def get_ai_response(self, prompt: str) -> GenerateContentResponse:
        """
        Receives a user prompt, processes it with the AIAgent, and returns the raw response.
        """
        response = self.model.generate_content(prompt)
        return response

    def format_response(self, response: GenerateContentResponse | str | dict) -> str:
        """
        Formats various response types from the agent into a user-friendly string.
        """
        # 1. Handle raw Gemini SDK response objects
        if isinstance(response, GenerateContentResponse):
            try:
                # Thuộc tính .text là cách an toàn và trực tiếp nhất để lấy text
                return response.text
            except AttributeError:
                return "Lỗi: Không thể trích xuất nội dung từ phản hồi của AI."

        # 2. Handle pre-formatted strings
        if isinstance(response, str):
            return response

        # 4. Fallback for any other unexpected data types
        return "Không thể định dạng loại phản hồi không xác định."

    async def process_message(self, message: str) -> str:
        """
        Xử lý tin nhắn bằng Gemini AI cho tư vấn lịch trình
        """
        try:
            response = self.model.generate_content(
                message,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Tăng creativity cho tư vấn
                    max_output_tokens=500  # Tăng độ dài cho phản hồi chi tiết
                )
            )
            return response.text
        except Exception as e:
            raise GeminiAPIError(f"Lỗi khi xử lý tin nhắn: {str(e)}")