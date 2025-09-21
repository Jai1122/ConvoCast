# ConvoCast

Convert Confluence pages into onboarding podcasts with AI-powered Q&A format conversion.

## Overview

ConvoCast is a Python tool designed to help new team members get familiar with project documentation by converting Confluence pages into engaging podcast episodes. It uses VLLM inference to transform technical documentation into conversational Q&A format, making onboarding smoother and more accessible.

## Features

- **Confluence Integration**: Securely access and traverse Confluence pages
- **AI-Powered Conversion**: Uses VLLM inference to convert content to Q&A format
- **Podcast Generation**: Text-to-speech conversion for audio episodes
- **Onboarding Focus**: Tailored for new team member orientation
- **CLI Interface**: Easy-to-use command-line tool with rich console output

## Setup

1. **Install Dependencies**
   ```bash
   pip install -e .
   # or
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Confluence Configuration
CONFLUENCE_BASE_URL=https://your-company.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-confluence-api-token

# VLLM Configuration
VLLM_API_URL=https://vllm.com
VLLM_API_KEY=your-vllm-api-key
VLLM_MODEL=llama-2-7b-chat

# Optional Configuration
OUTPUT_DIR=./output
MAX_PAGES=50
VOICE_SPEED=1.0
```

## Usage

### Generate Podcast Episodes

```bash
# Generate from a root Confluence page
convocast generate --page-id "123456789"

# Custom output directory and page limit
convocast generate --page-id "123456789" --output "./my-podcasts" --max-pages 25

# Generate text scripts only (skip audio)
convocast generate --page-id "123456789" --text-only
```

### Validate Configuration

```bash
convocast validate
```

## Output

ConvoCast generates:

- **Audio Files**: `.wav` podcast episodes
- **Text Scripts**: Formatted Q&A content
- **Summary**: JSON file with episode metadata

## Architecture

- **Confluence Client**: Handles secure API access and page traversal using requests
- **VLLM Integration**: Converts content using remote LLM inference
- **Content Processor**: Transforms documentation to onboarding-focused Q&A
- **TTS Generator**: Creates audio files using pyttsx3 or system TTS
- **CLI Interface**: User-friendly command-line tool built with Click

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run the CLI
python -m convocast.cli generate --page-id "123456789"

# Run tests
pytest

# Format code
black convocast/
isort convocast/

# Type checking
mypy convocast/
```