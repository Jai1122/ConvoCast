"""Content processing pipeline for Q&A conversion."""

import re
from typing import Dict, List

from rich.console import Console

from ..llm.vllm_client import VLLMClient
from ..types import ConfluencePage, PageGroup, PodcastEpisode, QAContent

console = Console()


class ContentProcessor:
    """Processes Confluence pages into podcast episodes."""

    def __init__(self, llm_client: VLLMClient) -> None:
        """Initialize content processor with LLM client."""
        self.llm_client = llm_client

    def process_pages(self, pages: List[ConfluencePage]) -> List[PodcastEpisode]:
        """Process multiple pages into podcast episodes using holistic approach."""
        console.print("🔄 Analyzing pages for content grouping...")

        # Filter out pages with insufficient content
        valid_pages = [page for page in pages if self._has_sufficient_content(page)]
        console.print(
            f"📊 Found {len(valid_pages)} pages with sufficient content out of {len(pages)} total"
        )

        if not valid_pages:
            console.print("[red]❌ No pages with sufficient content found[/red]")
            return []

        # Group pages by similarity/topic
        page_groups = self._group_pages_by_topic(valid_pages)
        console.print(f"📂 Created {len(page_groups)} content groups")

        episodes: List[PodcastEpisode] = []

        for group in page_groups:
            console.print(
                f"🔄 Processing group: [bold]{group.name}[/bold] ({len(group.pages)} pages)"
            )

            try:
                qa_content = self._convert_group_to_qa(group)
                if qa_content:
                    episodes.append(
                        PodcastEpisode(
                            title=group.name,
                            content=qa_content,
                            source_pages=[page.title for page in group.pages],
                        )
                    )
                    console.print(f"✅ Generated {len(qa_content)} Q&A items for group")
                else:
                    console.print(f"⚠️  Skipped group - no Q&A content generated")
            except Exception as e:
                console.print(f"[red]❌ Error processing group {group.name}: {e}[/red]")

        return episodes

    def _has_sufficient_content(self, page: ConfluencePage) -> bool:
        """Check if page has sufficient content for processing."""
        return bool(page.content.strip()) and len(page.content) >= 20

    def _group_pages_by_topic(self, pages: List[ConfluencePage]) -> List[PageGroup]:
        """Group pages by topic using keyword similarity and hierarchy."""
        if len(pages) <= 3:
            # If we have few pages, create one comprehensive group
            return [
                PageGroup(
                    name="Comprehensive Onboarding Guide",
                    pages=pages,
                    combined_content=self._combine_page_contents(pages),
                )
            ]

        groups: List[PageGroup] = []

        # Simple grouping by common keywords in titles
        topic_keywords = self._extract_topic_keywords(pages)
        grouped_pages: set[str] = set()

        for keyword in topic_keywords:
            related_pages = [
                page
                for page in pages
                if page.id not in grouped_pages
                and (
                    keyword.lower() in page.title.lower()
                    or keyword.lower() in page.content.lower()[:500]
                )
            ]

            if len(related_pages) >= 2:
                group_name = f"{keyword.title()} Documentation"
                groups.append(
                    PageGroup(
                        name=group_name,
                        pages=related_pages,
                        combined_content=self._combine_page_contents(related_pages),
                    )
                )
                grouped_pages.update(page.id for page in related_pages)

        # Add remaining ungrouped pages to a general group
        ungrouped_pages = [page for page in pages if page.id not in grouped_pages]
        if ungrouped_pages:
            groups.append(
                PageGroup(
                    name="General Documentation",
                    pages=ungrouped_pages,
                    combined_content=self._combine_page_contents(ungrouped_pages),
                )
            )

        return groups

    def _extract_topic_keywords(self, pages: List[ConfluencePage]) -> List[str]:
        """Extract common topic keywords from page titles and content."""
        all_titles = " ".join(page.title for page in pages).lower()

        # Common technical keywords that might indicate topics
        potential_keywords = [
            "api",
            "setup",
            "config",
            "install",
            "deploy",
            "test",
            "guide",
            "tutorial",
            "architecture",
            "design",
            "development",
            "security",
            "authentication",
            "database",
            "frontend",
            "backend",
            "service",
        ]

        found_keywords = [
            keyword for keyword in potential_keywords if keyword in all_titles
        ]

        # Also extract words that appear in multiple titles
        title_words: dict[str, int] = {}
        for page in pages:
            words = [
                word.lower().strip() for word in page.title.split() if len(word) > 3
            ]
            for word in words:
                title_words[word] = title_words.get(word, 0) + 1

        frequent_words = [word for word, count in title_words.items() if count >= 2]

        return list(set(found_keywords + frequent_words))[:5]  # Limit to 5 topics

    def _combine_page_contents(self, pages: List[ConfluencePage]) -> str:
        """Combine content from multiple pages into a cohesive text."""
        combined = ""
        for page in pages:
            combined += f"\n\n=== {page.title} ===\n{page.content}"
        return combined.strip()

    def _convert_group_to_qa(self, group: PageGroup) -> List[QAContent]:
        """Convert a group of pages to holistic Q&A format."""
        try:
            qa_response = self.llm_client.convert_group_to_qa(
                group.combined_content, group.name, [page.title for page in group.pages]
            )
            return self._parse_qa_response(qa_response)
        except Exception as e:
            console.print(
                f"[red]Failed to convert group '{group.name}' to Q&A: {e}[/red]"
            )
            return []

    def _parse_qa_response(self, response: str) -> List[QAContent]:
        """Parse LLM response into structured Q&A content."""
        qa_items: List[QAContent] = []
        lines = [line.strip() for line in response.split("\n") if line.strip()]

        current_q = ""
        current_a = ""
        is_answer = False

        for line in lines:
            if line.startswith("Q:"):
                # Save previous Q&A if complete
                if current_q and current_a:
                    qa_items.append(
                        QAContent(
                            question=re.sub(r"^Q:\s*", "", current_q).strip(),
                            answer=re.sub(r"^A:\s*", "", current_a).strip(),
                        )
                    )

                current_q = line
                current_a = ""
                is_answer = False

            elif line.startswith("A:"):
                current_a = line
                is_answer = True

            elif line and is_answer:
                current_a += " " + line

            elif line and not is_answer and current_q:
                current_q += " " + line

        # Don't forget the last Q&A pair
        if current_q and current_a:
            qa_items.append(
                QAContent(
                    question=re.sub(r"^Q:\s*", "", current_q).strip(),
                    answer=re.sub(r"^A:\s*", "", current_a).strip(),
                )
            )

        # Filter out empty Q&A items
        return [qa for qa in qa_items if qa.question and qa.answer]

    def format_for_podcast(self, episode: PodcastEpisode) -> str:
        """Format episode content for podcast script."""
        intro = f"Welcome to the {episode.title} onboarding episode."

        if episode.source_pages:
            intro += f" This episode covers information from the following documentation pages: {', '.join(episode.source_pages)}."

        intro += " Let's dive into some key questions about this topic.\n\n"

        qa_text = ""
        for i, qa in enumerate(episode.content, 1):
            qa_text += f"Question {i}: {qa.question}\n\nAnswer: {qa.answer}\n\n"

        outro = f"That concludes our overview of {episode.title}. These insights should help you understand this part of our project better. Thank you for listening!"

        return intro + qa_text + outro
