"""VLLM client for secure LLM inference."""

from typing import Any, Dict, List, Optional

import requests

from ..types import VLLMConfig


class VLLMClient:
    """Client for interacting with VLLM API."""

    def __init__(self, config: VLLMConfig) -> None:
        """Initialize VLLM client with configuration."""
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            }
        )

    def generate_completion(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """Generate completion from VLLM API."""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        try:
            response = self.session.post(
                f"{self.config.api_url}/v1/chat/completions", json=payload, timeout=60
            )
            response.raise_for_status()

            data = response.json()

            if not data.get("choices") or len(data["choices"]) == 0:
                raise RuntimeError("No response generated from VLLM")

            content = data["choices"][0]["message"]["content"]
            return str(content).strip()

        except requests.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                error_detail = (
                    e.response.json().get("error", str(e))
                    if e.response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else str(e)
                )
                raise RuntimeError(
                    f"VLLM API error: {e.response.status_code} - {error_detail}"
                )
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

    def convert_group_to_qa(
        self, combined_content: str, group_name: str, page_titles: List[str]
    ) -> str:
        """Convert a group of related pages to holistic Q&A format for onboarding."""
        print(f"🔍 VLLM: Starting conversion for group '{group_name}'")
        print(f"📊 VLLM: Content length: {len(combined_content)} characters")
        print(f"📄 VLLM: Page titles: {page_titles}")

        system_prompt = """You are an expert at creating comprehensive onboarding content for new team members. Your task is to convert multiple related technical documents into a holistic Q&A format that helps new employees understand the project better.

Guidelines:
- Create 5-8 comprehensive questions and answers that span across all the provided content
- Connect information from different pages to provide holistic understanding
- Focus on what new team members would want to know about this topic area
- Make answers clear, practical, and interconnected
- Include context about business requirements, system design, and project goals
- Use a friendly, conversational tone suitable for a podcast
- Avoid duplicating similar information - synthesize and combine related concepts
- ALWAYS format your response as Q: [Question] followed by A: [Answer]
- Each question and answer should be on separate lines"""

        user_prompt = f"""Convert the following group of related Confluence pages into a holistic Q&A format for new team member onboarding:

Topic Area: {group_name}

Source Pages: {', '.join(page_titles)}

Combined Content:
{combined_content}

Please create comprehensive questions that a new team member would ask about this topic area, synthesizing information from all the provided pages. Provide clear, helpful answers that connect concepts across the different pages.

IMPORTANT: Format your response exactly as:

Q: [Question]
A: [Answer]

Q: [Question]
A: [Answer]

Focus on providing a complete understanding of this topic area for onboarding purposes."""

        try:
            print(f"🚀 VLLM: Sending request to API...")
            response = self.generate_completion(user_prompt, system_prompt)
            print(f"✅ VLLM: Received response ({len(response)} chars)")
            print(f"🔍 VLLM: Response preview: {response[:300]}...")
            return response
        except Exception as e:
            print(f"❌ VLLM: Error during API call: {e}")
            raise
