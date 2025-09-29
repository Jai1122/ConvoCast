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

        system_prompt = """You are an expert at creating comprehensive onboarding content that will be converted into engaging podcast conversations. Your Q&A content needs to be rich, detailed, and conversation-ready.

=== CONTENT CREATION STRATEGY ===

QUESTION DEVELOPMENT:
- Create 6-10 comprehensive questions that new team members would naturally ask
- Progress from basic understanding to practical application
- Include "why" and "how" questions, not just "what"
- Frame questions as if a curious colleague is asking
- Examples: "Why did the team choose this approach?", "How does this fit into the bigger picture?"

ANSWER RICHNESS:
- Provide detailed answers with context and reasoning
- Include specific examples from the actual content
- Explain the "why" behind technical decisions
- Add background information that makes concepts more understandable
- Mention real-world implications and use cases
- Connect concepts across different sections

CONVERSATION READINESS:
- Write answers that contain natural talking points and examples
- Include analogies or comparisons that could spark discussion
- Add context that could lead to follow-up questions
- Provide enough detail for meaningful conversation expansion
- Think: "What would make this interesting to discuss?"

=== TECHNICAL QUALITY ===
- Synthesize information across all provided pages
- Avoid repetition while ensuring comprehensive coverage
- Maintain technical accuracy while being accessible
- Connect concepts to broader understanding
- Format: Q: [Question] followed by A: [Detailed Answer]"""

        user_prompt = f"""Create rich, conversation-ready Q&A content for "{group_name}" that will become an engaging podcast discussion.

=== SOURCE MATERIAL ===
Topic Area: {group_name}
Source Pages: {', '.join(page_titles)}

Content:
{combined_content}

=== TASK REQUIREMENTS ===

Create 6-10 comprehensive Q&A pairs that:

🎯 **QUESTION STRATEGY**:
1. Start with foundational understanding
2. Progress to practical applications
3. Include "why" and "how" questions
4. Ask about connections and implications
5. Frame from a new team member's perspective

💡 **EXAMPLE QUESTION TYPES**:
- "What is [concept] and why is it important to our system?"
- "How does this fit into the bigger picture of our architecture?"
- "What are the main benefits/challenges with this approach?"
- "When would a new developer typically encounter this?"
- "What should someone know before they start working with this?"

📝 **ANSWER REQUIREMENTS**:
- 3-5 sentences minimum per answer
- Include specific examples from the source material
- Explain reasoning and context behind decisions
- Connect to related concepts and broader implications
- Add details that could spark interesting discussion
- Use conversational language that feels natural to speak

🔧 **FORMAT**:
Q: [Compelling question that a curious colleague would ask]
A: [Rich, detailed answer with context, examples, and connections]

Focus on creating content that will naturally lead to an engaging, informative conversation between two knowledgeable people discussing fascinating technical topics."""

        try:
            print(f"🚀 VLLM: Sending request to API...")
            response = self.generate_completion(user_prompt, system_prompt)
            print(f"✅ VLLM: Received response ({len(response)} chars)")
            print(f"🔍 VLLM: Response preview: {response[:300]}...")
            return response
        except Exception as e:
            print(f"❌ VLLM: Error during API call: {e}")
            raise

    def convert_qa_to_conversation(
        self, qa_items: List, episode_title: str, style: str = "interview"
    ) -> str:
        """Convert Q&A content into natural podcast conversation."""
        print(f"🎭 VLLM: Converting Q&A to {style} conversation")

        system_prompt = """You are an expert podcast script writer who creates incredibly natural, engaging conversations for technical onboarding. Your specialty is making complex documentation feel like an exciting conversation between knowledgeable friends.

=== CHARACTER PROFILES ===

ALEX (Curious Host - Female Voice):
- Background: Tech-savvy but always learning, asks the questions listeners are thinking
- Personality: Enthusiastic, relatable, makes connections to everyday examples
- Speaking style: Uses "Oh!" "Wait, so..." "That's fascinating!" "Hold on..."
- Role: Guides the conversation, seeks clarification, celebrates insights
- Signature phrases: "I love that!", "That makes so much sense!", "Wait, let me make sure I understand..."

SAM (Technical Expert - Male Voice):
- Background: Deep technical knowledge but excellent at explaining simply
- Personality: Patient teacher, uses analogies, builds understanding step-by-step
- Speaking style: Uses "Well, think about it this way..." "Actually..." "The key thing is..."
- Role: Explains concepts, provides context, shares expertise
- Signature phrases: "Here's the thing...", "It's actually pretty cool...", "Let me give you an example..."

=== CONVERSATION DYNAMICS ===

NATURAL FLOW PATTERNS:
1. **Hook Opening**: Start with intrigue or relatable problem
2. **Discovery Journey**: Alex asks, Sam explains, both have realizations
3. **Connection Building**: Link concepts to bigger picture
4. **Practical Application**: "So in practice..." "What this means is..."
5. **Satisfying Conclusion**: Tie everything together

ADVANCED CONVERSATION TECHNIQUES:
- **Layered Questions**: Alex asks follow-ups that dive deeper
- **Thinking Out Loud**: "Hmm, so if I understand correctly..."
- **Collaborative Building**: Both contribute to explanations
- **Emotional Reactions**: "Wow!", "Oh no way!", "That's brilliant!"
- **Real-time Processing**: "Wait, that reminds me of...", "Actually, now I'm curious about..."

=== OUTPUT REQUIREMENTS ===

FORMATTING RULES:
- "ALEX:" and "SAM:" for speakers (REQUIRED)
- [BOTH LAUGH] [PAUSE] [EXCITED] [THINKING] for audio cues
- *emphasis* for vocal stress
- "--" for natural interruptions
- "..." for natural pauses/trailing off

QUALITY STANDARDS:
- Every exchange must advance understanding or engagement
- No repetitive explanations or circular conversations
- Each segment should have emotional texture (curiosity, excitement, understanding)
- Maintain technical accuracy while being conversational
- Include specific examples and analogies from the source material

CONVERSATION LENGTH: Aim for natural pacing that thoroughly covers topics without rushing."""

        # Convert Q&A items to text format for the prompt
        qa_text = ""
        for i, qa in enumerate(qa_items, 1):
            qa_text += f"\nQ{i}: {qa.question}\nA{i}: {qa.answer}\n"

        user_prompt = f"""Transform this Q&A content into an engaging podcast conversation about "{episode_title}":

{qa_text}

=== STRICT CONVERSATION RULES ===

**SPEAKER ASSIGNMENT RULES:**
- ALEX: Always asks questions, seeks clarification, expresses curiosity
- SAM: Always provides answers, explanations, and technical knowledge
- Maintain this Q&A dynamic throughout the entire conversation

**QUESTION-ANSWER FLOW:**
1. For each Q&A pair, ALEX should ask the question (potentially rephrased naturally)
2. SAM should provide the answer with examples and context
3. ALEX can ask follow-up questions for clarity
4. SAM responds with additional details

=== EXAMPLE OF DESIRED OUTPUT QUALITY ===

ALEX: Hey everyone! Welcome to Tech Talk. I'm Alex, and today I'm here with Sam to dive into API documentation. Sam, I have to admit, when I first heard about APIs, I was completely lost. Can you start by explaining what an API actually is?

SAM: Absolutely, Alex! Think about it this way - you know when you go to a restaurant and you don't need to know how the kitchen works? You just look at the menu, place your order, and get your food?

ALEX: Sure, that makes sense...

SAM: Well, an API is like the menu and the waiter combined. It tells you what you can request from a system and how to ask for it, but you don't need to understand how the system works internally.

ALEX: Oh, that's a great analogy! So in our system specifically, what kinds of things can developers actually request through our API?

SAM: Great question! In our system, developers can access user data, product information, and transaction history. For example, if you want to get a user's profile, you'd send a GET request to our users endpoint with the user ID.

ALEX: And that would return what exactly?

SAM: It returns a JSON object with all the user's information - name, email, preferences, account status, and so on. The beautiful thing is, the developer doesn't need to know that we're pulling from three different databases behind the scenes.

=== YOUR TASK ===

Create a conversation of similar quality and naturalness. Requirements:

🎯 **STRUCTURE**:
1. **Engaging Hook** (30-45 seconds): Alex introduces topic and expresses curiosity
2. **Q&A Core Discussion** (8-12 minutes): Each original Q&A becomes a natural exchange
3. **Practical Connection** (2-3 minutes): Alex asks "how does this apply?" type questions
4. **Memorable Conclusion** (30-45 seconds): Alex summarizes key learnings

🎭 **CONVERSATION TECHNIQUES**:
- ALEX should ask ALL the questions (original + 3-5 clarifying questions)
- SAM should provide ALL the answers with examples and context
- Include 2-3 moments where Alex connects dots: "Oh, so that means..."
- Sam should provide concrete examples/analogies for every technical concept
- Add natural interruptions with "--" when Alex seeks clarification
- ALEX reactions: "That's fascinating!", "Wait, so...", "I see!", "That makes sense!"
- SAM responses: "Exactly!", "Great question!", "Think of it this way...", "Here's why..."

🎨 **AUDIO TEXTURE**:
- [EXCITED], [THINKING], [PAUSE], [BOTH LAUGH] at natural moments
- Use *emphasis* on key technical terms
- Natural trailing off with "..." when appropriate

🔧 **TECHNICAL ACCURACY**:
- Preserve all technical information from the Q&A
- Expand explanations with relevant context
- Connect topics to broader understanding

Make this sound like two friends having an exciting discovery conversation about fascinating technology!"""

        try:
            print(f"🚀 VLLM: Generating conversation script...")
            response = self.generate_completion(user_prompt, system_prompt)
            print(f"✅ VLLM: Generated conversation ({len(response)} chars)")
            print(f"🔍 VLLM: Script preview: {response[:200]}...")
            return response
        except Exception as e:
            print(f"❌ VLLM: Error generating conversation: {e}")
            raise
