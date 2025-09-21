# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ConvoCast is a Python application that converts Confluence pages into onboarding podcasts. The system integrates with Confluence API, uses VLLM for LLM inference, and generates audio podcasts to help new team members familiarize themselves with project documentation.

## Development Commands

```bash
# Install dependencies
pip install -e .
# or
pip install -r requirements.txt

# Install with development dependencies
pip install -e ".[dev]"

# Run the CLI
convocast --help

# Run tests
pytest

# Format code
black convocast/
isort convocast/

# Type checking
mypy convocast/
```

## Key CLI Commands

```bash
# Generate podcast from Confluence pages
convocast generate --page-id "123456789"

# Generate with custom options
convocast generate --page-id "123456789" --output "./output" --max-pages 25

# Generate text scripts only (no audio)
convocast generate --page-id "123456789" --text-only

# Validate configuration and connections
convocast validate
```

## Architecture

### Core Components

- **convocast/confluence/client.py**: Confluence API integration with authentication and page traversal
- **convocast/llm/vllm_client.py**: VLLM API client for secure LLM inference
- **convocast/processors/content_processor.py**: Content transformation pipeline for Q&A conversion
- **convocast/audio/tts_generator.py**: Text-to-speech audio generation
- **convocast/cli.py**: Command-line interface and main application entry point

### Configuration

- Environment variables managed in **convocast/config/__init__.py**
- Required env vars: CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN, VLLM_API_URL, VLLM_API_KEY
- Copy **.env.example** to **.env** and configure credentials

### Data Flow

1. Confluence client authenticates and traverses pages from root page ID
2. Content processor extracts and cleans HTML content using BeautifulSoup
3. VLLM client converts content to Q&A format for onboarding context
4. TTS generator creates audio files from processed scripts
5. CLI orchestrates the entire pipeline and handles output

### Python Types

All data models defined using Pydantic in **convocast/types.py** including:
- ConfluenceConfig, VLLMConfig, Config
- ConfluencePage, QAContent, PodcastEpisode

## Error Handling

- All API calls include proper error handling and timeout configuration
- VLLM client handles authentication errors and API timeouts
- Content processing skips pages with insufficient content
- Audio generation continues even if individual episodes fail
- Rich console provides colored output for better error visibility

## Development Notes

- Uses requests for HTTP requests with proper authentication headers
- BeautifulSoup with lxml parser for HTML parsing and content extraction
- Click for CLI framework with rich console output
- Built-in 'say' command for macOS TTS (pyttsx3 as alternative)
- Pydantic for data validation and type safety
- Output directory structure: audio files, text scripts, and JSON summary