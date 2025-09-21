"""Configuration management for ConvoCast."""

import os
from typing import Optional
from dotenv import load_dotenv
from ..types import Config, ConfluenceConfig, VLLMConfig

# Load environment variables
load_dotenv()


def get_config() -> Config:
    """Load and validate configuration from environment variables."""
    required_env_vars = [
        "CONFLUENCE_BASE_URL",
        "CONFLUENCE_USERNAME",
        "CONFLUENCE_API_TOKEN",
        "VLLM_API_URL",
        "VLLM_API_KEY"
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    confluence_config = ConfluenceConfig(
        base_url=os.getenv("CONFLUENCE_BASE_URL", ""),
        username=os.getenv("CONFLUENCE_USERNAME", ""),
        api_token=os.getenv("CONFLUENCE_API_TOKEN", "")
    )

    vllm_config = VLLMConfig(
        api_url=os.getenv("VLLM_API_URL", ""),
        api_key=os.getenv("VLLM_API_KEY", ""),
        model=os.getenv("VLLM_MODEL", "llama-2-7b-chat")
    )

    return Config(
        confluence=confluence_config,
        vllm=vllm_config,
        output_dir=os.getenv("OUTPUT_DIR", "./output"),
        max_pages=int(os.getenv("MAX_PAGES", "50")),
        voice_speed=float(os.getenv("VOICE_SPEED", "1.0"))
    )