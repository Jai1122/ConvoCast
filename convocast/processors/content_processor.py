"""Content processing pipeline for Q&A conversion."""

import re
from typing import Dict, List

from rich.console import Console

from ..llm.vllm_client import VLLMClient
from ..types import (
    ConfluencePage,
    ConversationSegment,
    ConversationStyle,
    PageGroup,
    PodcastEpisode,
    QAContent,
)

console = Console()


class ContentProcessor:
    """Processes Confluence pages into podcast episodes."""

    def __init__(
        self, llm_client: VLLMClient, enable_conversation: bool = False
    ) -> None:
        """Initialize content processor with LLM client."""
        self.llm_client = llm_client
        self.enable_conversation = enable_conversation

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
                    episode = PodcastEpisode(
                        title=group.name,
                        content=qa_content,
                        source_pages=[page.title for page in group.pages],
                        conversation_style=ConversationStyle.INTERVIEW,
                    )

                    # Always generate conversation segments for voice switching
                    console.print(f"🎭 Generating conversation segments (enable_conversation={self.enable_conversation})...")

                    # Generate conversational content if enabled
                    if self.enable_conversation:
                        console.print(f"🎭 Generating LLM-powered conversation for group...")
                        try:
                            dialogue_script = self._generate_conversation(
                                qa_content, group.name
                            )
                            if dialogue_script:
                                episode.dialogue_script = dialogue_script
                                parsed_segments = self._parse_dialogue_segments(dialogue_script)

                                # Check if parsing succeeded
                                if parsed_segments and len(parsed_segments) > 0:
                                    episode.conversation_segments = parsed_segments
                                    console.print(
                                        f"✅ Generated LLM conversation with {len(episode.conversation_segments)} segments"
                                    )
                                    # Debug: show first few speakers
                                    speakers = [seg.speaker for seg in episode.conversation_segments[:6]]
                                    console.print(f"🔍 Speaker sequence: {' → '.join(speakers)}")
                                else:
                                    console.print("[yellow]⚠️  Dialogue parsing returned empty, falling back to simple Q&A[/yellow]")
                                    episode.conversation_segments = self._create_simple_qa_segments(qa_content)
                                    console.print(f"✅ Created fallback Q&A with {len(episode.conversation_segments)} segments")
                                    speakers = [seg.speaker for seg in episode.conversation_segments[:6]]
                                    console.print(f"🔍 Speaker sequence: {' → '.join(speakers)}")
                            else:
                                console.print("[yellow]⚠️  LLM conversation generation failed, falling back to simple Q&A[/yellow]")
                                episode.conversation_segments = self._create_simple_qa_segments(qa_content)
                                console.print(f"✅ Created fallback Q&A with {len(episode.conversation_segments)} segments")
                                speakers = [seg.speaker for seg in episode.conversation_segments[:6]]
                                console.print(f"🔍 Speaker sequence: {' → '.join(speakers)}")
                        except Exception as e:
                            console.print(f"[yellow]⚠️  LLM conversation error: {e}, using simple Q&A[/yellow]")
                            episode.conversation_segments = self._create_simple_qa_segments(qa_content)
                            console.print(f"✅ Created fallback Q&A with {len(episode.conversation_segments)} segments")
                            speakers = [seg.speaker for seg in episode.conversation_segments[:6]]
                            console.print(f"🔍 Speaker sequence: {' → '.join(speakers)}")
                    else:
                        # Generate simple Q&A segments without complex conversation
                        console.print(f"🎙️ Creating simple Q&A structure (conversation mode disabled)...")
                        episode.conversation_segments = self._create_simple_qa_segments(qa_content)
                        console.print(f"✅ Created {len(episode.conversation_segments)} Q&A segments")
                        speakers = [seg.speaker for seg in episode.conversation_segments[:6]]
                        console.print(f"🔍 Speaker sequence: {' → '.join(speakers)}")

                    # Ensure we always have conversation segments
                    if not episode.conversation_segments or len(episode.conversation_segments) == 0:
                        console.print("[red]⚠️  No conversation segments created! Creating emergency fallback...[/red]")
                        console.print(f"🔍 Debug: conversation_segments type: {type(episode.conversation_segments)}, value: {episode.conversation_segments}")
                        console.print(f"🔍 Debug: qa_content has {len(qa_content)} items")

                        emergency_segments = self._create_simple_qa_segments(qa_content)
                        console.print(f"🔍 Emergency segments created: {len(emergency_segments)}")

                        episode.conversation_segments = emergency_segments

                        if episode.conversation_segments and len(episode.conversation_segments) > 0:
                            speakers = [seg.speaker for seg in episode.conversation_segments[:6]]
                            console.print(f"🚨 Emergency Q&A with {len(episode.conversation_segments)} segments: {' → '.join(speakers)}")
                        else:
                            console.print("[red]🚨🚨 CRITICAL: Emergency fallback also failed to create segments![/red]")

                    episodes.append(episode)
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
        console.print(f"🔗 Combining content from {len(pages)} pages...")
        combined = ""
        for page in pages:
            page_content = page.content.strip()
            console.print(f"📄 Adding '{page.title}' ({len(page_content)} chars)")
            combined += f"\n\n=== {page.title} ===\n{page_content}"

        result = combined.strip()
        console.print(f"📚 Combined content total: {len(result)} characters")
        return result

    def _convert_group_to_qa(self, group: PageGroup) -> List[QAContent]:
        """Convert a group of pages to holistic Q&A format."""
        console.print(
            f"🔍 Converting group '{group.name}' with {len(group.pages)} pages"
        )
        console.print(
            f"📄 Combined content length: {len(group.combined_content)} characters"
        )

        if len(group.combined_content.strip()) < 30:
            console.print(
                f"[yellow]⚠️  Group '{group.name}' has very little content ({len(group.combined_content)} chars), creating basic Q&A[/yellow]"
            )
            # Create a basic Q&A for small content
            return [
                QAContent(
                    question=f"What can you tell me about {group.name.lower()}?",
                    answer=f"Based on the documentation in {', '.join([p.title for p in group.pages])}: {group.combined_content.strip()}",
                )
            ]

        try:
            console.print(f"🤖 Sending to LLM for Q&A generation...")
            qa_response = self.llm_client.convert_group_to_qa(
                group.combined_content, group.name, [page.title for page in group.pages]
            )
            console.print(f"📝 LLM response length: {len(qa_response)} characters")
            console.print(f"🔍 LLM response preview: {qa_response[:200]}...")

            qa_items = self._parse_qa_response(qa_response)
            console.print(f"✅ Parsed {len(qa_items)} Q&A items from response")
            return qa_items
        except Exception as e:
            console.print(
                f"[red]Failed to convert group '{group.name}' to Q&A: {e}[/red]"
            )
            return []

    def _parse_qa_response(self, response: str) -> List[QAContent]:
        """Parse LLM response into structured Q&A content."""
        console.print(f"🔍 Parsing response with {len(response.split())} words")

        qa_items: List[QAContent] = []
        lines = [line.strip() for line in response.split("\n") if line.strip()]
        console.print(f"📝 Found {len(lines)} non-empty lines to process")

        # Try primary parsing method (Q: and A: format)
        qa_items = self._parse_standard_qa_format(lines)

        if not qa_items:
            console.print(
                "⚠️  Standard Q&A format parsing failed, trying alternative formats..."
            )
            # Try alternative parsing methods
            qa_items = self._parse_alternative_formats(response)

        # Emergency fallback: if still no Q&A items, create from raw response
        if not qa_items and response.strip():
            console.print(
                "[yellow]⚠️  All parsing failed, creating emergency Q&A from response content[/yellow]"
            )
            # Split response into chunks and create Q&A pairs
            sentences = [s.strip() for s in response.split('.') if s.strip() and len(s.strip()) > 20]
            if sentences:
                # Group sentences into Q&A pairs (every 2-3 sentences)
                for i in range(0, len(sentences), 3):
                    chunk = '. '.join(sentences[i:min(i+3, len(sentences))]) + '.'
                    if len(chunk) > 30:
                        qa_items.append(
                            QAContent(
                                question=f"Can you explain more about this topic?",
                                answer=chunk
                            )
                        )
                console.print(f"🚨 Created {len(qa_items)} emergency Q&A pairs from raw content")

        console.print(f"✅ Final result: {len(qa_items)} Q&A pairs extracted")
        return qa_items

    def _parse_standard_qa_format(self, lines: List[str]) -> List[QAContent]:
        """Parse standard Q: and A: format."""
        qa_items: List[QAContent] = []
        current_q = ""
        current_a = ""
        is_answer = False
        questions_found = 0
        answers_found = 0

        for i, line in enumerate(lines):
            if (
                line.startswith("Q:")
                or re.match(r"^Question \d+:", line)
                or re.match(r"^\d+\.", line)
            ):
                questions_found += 1
                console.print(f"🙋 Found question #{questions_found}: {line[:50]}...")

                # Save previous Q&A if complete
                if current_q and current_a:
                    qa_items.append(
                        QAContent(
                            question=re.sub(
                                r"^(Q:\s*|Question \d+:\s*|\d+\.\s*)", "", current_q
                            ).strip(),
                            answer=re.sub(r"^A:\s*", "", current_a).strip(),
                        )
                    )

                current_q = line
                current_a = ""
                is_answer = False

            elif line.startswith("A:") or line.startswith("Answer:"):
                answers_found += 1
                console.print(f"💡 Found answer #{answers_found}: {line[:50]}...")
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
                    question=re.sub(
                        r"^(Q:\s*|Question \d+:\s*|\d+\.\s*)", "", current_q
                    ).strip(),
                    answer=re.sub(r"^A:\s*", "", current_a).strip(),
                )
            )

        console.print(
            f"📊 Found {questions_found} questions and {answers_found} answers"
        )
        console.print(f"✅ Created {len(qa_items)} complete Q&A pairs")

        # Filter out empty Q&A items
        valid_qa_items = [qa for qa in qa_items if qa.question and qa.answer]
        filtered_count = len(qa_items) - len(valid_qa_items)
        if filtered_count > 0:
            console.print(f"⚠️  Filtered out {filtered_count} incomplete Q&A pairs")

        return valid_qa_items

    def _parse_alternative_formats(self, response: str) -> List[QAContent]:
        """Try alternative parsing methods if standard format fails."""
        qa_items: List[QAContent] = []

        # Method 1: Try to extract any patterns that look like questions and answers
        question_patterns = [
            r"(?:Question|Q)(?:\s*\d+)?[:\.]?\s*(.+?)(?=(?:Answer|A)[:\.]|$)",
            r"(\?.+?)(?=(?:Answer|A)[:\.]|$)",
        ]

        answer_patterns = [
            r"(?:Answer|A)(?:\s*\d+)?[:\.]?\s*(.+?)(?=(?:Question|Q)[:\.]|$)",
        ]

        for q_pattern in question_patterns:
            questions = re.findall(q_pattern, response, re.DOTALL | re.IGNORECASE)
            for a_pattern in answer_patterns:
                answers = re.findall(a_pattern, response, re.DOTALL | re.IGNORECASE)

                # Pair up questions and answers
                for i, question in enumerate(questions):
                    if i < len(answers):
                        q_clean = re.sub(r"\s+", " ", question.strip())
                        a_clean = re.sub(r"\s+", " ", answers[i].strip())
                        if q_clean and a_clean:
                            qa_items.append(QAContent(question=q_clean, answer=a_clean))

            if qa_items:
                console.print(f"✅ Alternative parsing found {len(qa_items)} Q&A pairs")
                break

        return qa_items

    def _generate_conversation(
        self, qa_content: List[QAContent], episode_title: str
    ) -> str:
        """Generate conversational dialogue from Q&A content."""
        try:
            console.print(f"🎭 Converting Q&A to natural conversation...")
            dialogue_script = self.llm_client.convert_qa_to_conversation(
                qa_content, episode_title, style="interview"
            )
            console.print(
                f"✅ Generated dialogue script ({len(dialogue_script)} characters)"
            )
            return dialogue_script
        except Exception as e:
            console.print(
                f"[red]Failed to generate conversation for '{episode_title}': {e}[/red]"
            )
            return ""

    def _parse_dialogue_segments(
        self, dialogue_script: str
    ) -> List[ConversationSegment]:
        """Parse dialogue script into conversation segments."""
        console.print("🔍 Parsing dialogue into segments...")
        console.print(f"📝 Dialogue script length: {len(dialogue_script)} chars")
        console.print(f"📝 First 200 chars: {dialogue_script[:200]}")

        segments = []
        lines = dialogue_script.split("\n")

        current_speaker = None
        current_text = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for speaker indicators (case-insensitive)
            if line.upper().startswith("ALEX:"):
                if current_speaker and current_text:
                    segments.append(
                        ConversationSegment(
                            speaker=current_speaker.lower(), text=current_text.strip()
                        )
                    )
                current_speaker = "alex"
                current_text = line[5:].strip()
                console.print(f"✅ Found ALEX segment")

            elif line.upper().startswith("SAM:"):
                if current_speaker and current_text:
                    segments.append(
                        ConversationSegment(
                            speaker=current_speaker.lower(), text=current_text.strip()
                        )
                    )
                current_speaker = "sam"
                current_text = line[4:].strip()
                console.print(f"✅ Found SAM segment")

            elif line.startswith("[") and line.endswith("]"):
                # Audio cue (e.g., [BOTH LAUGH], [PAUSE])
                audio_cue = line.lower().replace("[", "").replace("]", "")
                if "both" in audio_cue or "laugh" in audio_cue:
                    segments.append(ConversationSegment(speaker="both", text=line))
                else:
                    segments.append(ConversationSegment(speaker="narrator", text=line))

            else:
                # Continue current speaker's text
                if current_speaker and line:
                    current_text += " " + line

        # Don't forget the last segment
        if current_speaker and current_text:
            segments.append(
                ConversationSegment(
                    speaker=current_speaker.lower(), text=current_text.strip()
                )
            )

        console.print(f"✅ Parsed {len(segments)} conversation segments from dialogue")

        # If no segments were parsed, the dialogue format might be wrong
        if not segments and dialogue_script.strip():
            console.print("[yellow]⚠️  No segments parsed from dialogue, dialogue format may be incorrect[/yellow]")
            console.print("[yellow]   Expected format: 'ALEX: text' or 'SAM: text'[/yellow]")

        return segments

    def _create_simple_qa_segments(self, qa_content: List[QAContent]) -> List[ConversationSegment]:
        """Create simple Q&A conversation segments without complex dialogue generation."""
        console.print(f"🎙️ _create_simple_qa_segments called with {len(qa_content)} Q&A items")
        segments = []

        # Add introduction by Alex
        intro_segment = ConversationSegment(
            speaker="alex",
            text="Welcome everyone! I'm Alex, and today I have Sam here with me to discuss some important topics. Sam, let's dive into some key questions."
        )
        segments.append(intro_segment)
        console.print(f"✅ Added intro segment: {intro_segment.speaker}")

        # Create Q&A exchanges
        if not qa_content:
            console.print("[yellow]⚠️  No Q&A content provided, creating minimal content[/yellow]")
            # Create a minimal Q&A exchange if no content
            segments.append(
                ConversationSegment(
                    speaker="alex",
                    text="Sam, can you tell us about the topics we're covering today?"
                )
            )
            segments.append(
                ConversationSegment(
                    speaker="sam",
                    text="Thanks Alex! Today we're covering important onboarding information. Let's make sure everyone has the context they need to get started."
                )
            )
            console.print("✅ Added minimal Q&A exchange")
        else:
            for i, qa in enumerate(qa_content):
                # Alex asks the question
                question_text = f"Question {i+1}: {qa.question}"
                segments.append(
                    ConversationSegment(
                        speaker="alex",
                        text=question_text
                    )
                )
                console.print(f"✅ Added question segment {i+1}")

                # Sam provides the answer
                answer_text = qa.answer
                segments.append(
                    ConversationSegment(
                        speaker="sam",
                        text=answer_text
                    )
                )
                console.print(f"✅ Added answer segment {i+1}")

        # Add conclusion by Alex
        conclusion_segment = ConversationSegment(
            speaker="alex",
            text="Thank you Sam for those detailed explanations! That covers all our key topics for today. Thanks everyone for listening!"
        )
        segments.append(conclusion_segment)
        console.print(f"✅ Added conclusion segment: {conclusion_segment.speaker}")

        console.print(f"🎉 Total segments created: {len(segments)}")
        return segments

    def format_for_podcast(self, episode: PodcastEpisode) -> str:
        """Format episode content for podcast script."""
        # Use conversational format if available
        if episode.dialogue_script and episode.conversation_segments:
            console.print("📻 Using conversational format for podcast")
            return episode.dialogue_script

        # Fallback to traditional Q&A format
        console.print("📻 Using traditional Q&A format for podcast")
        intro = f"Welcome to the {episode.title} onboarding episode."

        if episode.source_pages:
            intro += f" This episode covers information from the following documentation pages: {', '.join(episode.source_pages)}."

        intro += " Let's dive into some key questions about this topic.\n\n"

        qa_text = ""
        for i, qa in enumerate(episode.content, 1):
            qa_text += f"Question {i}: {qa.question}\n\nAnswer: {qa.answer}\n\n"

        outro = f"That concludes our overview of {episode.title}. These insights should help you understand this part of our project better. Thank you for listening!"

        return intro + qa_text + outro
