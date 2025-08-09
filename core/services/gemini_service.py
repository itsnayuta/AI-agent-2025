# Gemini AI Service
import google.generativeai as genai
import threading
import queue
from typing import Any
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
        """Thread-safe Gemini API call"""
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
        """Generate content with timeout handling"""
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
        """Extract function call from Gemini response"""
        try:
            if hasattr(response.candidates[0].content.parts[0], 'function_call'):
                return response.candidates[0].content.parts[0].function_call
            return None
        except (IndexError, AttributeError):
            return None
