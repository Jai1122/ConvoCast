"""Content processing pipeline for Q&A conversion."""

import re
from typing import List
from rich.console import Console

from ..types import ConfluencePage, QAContent, PodcastEpisode
from ..llm.vllm_client import VLLMClient

console = Console()


class ContentProcessor:
    """Processes Confluence pages into podcast episodes."""

    def __init__(self, llm_client: VLLMClient) -> None:
        """Initialize content processor with LLM client."""
        self.llm_client = llm_client

    def process_pages(self, pages: List[ConfluencePage]) -> List[PodcastEpisode]:
        """Process multiple pages into podcast episodes."""
        episodes: List[PodcastEpisode] = []

        for page in pages:
            console.print(f"🔄 Processing: [bold]{page.title}[/bold]")

            try:
                qa_content = self._convert_page_to_qa(page)
                if qa_content:
                    episodes.append(PodcastEpisode(
                        title=page.title,
                        content=qa_content
                    ))
                    console.print(f"✅ Generated {len(qa_content)} Q&A items")
                else:
                    console.print(f"⚠️  Skipped - insufficient content")
            except Exception as e:
                console.print(f"[red]❌ Error processing page {page.title}: {e}[/red]")

        return episodes

    def _convert_page_to_qa(self, page: ConfluencePage) -> List[QAContent]:
        """Convert a single page to Q&A format."""
        if not page.content.strip() or len(page.content) < 100:
            console.print(f"Skipping page '{page.title}' - insufficient content")
            return []

        try:
            qa_response = self.llm_client.convert_to_qa(page.content, page.title)
            return self._parse_qa_response(qa_response)
        except Exception as e:
            console.print(f"[red]Failed to convert page '{page.title}' to Q&A: {e}[/red]")
            return []

    def _parse_qa_response(self, response: str) -> List[QAContent]:
        """Parse LLM response into structured Q&A content."""
        qa_items: List[QAContent] = []
        lines = [line.strip() for line in response.split('\n') if line.strip()]

        current_q = ""
        current_a = ""
        is_answer = False

        for line in lines:
            if line.startswith('Q:'):
                # Save previous Q&A if complete
                if current_q and current_a:
                    qa_items.append(QAContent(
                        question=re.sub(r'^Q:\s*', '', current_q).strip(),
                        answer=re.sub(r'^A:\s*', '', current_a).strip()
                    ))

                current_q = line
                current_a = ""
                is_answer = False

            elif line.startswith('A:'):
                current_a = line
                is_answer = True

            elif line and is_answer:
                current_a += " " + line

            elif line and not is_answer and current_q:
                current_q += " " + line

        # Don't forget the last Q&A pair
        if current_q and current_a:
            qa_items.append(QAContent(
                question=re.sub(r'^Q:\s*', '', current_q).strip(),
                answer=re.sub(r'^A:\s*', '', current_a).strip()
            ))

        # Filter out empty Q&A items
        return [qa for qa in qa_items if qa.question and qa.answer]

    def format_for_podcast(self, episode: PodcastEpisode) -> str:
        """Format episode content for podcast script."""
        intro = f"Welcome to the {episode.title} onboarding episode. Let's dive into some key questions about this topic.\n\n"

        qa_text = ""
        for i, qa in enumerate(episode.content, 1):
            qa_text += f"Question {i}: {qa.question}\n\nAnswer: {qa.answer}\n\n"

        outro = f"That concludes our overview of {episode.title}. These insights should help you understand this part of our project better. Thank you for listening!"

        return intro + qa_text + outro