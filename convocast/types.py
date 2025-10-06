"""Type definitions for ConvoCast."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ConfluenceConfig(BaseModel):
    """Configuration for Confluence connection."""

    base_url: str
    username: str
    api_token: str


class VLLMConfig(BaseModel):
    """Configuration for VLLM connection."""

    api_url: str
    api_key: str
    model: str


class TTSEngine(str, Enum):
    """Available TTS engines."""

    PYTTSX3 = "pyttsx3"
    GTTS = "gtts"
    MACOS_SAY = "macos_say"
    EDGE_TTS = "edge_tts"


class VoiceProfile(BaseModel):
    """Voice profile configuration."""

    name: str
    engine: TTSEngine
    voice_id: Optional[str] = None  # Engine-specific voice ID
    language: str = "en"
    speed: float = 1.0
    pitch: float = 1.0


class Config(BaseModel):
    """Main application configuration."""

    confluence: ConfluenceConfig
    vllm: VLLMConfig
    output_dir: str
    max_pages: int
    voice_speed: float
    tts_engine: TTSEngine = TTSEngine.PYTTSX3
    voice_profile: Optional[str] = None


class ConfluencePage(BaseModel):
    """Represents a Confluence page."""

    id: str
    title: str
    content: str
    url: str
    children: Optional[List["ConfluencePage"]] = None


class QAContent(BaseModel):
    """Question and answer content."""

    question: str
    answer: str


class PageGroup(BaseModel):
    """Group of related Confluence pages."""

    name: str
    pages: List[ConfluencePage]
    combined_content: str = ""


class ConversationSegment(BaseModel):
    """A segment of conversation with speaker and text."""

    speaker: str  # "alex", "sam", "both", "narrator"
    text: str
    duration_seconds: Optional[float] = None
    audio_path: Optional[str] = None


class ConversationStyle(str, Enum):
    """Available conversation styles."""

    INTERVIEW = "interview"
    DISCUSSION = "discussion"
    TEACHING = "teaching"


class PodcastEpisode(BaseModel):
    """Podcast episode with Q&A content and conversation support."""

    title: str
    content: List[QAContent]
    audio_path: Optional[str] = None
    source_pages: Optional[List[str]] = None

    # Conversational content
    dialogue_script: Optional[str] = None
    conversation_segments: Optional[List[ConversationSegment]] = None
    conversation_style: ConversationStyle = ConversationStyle.INTERVIEW


# Update forward references
ConfluencePage.model_rebuild()
