"""Type definitions for ConvoCast."""

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


class Config(BaseModel):
    """Main application configuration."""
    confluence: ConfluenceConfig
    vllm: VLLMConfig
    output_dir: str
    max_pages: int
    voice_speed: float


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


class PodcastEpisode(BaseModel):
    """Podcast episode with Q&A content."""
    title: str
    content: List[QAContent]
    audio_path: Optional[str] = None


# Update forward references
ConfluencePage.model_rebuild()