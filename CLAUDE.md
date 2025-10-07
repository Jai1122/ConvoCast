# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ConvoCast is a Python application that converts Confluence pages into onboarding podcasts. The system integrates with Confluence API, uses VLLM for LLM inference, and generates audio podcasts to help new team members familiarize themselves with project documentation.

## 🔍 Application Stability Status

### ✅ **STABLE COMPONENTS**
- **Core Architecture**: All modules import and function correctly
- **Conversation Generation**: Alex/Sam voice switching works reliably
- **Multiple TTS Engines**: Robust fallback system (pyttsx3 → Piper → macOS → eSpeak → gTTS)
- **Offline Operation**: No external API dependencies for TTS
- **Data Pipeline**: Content processing → Q&A generation → Audio output
- **Error Handling**: Graceful fallback when Piper models unavailable

### ⚠️  **SETUP REQUIREMENTS**
- **Dependencies**: Run `python test_setup.py` to verify installation
- **TTS Engines**: At least one must be available (pyttsx3 recommended)
- **Environment**: Configure `.env` for Confluence/VLLM access
- **Audio Tools**: ffmpeg/lame recommended for best audio quality

### 🧪 **TESTED CONFIGURATIONS**
- **Python**: 3.8+ (core functionality)
- **TTS Engines**: pyttsx3 (cross-platform), macOS say, espeak
- **Audio**: MP3 generation with multiple conversion fallbacks
- **Voice Switching**: Alex (female) ↔ Sam (male) conversation segments

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

# Generate with specific TTS engine and voice profile (fully offline)
convocast generate --page-id "123456789" --tts-engine pyttsx3 --voice-profile narrator_female

# Generate conversational podcast with multiple speakers
convocast generate --page-id "123456789" --conversation --conversation-style interview

# List all available voice profiles
convocast list-voices

# Validate configuration and connections
convocast validate
```

## Audio Generation & Voice Profiles

ConvoCast now supports multiple TTS engines and voice profiles:

### Available TTS Engines (Fully Offline):
- **pyttsx3**: Cross-platform offline TTS (default, most compatible)
- **piper**: High-quality offline neural TTS (requires model setup)
- **espeak**: Lightweight offline TTS (good for basic needs)
- **macos_say**: macOS built-in 'say' command (macOS only, high quality)
- **gtts**: Google Text-to-Speech (requires internet, not recommended)

### Built-in Voice Profiles (Offline):
- `piper_female`: High-quality offline female voice (Piper neural TTS)
- `piper_male`: High-quality offline male voice (Piper neural TTS)
- `alex_female`: Conversational female host (Alex) - Piper TTS
- `sam_male`: Technical expert male voice (Sam) - Piper TTS
- `espeak_female`: Lightweight female voice (eSpeak)
- `espeak_male`: Lightweight male voice (eSpeak)
- `default`: Standard pyttsx3 voice
- `narrator_male`: Professional male narrator (pyttsx3)
- `narrator_female`: Professional female narrator (pyttsx3)
- `macos_alex`: macOS Alex voice
- `gtts_default`: Google TTS English (requires internet)
- `gtts_british`: Google TTS British English (requires internet)

### Audio Output:
- All audio files are generated in MP3 format
- Automatic chunking for long content (gTTS)
- Fallback mechanisms for format conversion
- Enhanced error handling and debugging

## 🔧 Troubleshooting & Diagnostics

### Quick Diagnostics
```bash
# Test complete setup
python test_setup.py

# Verify TTS engines
convocast list-voices

# Test connectivity
convocast validate
```

### Common Issues & Solutions

#### **"Audio stops after 20-30 seconds"**
```bash
# Solution 1: Install audio tools
brew install ffmpeg lame  # macOS
sudo apt-get install ffmpeg lame  # Linux

# Solution 2: Try different TTS engine
convocast generate --page-id "123" --tts-engine pyttsx3
convocast generate --page-id "123" --tts-engine macos_say

# Solution 3: Use robust conversion
pip install pydub
```

#### **"No voice switching between Alex/Sam"**
```bash
# Ensure conversation mode is enabled
convocast generate --page-id "123" --conversation

# Verify voice profiles
convocast list-voices

# Check debug output for voice mapping
# Should show: Speaker 'alex' → Voice 'alex_female' → Engine 'piper'
```

#### **"TTS Engine not available"**
```bash
# Install missing engines
pip install pyttsx3  # Cross-platform
sudo apt-get install espeak  # Linux lightweight
brew install espeak  # macOS alternative

# Check engine priority in fallback order:
# 1. pyttsx3 (most compatible)
# 2. piper (if models available)
# 3. macos_say (macOS only)
# 4. espeak (Linux/basic)
```

#### **"Piper models not found" (Fixed - Now Falls Back Gracefully)**
```bash
# This is now handled automatically - system falls back to pyttsx3
# To enable Piper TTS (optional):
# 1. Download models from: https://github.com/rhasspy/piper/releases
# 2. Place .onnx and .onnx.json files in: ./piper_models/
# 3. Install Piper: pip install piper-tts

# Expected fallback behavior:
🎤 Trying piper engine...
⚠️  Piper models not found - falling back to next TTS engine
🎤 Trying pyttsx3 engine...
✅ Audio generated successfully with pyttsx3
```

#### **"Import errors"**
```bash
# Install core dependencies
pip install -e .

# Install optional audio dependencies
pip install convocast[audio]

# Check specific imports
python -c "from convocast.audio.tts_generator import TTSGenerator; print('OK')"
```

#### **"Audio File Issues"**
```bash
# Install audio processing tools
brew install ffmpeg lame  # macOS
sudo apt-get install ffmpeg lame  # Linux

# Check file permissions
chmod 755 ./output

# Verify output directory exists
mkdir -p ./output
```

#### **"VLLM Connection Failed"**
```bash
# Check VLLM server status
curl -X GET http://your-vllm-server:8000/health

# Verify API endpoint and key in .env
cat .env | grep VLLM

# Test connectivity
convocast validate
```

### Platform-Specific Notes

#### **macOS**
- Built-in `say` command provides excellent quality
- Use Homebrew for easy dependency installation
- May need to allow microphone access

#### **Linux**
- Install espeak for basic TTS: `sudo apt-get install espeak espeak-data`
- May need additional audio codecs
- Check ALSA/PulseAudio configuration

#### **Windows**
- Use pyttsx3 with SAPI voices
- May need Visual C++ redistributables
- Check Windows speech settings

### Performance Optimization

#### **Faster Audio Generation**
- Use `pyttsx3` or `espeak` (offline, fast)
- Install `ffmpeg` for efficient conversion
- Reduce `--max-pages` for testing

#### **Better Audio Quality**
- Use `macos_say` on macOS
- Install Piper neural models for best quality
- Use higher bitrate in conversion (192k vs 128k)

#### **Offline Operation**
- Use `pyttsx3`, `espeak`, or `macos_say` engines
- Avoid `gtts` (requires internet)
- Pre-download Piper models if using neural TTS

### Debug Output Interpretation

```bash
# Expected successful conversation output:
🎭 Generating conversation segments (enable_conversation=True)...
✅ Created 8 Q&A segments
🔍 Speaker sequence: alex → sam → alex → sam
🎤 Trying pyttsx3 engine...
🎭 Speaker 'alex' → Voice 'alex_female' → Engine 'piper'
✅ Audio generated successfully with pyttsx3
```

### File Structure Validation
```bash
# Check required files exist
ls -la .env                    # Environment config
ls -la convocast/             # Main package
ls -la requirements.txt       # Dependencies
python test_setup.py         # Comprehensive test
```

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