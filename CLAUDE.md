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

# Generate with specific TTS engine and voice profile
convocast generate --page-id "123456789" --tts-engine gtts --voice-profile gtts_british

# Generate conversational podcast with multiple speakers
convocast generate --page-id "123456789" --conversation --conversation-style interview

# List all available voice profiles
convocast list-voices

# Validate configuration and connections
convocast validate
```

## Audio Generation & Voice Profiles

ConvoCast now supports multiple TTS engines and voice profiles:

### Available TTS Engines:
- **pyttsx3**: Cross-platform, offline TTS (default)
- **gtts**: Google Text-to-Speech (requires internet)
- **macos_say**: macOS built-in 'say' command (macOS only)

### Built-in Voice Profiles:
- `default`: Standard pyttsx3 voice
- `narrator_male`: Professional male narrator (pyttsx3)
- `narrator_female`: Professional female narrator (pyttsx3)
- `gtts_default`: Google TTS English
- `gtts_british`: Google TTS British English
- `macos_alex`: macOS Alex voice

### Audio Output:
- All audio files are generated in MP3 format
- Automatic chunking for long content (gTTS)
- Fallback mechanisms for format conversion
- Enhanced error handling and debugging

## Conversational Podcasts

ConvoCast now supports **natural conversation generation** with multiple speakers:

### Features:
- **Two-Speaker Format**: Alex (female host) and Sam (male expert)
- **Natural Dialogue**: Interruptions, clarifications, and "aha!" moments
- **AI-Generated Scripts**: LLM converts Q&A into realistic conversations
- **Multi-Voice Audio**: Different TTS voices for each speaker
- **Audio Cues**: Supports [BOTH LAUGH], [PAUSE], *emphasis* markers

### Conversation Styles:
- `interview`: Alex interviews Sam (default)
- `discussion`: Two hosts explore topics together
- `teaching`: Teacher-student dynamic

### Example Usage:
```bash
# Basic conversational podcast
convocast generate --page-id "123" --conversation

# With specific style
convocast generate --page-id "123" --conversation --conversation-style discussion

# Conversational with Google TTS
convocast generate --page-id "123" --conversation --tts-engine gtts
```

### How It Works:
1. **Content Analysis**: Groups related documentation pages
2. **Q&A Generation**: Creates comprehensive questions/answers
3. **Dialogue Conversion**: LLM transforms Q&A into natural conversation
4. **Multi-Voice Audio**: Each speaker gets different voice characteristics
5. **Segment Combination**: Combines all audio with natural pauses

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