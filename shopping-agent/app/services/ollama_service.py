
import requests

from app.config import (
    OLLAMA_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
)


class OllamaService:
    def __init__(self):
        self.chat_url = f"{OLLAMA_URL.rstrip('/')}/api/chat"

    def chat(self, messages: list[dict]) -> str:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        }

        try:
            response = requests.post(
                self.chat_url,
                json=payload,
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Could not connect to Ollama: {exc}"
            ) from exc
        except (KeyError, ValueError) as exc:
            raise RuntimeError(
                "Ollama returned an invalid response"
            ) from exc
