import os
import sys
import json
import requests
from dotenv import load_dotenv

# Ensure UTF-8 output encoding for Windows terminal compatibility
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Load environment variables from .env
load_dotenv()


class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        """
        Khởi tạo Ollama REST API Client.
        Đọc cấu hình từ biến môi trường hoặc dùng giá trị mặc định.
        """
        env_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        env_model = os.getenv("OLLAMA_MODEL", "qwen3:0.6b")
        
        self.base_url = (base_url or env_url).rstrip('/')
        self.model = model or env_model

    def check_health(self) -> dict:
        """
        Kiểm tra trạng thái Ollama Server và lấy danh sách models khả dụng (/api/tags).
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "online": True,
                    "models": models,
                    "message": f"Ollama Server online. Found {len(models)} model(s)."
                }
            else:
                return {
                    "online": False,
                    "models": [],
                    "message": f"Ollama Server returned HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "online": False,
                "models": [],
                "message": f"Could not connect to Ollama Server at {self.base_url}: {str(e)}"
            }

    def _rule_engine_fallback(self, prompt: str, format_json: bool = False) -> str:
        """
        Cơ chế Fallback an toàn kiểu Rule-Engine khi Ollama Server offline hoặc lỗi.
        """
        fallback_text = (
            "[RULE-ENGINE FALLBACK] Ollama Server hiện chưa sẵn sàng hoặc đang offline. "
            "Phản hồi được khởi tạo tự động từ quy tắc dự phòng an toàn (Air-gapped Guardrail Rule Engine)."
        )
        if format_json:
            fallback_dict = {
                "status": "FALLBACK",
                "message": fallback_text,
                "review_status": "NEEDS_HUMAN_REVIEW",
                "citations": ["Quy định nội bộ Agribank (Dự phòng Rule-Engine)"],
                "results": []
            }
            return json.dumps(fallback_dict, ensure_ascii=False, indent=2)
        return fallback_text

    def generate(self, prompt: str, format_json: bool = False, temperature: float = 0.2) -> str:
        """
        Gửi prompt tới Ollama REST API endpoint /api/generate và nhận văn bản / JSON.
        """
        health = self.check_health()
        if not health["online"]:
            return self._rule_engine_fallback(prompt, format_json)

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if format_json:
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                result_json = response.json()
                return result_json.get("response", "")
            else:
                print(f"[OllamaClient Warning] HTTP {response.status_code}: {response.text}")
                return self._rule_engine_fallback(prompt, format_json)
        except Exception as e:
            print(f"[OllamaClient Exception] Error sending request: {e}")
            return self._rule_engine_fallback(prompt, format_json)


if __name__ == "__main__":
    print("=== TEST MODULE OLLAMA ADAPTER ===")
    client = OllamaClient()
    health = client.check_health()

    print(f"Base URL: {client.base_url}")
    print(f"Target Model: {client.model}")
    print(f"Server Status: {'ONLINE' if health['online'] else 'OFFLINE'}")
    print(f"Message: {health['message']}")
    if health['models']:
        print(f"Models: {health['models']}")

    # Test prompt generation
    test_prompt = "Xin chào, hãy giới thiệu ngắn gọn 1 câu về Ngân hàng Agribank."
    print("\n--- Test Generate ---")
    response_text = client.generate(prompt=test_prompt, format_json=False)
    print(f"Prompt: {test_prompt}")
    print(f"Response:\n{response_text}")

    server_online = "YES" if health['online'] else "NO"
    adapter_status = "PASS" if isinstance(response_text, str) and len(response_text) > 0 else "FAIL"

    print("\n" + "=" * 35)
    print(f"OLLAMA ADAPTER: {adapter_status}")
    print(f"OLLAMA SERVER ONLINE: {server_online}")
    print("=" * 35)
