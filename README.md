# ConvoCast

Convert Confluence pages into onboarding podcasts with AI-powered Q&A format conversion.

## Overview

ConvoCast is a Python tool designed to help new team members get familiar with project documentation by converting Confluence pages into engaging podcast episodes. It uses VLLM inference to transform technical documentation into conversational Q&A format, making onboarding smoother and more accessible.

## 🚀 Quick Start

```bash
# 1. Install ConvoCast
git clone <repository-url>
cd ConvoCast
pip install -e .

# 2. Test your setup
python test_setup.py

# 3. Configure environment
cp .env.example .env
# Edit .env with your Confluence and VLLM settings

# 4. Generate your first podcast
convocast generate --page-id "YOUR_PAGE_ID" --conversation
```

## ✅ Stability Status

**STABLE** - Ready for production use with proper setup:
- ✅ Core conversation generation pipeline works reliably
- ✅ Alex/Sam voice switching functions correctly
- ✅ Multiple TTS engine fallbacks ensure audio generation
- ✅ Fully offline operation (no external TTS APIs)
- ✅ Comprehensive error handling and debugging

**Requirements**: Run `python test_setup.py` to verify your installation.

## Features

- **Confluence Integration**: Securely access and traverse Confluence pages
- **AI-Powered Conversion**: Uses VLLM inference to convert content to Q&A format
- **Multi-Speaker Podcasts**: Natural conversations between Alex (host) and Sam (expert)
- **Flexible Audio Generation**: Multiple TTS engines with voice profiles
- **Clean Audio Output**: Automatically removes formatting artifacts like asterisks
- **Conversation Modes**: Simple Q&A or complex natural dialogue
- **Podcast Generation**: High-quality text-to-speech conversion for audio episodes
- **Onboarding Focus**: Tailored for new team member orientation
- **CLI Interface**: Easy-to-use command-line tool with rich console output

## Setup

### Quick Start

1. **Install Dependencies**
   ```bash
   pip install -e .
   # or
   pip install -r requirements.txt
   ```

2. **Test Your Setup**
   ```bash
   python test_setup.py
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Validate Installation**
   ```bash
   convocast validate
   ```

### System Requirements

- **Python**: 3.8+ (tested with 3.8-3.11)
- **Operating System**: Windows, macOS, Linux
- **Memory**: 4GB RAM minimum, 8GB recommended

### Optional Audio Dependencies

For better audio processing:
```bash
pip install convocast[audio]
# OR manually:
pip install pygame pydub mutagen
```

### System TTS Setup

**macOS** (Recommended): Built-in `say` command (no setup needed)

**Linux**:
```bash
sudo apt-get install espeak espeak-data
```

**Windows**: Built-in SAPI voices via pyttsx3 (no setup needed)

### Audio Tools (Recommended)

**macOS**:
```bash
brew install ffmpeg lame
```

**Linux**:
```bash
sudo apt-get install ffmpeg lame
```

**Windows**: Download FFmpeg from https://ffmpeg.org/

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

#### Basic Usage

```bash
# Generate from a root Confluence page
convocast generate --page-id "123456789"

# Custom output directory and page limit
convocast generate --page-id "123456789" --output "./my-podcasts" --max-pages 25

# Generate text scripts only (skip audio)
convocast generate --page-id "123456789" --text-only
```

#### Multi-Speaker Q&A Mode (Default)

```bash
# Simple Q&A with two speakers - Alex asks questions, Sam provides answers
convocast generate --page-id "123456789"

# Use different TTS engines for distinct voices
convocast generate --page-id "123456789" --tts-engine gtts
convocast generate --page-id "123456789" --tts-engine macos_say
```

**How it works:**
- **Alex (Female Host)**: Asks all questions with curiosity and enthusiasm
- **Sam (Male Expert)**: Provides all answers with technical knowledge
- **Clean Audio**: Automatically removes asterisks, formatting, and audio cues
- **Natural Flow**: Includes introductions and conclusions

#### Advanced Conversational Mode

```bash
# Generate natural conversation with interruptions and reactions
convocast generate --page-id "123456789" --conversation

# Different conversation styles
convocast generate --page-id "123456789" --conversation --conversation-style interview
convocast generate --page-id "123456789" --conversation --conversation-style discussion
convocast generate --page-id "123456789" --conversation --conversation-style teaching
```

**Conversation Features:**
- **Natural Dialogue**: AI-generated conversations with interruptions and reactions
- **Multiple Speakers**: Alex and Sam have distinct personalities and speaking styles
- **Audio Cues**: Supports [BOTH LAUGH], [PAUSE], [EXCITED] for natural flow
- **Follow-up Questions**: Alex asks clarifying questions beyond the original Q&A

#### Audio & Voice Configuration

```bash
# List available voice profiles
convocast list-voices

