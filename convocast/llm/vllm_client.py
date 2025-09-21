"""VLLM client for secure LLM inference."""

from typing import Dict, List, Any
import requests
from ..types import VLLMConfig


class VLLMClient:
    """Client for interacting with VLLM API."""

    def __init__(self, config: VLLMConfig) -> None:
        """Initialize VLLM client with configuration."""
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        })

    def generate_completion(self, prompt: str, system_prompt: str = None) -> str:
        """Generate completion from VLLM API."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }

        try:
            response = self.session.post(
                f"{self.config.api_url}/v1/chat/completions",
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            data = response.json()

            if not data.get("choices") or len(data["choices"]) == 0:
                raise RuntimeError("No response generated from VLLM")

            return data["choices"][0]["message"]["content"].strip()

        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                error_detail = e.response.json().get('error', str(e)) if e.response.headers.get('content-type', '').startswith('application/json') else str(e)
                raise RuntimeError(f"VLLM API error: {e.response.status_code} - {error_detail}")
            raise RuntimeError(f"Failed to generate completion: {e}")

    def convert_to_qa(self, content: str, page_title: str) -> str:
        """Convert content to Q&A format for onboarding."""
        system_prompt = """You are an expert at creating onboarding content for new team members. Your task is to convert technical documentation into a conversational Q&A format that helps new employees understand the project better.

Guidelines:
- Create 3-5 questions and answers per content section
- Focus on what new team members would want to know
- Make answers clear and practical
- Include context about business requirements, system design, and project goals
- Use a friendly, conversational tone suitable for a podcast"""

        user_prompt = f"""Convert the following Confluence page content into a Q&A format for new team member onboarding:

Page Title: {page_title}

Content:
{content}

Please create relevant questions that a new team member would ask about this content, and provide clear, helpful answers. Format as:

Q: [Question]
A: [Answer]

Focus on practical information that helps with onboarding and project understanding."""

        return self.generate_completion(user_prompt, system_prompt)