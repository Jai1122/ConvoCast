#!/usr/bin/env python3
"""
ConvoCast Setup and Stability Test Script

This script tests the entire ConvoCast installation and identifies
any missing dependencies or configuration issues.
"""

import sys
import subprocess
import os
from pathlib import Path

def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def test_python_version():
    print_section("Python Environment Test")
    print(f"Python version: {sys.version}")
    version_info = sys.version_info
    if version_info >= (3, 8):
        print("✓ Python version is compatible (3.8+)")
        return True
    else:
        print("❌ Python version too old. Requires Python 3.8+")
        return False

def test_core_imports():
    print_section("Core Dependencies Test")

    core_deps = [
        ('requests', 'HTTP requests'),
        ('click', 'CLI framework'),
        ('dotenv', 'Environment configuration'),
        ('bs4', 'HTML parsing'),
        ('pydantic', 'Data validation'),
        ('rich', 'Console output'),
        ('lxml', 'XML parsing')
    ]

    missing_deps = []

    for module, description in core_deps:
        try:
            __import__(module)
            print(f"✓ {module} - {description}")
        except ImportError:
            print(f"❌ {module} - {description} (MISSING)")
            missing_deps.append(module)

    return len(missing_deps) == 0

def test_tts_engines():
    print_section("TTS Engines Test")

    # Test pyttsx3
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        voice_count = len(voices) if voices else 0
        print(f"✓ pyttsx3 - Cross-platform TTS ({voice_count} voices available)")
        engine.stop()
        pyttsx3_available = True
    except Exception as e:
        print(f"❌ pyttsx3 - Cross-platform TTS (ERROR: {e})")
        pyttsx3_available = False

    # Test system TTS engines
    engines_tested = {'pyttsx3': pyttsx3_available}

    # Test espeak
    try:
        result = subprocess.run(['espeak', '--version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ espeak - Lightweight TTS")
            engines_tested['espeak'] = True
        else:
            print(f"❌ espeak - Command failed")
            engines_tested['espeak'] = False
    except Exception:
        print(f"❌ espeak - Not installed (install: sudo apt-get install espeak)")
        engines_tested['espeak'] = False

    # Test macOS say
    try:
        result = subprocess.run(['say', '--version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ macOS say - High quality TTS")
            engines_tested['macos_say'] = True
        else:
            print(f"❌ macOS say - Command failed")
            engines_tested['macos_say'] = False
    except Exception:
        print(f"❌ macOS say - Not available (macOS only)")
        engines_tested['macos_say'] = False

    available_engines = sum(engines_tested.values())
    print(f"\n📊 Summary: {available_engines}/{len(engines_tested)} TTS engines available")

    return available_engines > 0

def test_audio_tools():
    print_section("Audio Processing Tools Test")

    tools = []

    # Test ffmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ ffmpeg - Audio conversion ({version})")
            tools.append('ffmpeg')
        else:
            print(f"❌ ffmpeg - Command failed")
    except Exception:
        print(f"❌ ffmpeg - Not installed (recommended for audio conversion)")

    # Test lame
    try:
        result = subprocess.run(['lame', '--version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✓ lame - MP3 encoder")
            tools.append('lame')
        else:
            print(f"❌ lame - Command failed")
    except Exception:
        print(f"❌ lame - Not installed (alternative MP3 encoder)")

    return len(tools) > 0

def test_optional_deps():
    print_section("Optional Dependencies Test")

    optional_deps = [
        ('pygame', 'Enhanced audio handling'),
        ('pydub', 'Audio format conversion'),
        ('mutagen', 'Audio metadata'),
        ('gtts', 'Google TTS (online)')
    ]

    available_deps = []

    for module, description in optional_deps:
        try:
            __import__(module)
            print(f"✓ {module} - {description}")
            available_deps.append(module)
        except ImportError:
            print(f"⚠️  {module} - {description} (optional, install with: pip install {module})")

    return len(available_deps)

def test_convocast_import():
    print_section("ConvoCast Module Test")

    try:
        from convocast.types import TTSEngine, VoiceProfile, ConversationSegment
        print("✓ ConvoCast types import successfully")

        from convocast.audio.tts_generator import TTSGenerator
        print("✓ TTSGenerator import successfully")

        # Test voice profiles
        profiles = TTSGenerator.VOICE_PROFILES
        print(f"✓ {len(profiles)} voice profiles available")

        # Test engine priority
        temp_generator = TTSGenerator("./temp")
        fallback_engines = temp_generator.fallback_engines
        print(f"✓ Engine fallback order: {[e.value for e in fallback_engines]}")

        return True

    except Exception as e:
        print(f"❌ ConvoCast import failed: {e}")
        return False

def test_environment_config():
    print_section("Environment Configuration Test")

    env_file = Path('.env')
    env_example = Path('.env.example')

    if env_example.exists():
        print("✓ .env.example found")
        if env_file.exists():
            print("✓ .env file found")
            print("ℹ️  Remember to configure your VLLM and Confluence settings")
        else:
            print("⚠️  .env file not found - copy from .env.example and configure")
    else:
        print("❌ .env.example not found")

    return True

def generate_recommendations():
    print_section("Recommendations & Next Steps")

    print("📋 INSTALLATION RECOMMENDATIONS:")
    print("")
    print("1. CORE SETUP:")
    print("   pip install -e .")
    print("   # OR")
    print("   pip install -r requirements.txt")
    print("")
    print("2. AUDIO ENHANCEMENTS (optional):")
    print("   pip install pygame pydub mutagen")
    print("")
    print("3. SYSTEM TTS SETUP:")
    print("   # macOS: Built-in (no setup needed)")
    print("   # Linux: sudo apt-get install espeak espeak-data")
    print("   # Windows: Built-in via pyttsx3")
    print("")
    print("4. AUDIO TOOLS (recommended):")
    print("   # macOS: brew install ffmpeg lame")
    print("   # Linux: sudo apt-get install ffmpeg lame")
    print("   # Windows: Download from https://ffmpeg.org/")
    print("")
    print("5. CONFIGURATION:")
    print("   cp .env.example .env")
    print("   # Edit .env with your Confluence and VLLM settings")
    print("")
    print("📝 USAGE EXAMPLES:")
    print("")
    print("   # Test setup:")
    print("   convocast validate")
    print("")
    print("   # List available voices:")
    print("   convocast list-voices")
    print("")
    print("   # Generate podcast (offline):")
    print("   convocast generate --page-id 'YOUR_PAGE_ID' --conversation")
    print("")

def main():
    print("ConvoCast Setup and Stability Test")
    print("This script will test your ConvoCast installation")

    results = []
    results.append(test_python_version())
    results.append(test_core_imports())
    results.append(test_tts_engines())
    results.append(test_audio_tools())
    test_optional_deps()  # Non-critical
    results.append(test_convocast_import())
    test_environment_config()  # Non-critical

    print_section("FINAL RESULTS")

    critical_tests_passed = sum(results)
    total_critical_tests = len(results)

    if critical_tests_passed == total_critical_tests:
        print("🎉 ALL CRITICAL TESTS PASSED!")
        print("✅ ConvoCast is ready to use")
    else:
        print(f"⚠️  {critical_tests_passed}/{total_critical_tests} critical tests passed")
        print("❌ ConvoCast requires setup to function properly")

    generate_recommendations()

if __name__ == "__main__":
    main()