# Use specific TTS engines
convocast generate --page-id "123456789" --tts-engine pyttsx3    # Cross-platform (default)
convocast generate --page-id "123456789" --tts-engine gtts       # Google TTS (requires internet)
convocast generate --page-id "123456789" --tts-engine macos_say  # macOS only

# Use specific voice profiles
convocast generate --page-id "123456789" --voice-profile default
convocast generate --page-id "123456789" --voice-profile narrator_female
convocast generate --page-id "123456789" --voice-profile gtts_british
convocast generate --page-id "123456789" --voice-profile macos_alex

# Multi-speaker with different engines
convocast generate --page-id "123456789" --conversation
# Alex uses Google TTS (female), Sam uses macOS say (male) for distinct voices
```

**Available Voice Profiles:**
- `default`: Standard cross-platform voice
- `narrator_male`: Professional male narrator
- `narrator_female`: Professional female narrator
- `gtts_default`: Google TTS English
- `gtts_british`: Google TTS British English
- `macos_alex`: macOS Alex voice
- `alex_female`: Optimized for Alex (curious host)
- `sam_male`: Optimized for Sam (technical expert)

### Audio Quality Features

**Clean Speech Output:**
- ✅ **Asterisks Removed**: `*emphasis*` becomes natural speech
- ✅ **Formatting Cleaned**: Removes markdown, code formatting
- ✅ **Audio Cues Processed**: `[BOTH LAUGH]` creates natural pauses
- ✅ **Speaker Labels Stripped**: `ALEX:` and `SAM:` labels removed from audio
- ✅ **Punctuation Normalized**: Multiple punctuation marks cleaned up

### Validate Configuration

```bash
convocast validate
```

## Output

ConvoCast generates:

- **Audio Files**: High-quality `.mp3` podcast episodes with multi-speaker support
- **Text Scripts**: Clean, formatted conversation or Q&A content
- **Conversation Segments**: Individual audio files for each speaker (when using conversation mode)
- **Summary**: JSON file with episode metadata and speaker information

### Output Structure

```
output/
├── episode-name.mp3              # Final combined audio
├── episode-name.txt              # Clean text script
├── episode-name-summary.json     # Episode metadata
└── segments/                     # Individual speaker segments (conversation mode)
    ├── episode-name_001_alex.mp3
    ├── episode-name_002_sam.mp3
    └── ...
```

### Text Script Format

**Simple Q&A Mode:**
```
ALEX: Welcome everyone! I'm Alex, and today I have Sam here with me...
SAM: Thank you Alex! Let me explain...
ALEX: Question 1: What is the main purpose of this system?
SAM: The main purpose of this system is to...
```

**Conversation Mode:**
```
ALEX: Hey everyone! Welcome to Tech Talk. Sam, I have to admit, APIs confused me at first.
SAM: Oh, I totally get that! Think of it like a restaurant menu...
ALEX: That's brilliant! So the API is like the waiter?
SAM: Exactly! The waiter takes your order and brings back your food.
[BOTH LAUGH]
```

## Architecture

- **Confluence Client**: Handles secure API access and page traversal using requests
- **VLLM Integration**: Converts content using remote LLM inference
- **Content Processor**: Transforms documentation to onboarding-focused Q&A
- **TTS Generator**: Creates audio files using pyttsx3 or system TTS
- **CLI Interface**: User-friendly command-line tool built with Click

## Troubleshooting

### Audio Issues

**Problem: TTS generation hangs or fails**
```bash
# Ensure you're using the virtual environment
source venv/bin/activate
convocast generate --page-id "123456789"
```

**Problem: Asterisks being read aloud**
- ✅ **Fixed in latest version**: Asterisks are automatically removed from speech
- The system now cleans all formatting markers before TTS generation

**Problem: Voice sounds robotic or unclear**
```bash
# Try different TTS engines
convocast generate --page-id "123456789" --tts-engine gtts      # Often more natural
convocast generate --page-id "123456789" --tts-engine macos_say # macOS only, high quality

# Use conversation mode for better flow
convocast generate --page-id "123456789" --conversation
```

**Problem: Can't distinguish between speakers**
```bash
# Use conversation mode with distinct voices
convocast generate --page-id "123456789" --conversation
# Alex (female) and Sam (male) will have different voice characteristics

# Or use specific voice profiles
convocast generate --page-id "123456789" --voice-profile narrator_female
```

### Environment Issues

**Problem: Missing dependencies**
```bash
# Install all TTS dependencies
pip install -r requirements.txt
pip install -e .

# For macOS users
brew install ffmpeg  # Optional, for better audio conversion
```

**Problem: VLLM API errors**
- Check your `.env` file has correct VLLM credentials
- Verify your API key has sufficient quota
- Run `convocast validate` to test connections

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