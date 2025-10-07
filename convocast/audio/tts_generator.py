"""Text-to-speech generator for podcast audio."""

import io
import os
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from rich.console import Console

from ..types import ConversationSegment, PodcastEpisode, TTSEngine, VoiceProfile

console = Console()


class TTSGenerator:
    """Enhanced text-to-speech generator with multiple engine support."""

    # Predefined voice profiles
    VOICE_PROFILES = {
        "default": VoiceProfile(
            name="Default",
            engine=TTSEngine.PYTTSX3,
            language="en",
            speed=1.0,
            pitch=1.0,
        ),
        "narrator_male": VoiceProfile(
            name="Professional Male Narrator",
            engine=TTSEngine.PYTTSX3,
            voice_id=(
                "com.apple.voice.compact.en-US.Samantha" if os.name == "posix" else None
            ),
            language="en",
            speed=0.9,
            pitch=0.8,
        ),
        "narrator_female": VoiceProfile(
            name="Professional Female Narrator",
            engine=TTSEngine.PYTTSX3,
            voice_id=(
                "com.apple.voice.compact.en-US.Alex" if os.name == "posix" else None
            ),
            language="en",
            speed=0.85,
            pitch=1.1,
        ),
        "gtts_default": VoiceProfile(
            name="Google TTS Default",
            engine=TTSEngine.GTTS,
            language="en",
            speed=0.8,
            pitch=1.0,
        ),
        "gtts_british": VoiceProfile(
            name="Google TTS British",
            engine=TTSEngine.GTTS,
            language="en-uk",
            speed=0.8,
            pitch=1.0,
        ),
        "macos_alex": VoiceProfile(
            name="macOS Alex",
            engine=TTSEngine.MACOS_SAY,
            voice_id="Alex",
            language="en",
            speed=0.85,
            pitch=1.0,
        ),
        # Piper voices (high quality, fully offline neural TTS)
        "piper_female": VoiceProfile(
            name="Piper Female - High Quality Offline",
            engine=TTSEngine.PIPER,
            voice_id="en_US-amy-medium",  # Clear female voice
            language="en-US",
            speed=0.8,
            pitch=1.0,
        ),
        "piper_male": VoiceProfile(
            name="Piper Male - High Quality Offline",
            engine=TTSEngine.PIPER,
            voice_id="en_US-ryan-medium",  # Clear male voice
            language="en-US",
            speed=0.75,
            pitch=1.0,
        ),
        # Conversation-specific voices (Platform optimized)
        "alex_female": VoiceProfile(
            name="Alex - Curious Female Host",
            engine=TTSEngine.MACOS_SAY if platform.system() == "Darwin" else TTSEngine.PYTTSX3,
            voice_id="Samantha" if platform.system() == "Darwin" else "female",  # High quality female voice
            language="en-US",
            speed=0.8,  # Energetic pace
            pitch=1.0,
        ),
        "sam_male": VoiceProfile(
            name="Sam - Knowledgeable Male Expert",
            engine=TTSEngine.MACOS_SAY if platform.system() == "Darwin" else TTSEngine.PYTTSX3,
            voice_id="Alex" if platform.system() == "Darwin" else "male",  # High quality male voice
            language="en-US",
            speed=0.75,   # Thoughtful pace
            pitch=1.0,
        ),
        # eSpeak voices (lightweight offline backup)
        "espeak_female": VoiceProfile(
            name="eSpeak Female - Lightweight Offline",
            engine=TTSEngine.ESPEAK,
            voice_id="en+f3",  # Female voice variant 3
            language="en",
            speed=0.85,
            pitch=1.1,
        ),
        "espeak_male": VoiceProfile(
            name="eSpeak Male - Lightweight Offline",
            engine=TTSEngine.ESPEAK,
            voice_id="en+m3",  # Male voice variant 3
            language="en",
            speed=0.8,
            pitch=0.9,
        ),
    }

    # Speaker-to-voice mapping for conversations
    CONVERSATION_VOICES = {
        "alex": "alex_female",
        "sam": "sam_male",
        "narrator": "default",
        "both": "narrator",  # For shared segments like laughter
    }

    def __init__(
        self,
        output_dir: str,
        voice_speed: float = 1.0,
        engine: TTSEngine = TTSEngine.PYTTSX3,
        voice_profile: Optional[str] = None,
    ) -> None:
        """Initialize TTS generator with enhanced options."""
        self.output_dir = Path(output_dir)
        self.voice_speed = voice_speed
        self.engine = engine
        self.voice_profile = self.VOICE_PROFILES.get(
            voice_profile or "default", self.VOICE_PROFILES["default"]
        )

        # Define fallback engine order for robustness (best quality first)
        import platform
        if platform.system() == "Darwin":  # macOS
            self.fallback_engines = [
                TTSEngine.MACOS_SAY,  # macOS high quality offline (best on macOS)
                TTSEngine.PYTTSX3,    # Cross-platform offline fallback
                TTSEngine.PIPER,      # Best quality offline neural TTS (if models available)
                TTSEngine.ESPEAK,     # Lightweight offline backup
                TTSEngine.GTTS,       # Last resort (requires internet)
            ]
        else:
            self.fallback_engines = [
                TTSEngine.PYTTSX3,    # Cross-platform offline (most compatible)
                TTSEngine.PIPER,      # Best quality offline neural TTS (if models available)
                TTSEngine.MACOS_SAY,  # macOS high quality offline
                TTSEngine.ESPEAK,     # Lightweight offline backup
                TTSEngine.GTTS,       # Last resort (requires internet)
            ]

        # Initialize pygame mixer for audio handling (optional)
        try:
            import pygame
            import os
            # Disable pygame's welcome message and potential audio device issues
            os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
            # Use better audio settings to prevent stopping issues
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.init()
            # Set additional mixer settings for better playback
            pygame.mixer.set_num_channels(8)
            console.print("✓ Pygame mixer initialized for enhanced audio handling")
        except ImportError:
            console.print("[yellow]⚠️  Pygame not available - using basic audio combination[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Pygame mixer initialization failed: {e}[/yellow]")
            console.print("[yellow]   Using basic audio combination[/yellow]")

    def generate_audio(self, episode: PodcastEpisode, script: str) -> str:
        """Generate audio file for a single episode."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        filename = self._sanitize_filename(episode.title)
        audio_path = self.output_dir / f"{filename}.mp3"
        script_path = self.output_dir / f"{filename}.txt"

        # Save script file
        script_path.write_text(script, encoding="utf-8")

        try:
            # Clean the script before TTS generation to remove asterisks and formatting
            cleaned_script = self._clean_audio_cues(script)
            console.print(f"🧹 Cleaned script: {len(script)} → {len(cleaned_script)} characters")

            # Try generating with primary engine, then fallbacks
            audio_generated = False
            last_error = None

            # List of engines to try (primary first, then fallbacks)
            engines_to_try = [self.voice_profile.engine] + [
                engine for engine in self.fallback_engines
                if engine != self.voice_profile.engine
            ]

            for engine_attempt in engines_to_try:
                try:
                    console.print(f"🎤 Trying {engine_attempt.value} engine...")

                    if engine_attempt == TTSEngine.PIPER:
                        self._generate_with_piper(cleaned_script, str(audio_path))
                    elif engine_attempt == TTSEngine.ESPEAK:
                        self._generate_with_espeak(cleaned_script, str(audio_path))
                    elif engine_attempt == TTSEngine.PYTTSX3:
                        self._generate_with_pyttsx3(cleaned_script, str(audio_path))
                    elif engine_attempt == TTSEngine.GTTS:
                        self._generate_with_gtts(cleaned_script, str(audio_path))
                    elif engine_attempt == TTSEngine.MACOS_SAY:
                        self._generate_with_say(cleaned_script, str(audio_path))
                    else:
                        continue  # Skip unsupported engines

                    # Validate the generated audio
                    if self._validate_audio_file(str(audio_path), cleaned_script):
                        console.print(f"✅ Audio generated successfully with {engine_attempt.value}")
                        audio_generated = True
                        break
                    else:
                        console.print(f"[yellow]⚠️  {engine_attempt.value} generated invalid audio, trying next engine[/yellow]")
                        continue

                except Exception as e:
                    last_error = e
                    console.print(f"[yellow]⚠️  {engine_attempt.value} failed: {str(e)[:100]}..., trying next engine[/yellow]")
                    continue

            if not audio_generated:
                raise RuntimeError(f"All TTS engines failed. Last error: {last_error}")

            console.print(f"🎵 Audio generated: [green]{audio_path}[/green]")
            return str(audio_path)
        except Exception as e:
            console.print(
                f"[red]❌ Failed to generate audio for '{episode.title}': {e}[/red]"
            )
            raise

    def generate_conversation_audio(self, episode: PodcastEpisode, script: str) -> str:
        """Generate multi-speaker audio for conversational episodes."""

        # Check if we have sufficient conversation segments
        if not episode.conversation_segments:
            console.print(
                "[yellow]⚠️  No conversation segments found, using standard generation[/yellow]"
            )
            return self.generate_audio(episode, script)

        # Check if conversation segments are too minimal (less than 100 chars total)
        total_segment_length = sum(len(seg.text) for seg in episode.conversation_segments)
        script_length = len(script)

        console.print(f"🔍 Conversation segments: {len(episode.conversation_segments)} segments, {total_segment_length} chars")
        console.print(f"🔍 Full script length: {script_length} chars")

        # If segments are minimal but script is substantial, convert script to segments
        if total_segment_length < 100 and script_length > 200:
            console.print("🔄 Converting full script to conversation segments (segments too minimal)")
            return self._generate_audio_from_script(script, episode.title)

        # If segments are insufficient compared to script, enhance them
        if script_length > total_segment_length * 3:
            console.print("⚠️  Conversation segments seem incomplete compared to full script")
            console.print("🔄 Using full script content instead of minimal segments")
            return self._generate_audio_from_script(script, episode.title)

        console.print(
            f"🎭 Generating conversation audio with {len(episode.conversation_segments)} segments"
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._sanitize_filename(episode.title)

        # Generate audio for each segment
        segment_files = []
        for i, segment in enumerate(episode.conversation_segments):
            console.print(
                f"🎤 Processing segment {i+1}/{len(episode.conversation_segments)}: {segment.speaker}"
            )

            # Clean up audio cues for TTS
            text = self._clean_audio_cues(segment.text)
            if not text.strip():
                continue

            # Get voice profile for this speaker
            voice_profile_name = self.CONVERSATION_VOICES.get(
                segment.speaker, "default"
            )
            voice_profile = self.VOICE_PROFILES.get(
                voice_profile_name, self.VOICE_PROFILES["default"]
            )

            console.print(f"🎭 Speaker '{segment.speaker}' → Voice '{voice_profile_name}' → Engine '{voice_profile.engine.value}'")

            # Generate segment audio
            segment_filename = f"{filename}_segment_{i:03d}_{segment.speaker}.mp3"
            segment_path = self.output_dir / segment_filename

            try:
                console.print(f"🎤 Generating audio for: '{text[:50]}...'")
                self._generate_segment_with_voice(
                    text, str(segment_path), voice_profile
                )

                # Verify the segment was created successfully
                if os.path.exists(str(segment_path)) and os.path.getsize(str(segment_path)) > 0:
                    segment_files.append(str(segment_path))
                    console.print(f"✓ Segment {i+1} generated successfully")
                else:
                    console.print(f"[yellow]⚠️  Segment {i+1} file was not created or is empty[/yellow]")
                    continue

                # Add pause after each segment for natural conversation flow
                if segment.speaker in ["alex", "sam"]:
                    try:
                        pause_file = self._generate_pause(0.5)  # 0.5 second pause
                        if pause_file:  # Only add if pause generation succeeded
                            segment_files.append(pause_file)
                    except Exception as pause_error:
                        console.print(f"[yellow]⚠️  Failed to generate pause: {pause_error}[/yellow]")

            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Skipping segment {i+1} due to error: {e}[/yellow]"
                )
                import traceback
                console.print(f"[yellow]Full error trace: {traceback.format_exc()}[/yellow]")
                continue

        if not segment_files:
            raise RuntimeError("No audio segments were generated successfully")

        # Combine all segments into final audio
        final_audio_path = self.output_dir / f"{filename}.mp3"
        console.print(f"🔗 Combining {len(segment_files)} audio segments...")

        self._combine_audio_files(segment_files, str(final_audio_path))

        # Clean up temporary segment files (both MP3 and WAV)
        console.print(f"🧹 Cleaning up {len(segment_files)} temporary segment files...")
        for segment_file in segment_files:
            try:
                if os.path.exists(segment_file):
                    # Clean up segment files and related files
                    if "segment_" in segment_file or "pause_" in segment_file:
                        os.unlink(segment_file)
                        console.print(f"✅ Removed: {os.path.basename(segment_file)}")

                    # Also clean up any related WAV files
                    wav_equivalent = segment_file.replace('.mp3', '.wav')
                    if os.path.exists(wav_equivalent) and "segment_" in wav_equivalent:
                        os.unlink(wav_equivalent)
                        console.print(f"✅ Removed WAV: {os.path.basename(wav_equivalent)}")

                    # Clean up any remaining temporary WAV files in output directory
                    import glob
                    remaining_wavs = glob.glob(str(self.output_dir / "*.wav"))
                    for wav_file in remaining_wavs:
                        if "temp" in wav_file or "pause" in wav_file:
                            try:
                                os.unlink(wav_file)
                                console.print(f"✅ Cleaned up temp WAV: {os.path.basename(wav_file)}")
                            except:
                                pass
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not remove {segment_file}: {e}[/yellow]")

        console.print(
            f"🎵 Conversation audio generated: [green]{final_audio_path}[/green]"
        )

        # Validate the final combined audio
        if self._validate_audio_file(str(final_audio_path)):
            console.print("✓ Final conversation audio validation passed")
        else:
            console.print("[yellow]⚠️  Final conversation audio validation failed[/yellow]")

        return str(final_audio_path)

    def _generate_audio_from_script(self, script: str, episode_title: str) -> str:
        """Generate audio from full script text by parsing it into segments."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._sanitize_filename(episode_title)
        final_audio_path = self.output_dir / f"{filename}.mp3"

        console.print(f"📝 Processing full script ({len(script)} characters)")

        # Parse script into speaker segments
        segments = self._parse_script_into_segments(script)

        if not segments:
            console.print("⚠️  Could not parse script into segments, using standard generation")
            return self.generate_audio_from_text(script, str(final_audio_path))

        console.print(f"✅ Parsed script into {len(segments)} segments")

        # Generate audio for each segment
        segment_files = []
        for i, segment in enumerate(segments):
            console.print(f"🎤 Processing segment {i+1}/{len(segments)}: {segment['speaker']}")

            # Clean up audio cues for TTS
            text = self._clean_audio_cues(segment['text'])
            if not text.strip():
                continue

            # Get voice profile for this speaker
            voice_profile_name = self.CONVERSATION_VOICES.get(
                segment['speaker'], "default"
            )
            voice_profile = self.VOICE_PROFILES.get(
                voice_profile_name, self.VOICE_PROFILES["default"]
            )

            console.print(f"🎭 Speaker '{segment['speaker']}' → Voice '{voice_profile_name}' → Engine '{voice_profile.engine.value}'")

            # Generate segment audio
            segment_filename = f"{filename}_segment_{i:03d}_{segment['speaker']}.mp3"
            segment_path = self.output_dir / segment_filename

            try:
                console.print(f"🎤 Generating audio for: '{text[:50]}...'")
                self._generate_segment_with_voice(
                    text, str(segment_path), voice_profile
                )

                # Verify the segment was created successfully
                if os.path.exists(str(segment_path)) and os.path.getsize(str(segment_path)) > 0:
                    segment_files.append(str(segment_path))
                    console.print(f"✓ Segment {i+1} generated successfully")
                else:
                    console.print(f"[yellow]⚠️  Segment {i+1} file was not created or is empty[/yellow]")
                    continue

                # Add pause after each segment for natural conversation flow
                if segment['speaker'] in ["alex", "sam"]:
                    try:
                        pause_file = self._generate_pause(0.5)  # 0.5 second pause
                        if pause_file:  # Only add if pause generation succeeded
                            segment_files.append(pause_file)
                    except Exception as pause_error:
                        console.print(f"[yellow]⚠️  Failed to generate pause: {pause_error}[/yellow]")

            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Skipping segment {i+1} due to error: {e}[/yellow]"
                )
                continue

        if not segment_files:
            console.print("⚠️  No segments generated from script, using standard generation")
            return self.generate_audio_from_text(script, str(final_audio_path))

        # Combine all segments into final audio
        console.print(f"🔗 Combining {len(segment_files)} audio segments...")
        self._combine_audio_files(segment_files, str(final_audio_path))

        # Clean up temporary segment files
        console.print(f"🧹 Cleaning up {len(segment_files)} temporary segment files...")
        for segment_file in segment_files:
            try:
                if os.path.exists(segment_file):
                    # Clean up segment files and related files
                    if "segment_" in segment_file or "pause_" in segment_file:
                        os.unlink(segment_file)
                        console.print(f"✅ Removed: {os.path.basename(segment_file)}")

                    # Also clean up any related WAV files
                    wav_equivalent = segment_file.replace('.mp3', '.wav')
                    if os.path.exists(wav_equivalent) and "segment_" in wav_equivalent:
                        os.unlink(wav_equivalent)
                        console.print(f"✅ Removed WAV: {os.path.basename(wav_equivalent)}")

                    # Clean up any remaining temporary WAV files in output directory
                    import glob
                    remaining_wavs = glob.glob(str(self.output_dir / "*.wav"))
                    for wav_file in remaining_wavs:
                        if "temp" in wav_file or "pause" in wav_file:
                            try:
                                os.unlink(wav_file)
                                console.print(f"✅ Cleaned up temp WAV: {os.path.basename(wav_file)}")
                            except:
                                pass
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not remove {segment_file}: {e}[/yellow]")

        console.print(f"🎵 Script-based audio generated: [green]{final_audio_path}[/green]")

        # Validate the final combined audio
        if self._validate_audio_file(str(final_audio_path)):
            console.print("✓ Final script-based audio validation passed")
        else:
            console.print("[yellow]⚠️  Final script-based audio validation failed[/yellow]")

        return str(final_audio_path)

    def _parse_script_into_segments(self, script: str) -> List[dict]:
        """Parse a script text into speaker segments."""
        segments = []
        current_speaker = "narrator"

        lines = script.split('\n')
        current_text = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for speaker labels (ALEX:, SAM:, NARRATOR:)
            speaker_match = re.match(r'^(ALEX|SAM|NARRATOR):\s*(.*)', line, re.IGNORECASE)
            if speaker_match:
                # Save previous segment if we have content
                if current_text:
                    segments.append({
                        'speaker': current_speaker.lower(),
                        'text': ' '.join(current_text)
                    })
                    current_text = []

                # Start new segment
                speaker_name = speaker_match.group(1).lower()
                current_speaker = speaker_name
                remaining_text = speaker_match.group(2).strip()
                if remaining_text:
                    current_text.append(remaining_text)
            else:
                # Add to current segment
                current_text.append(line)

        # Add final segment
        if current_text:
            segments.append({
                'speaker': current_speaker.lower(),
                'text': ' '.join(current_text)
            })

        # If no speaker labels found, create segments by splitting content
        if not segments or len(segments) == 1:
            console.print("🔄 No speaker labels found, creating alternating Alex/Sam segments")
            text = script
            # Remove any existing labels
            text = re.sub(r'^(ALEX|SAM|NARRATOR):\s*', '', text, flags=re.MULTILINE | re.IGNORECASE)

            # Split into sentences and alternate speakers
            sentences = re.split(r'(?<=[.!?])\s+', text)
            segments = []
            for i, sentence in enumerate(sentences):
                if sentence.strip():
                    speaker = "alex" if i % 2 == 0 else "sam"
                    segments.append({
                        'speaker': speaker,
                        'text': sentence.strip()
                    })

        return segments

    def generate_audio_from_text(self, text: str, output_path: str) -> str:
        """Generate audio from plain text using the default voice."""
        try:
            cleaned_text = self._clean_audio_cues(text)
            console.print(f"🎤 Generating audio from text ({len(cleaned_text)} characters)")

            # Use the primary engine from voice profile
            if self.voice_profile.engine == TTSEngine.PIPER:
                self._generate_with_piper(cleaned_text, output_path)
            elif self.voice_profile.engine == TTSEngine.ESPEAK:
                self._generate_with_espeak(cleaned_text, output_path)
            elif self.voice_profile.engine == TTSEngine.PYTTSX3:
                self._generate_with_pyttsx3(cleaned_text, output_path)
            elif self.voice_profile.engine == TTSEngine.GTTS:
                self._generate_with_gtts(cleaned_text, output_path)
            elif self.voice_profile.engine == TTSEngine.MACOS_SAY:
                self._generate_with_say(cleaned_text, output_path)
            else:
                self._generate_with_pyttsx3(cleaned_text, output_path)  # fallback

            return output_path
        except Exception as e:
            console.print(f"[red]❌ Text-to-audio generation failed: {e}[/red]")
            raise

    def _generate_segment_with_voice(
        self, text: str, output_path: str, voice_profile: VoiceProfile
    ) -> None:
        """Generate audio segment with specific voice profile."""
        # Temporarily switch to the segment's voice profile
        original_voice = self.voice_profile
        self.voice_profile = voice_profile

        try:
            if voice_profile.engine == TTSEngine.PIPER:
                self._generate_with_piper(text, output_path)
            elif voice_profile.engine == TTSEngine.ESPEAK:
                self._generate_with_espeak(text, output_path)
            elif voice_profile.engine == TTSEngine.PYTTSX3:
                self._generate_with_pyttsx3(text, output_path)
            elif voice_profile.engine == TTSEngine.GTTS:
                self._generate_with_gtts(text, output_path)
            elif voice_profile.engine == TTSEngine.MACOS_SAY:
                self._generate_with_say(text, output_path)
            else:
                raise ValueError(f"Unsupported TTS engine: {voice_profile.engine}")
        finally:
            # Restore original voice profile
            self.voice_profile = original_voice

    def _clean_audio_cues(self, text: str) -> str:
        """Remove audio cues and formatting that shouldn't be spoken."""
        if not text:
            return ""

        # Remove audio cues in brackets (e.g., [BOTH LAUGH], [PAUSE], [EXCITED])
        text = re.sub(r"\[.*?\]", "", text)

        # Remove emphasis markers (*word* becomes word) - handle various patterns
        text = re.sub(r"\*([^*]+)\*", r"\1", text)  # *word*
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # **word**

        # Remove any remaining standalone asterisks (including multiple)
        text = re.sub(r"\*+", "", text)

        # Remove interruption markers (-- becomes pause)
        text = text.replace("--", " ")

        # Remove speaker labels if they somehow got through
        text = re.sub(r"^(ALEX|SAM|NARRATOR):\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n(ALEX|SAM|NARRATOR):\s*", "\n", text, flags=re.IGNORECASE)

        # Remove trailing dots that indicate pauses (... becomes natural pause)
        text = re.sub(r"\.{3,}", ".", text)

        # Clean up markdown-style formatting
        text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)  # _word_ or __word__
        text = re.sub(r"`([^`]+)`", r"\1", text)  # `code`

        # Remove problematic characters that might cause TTS issues
        text = re.sub(r"[#@$%^&+=|\\/<>{}]", "", text)  # Remove special chars

        # Remove excessive punctuation
        text = re.sub(r"[!]{2,}", "!", text)  # !! becomes !
        text = re.sub(r"[?]{2,}", "?", text)  # ?? becomes ?
        text = re.sub(r"[,]{2,}", ",", text)  # ,, becomes ,

        # Clean up extra whitespace and normalize
        text = re.sub(r"\s+", " ", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Safety check: if text is empty after cleaning, return a safe default
        if not text:
            return "Content not available for audio generation."

        return text

    def _generate_pause(self, duration_seconds: float) -> str:
        """Generate a silent pause audio file."""
        try:
            # Simple approach: create a very quiet audio file
            pause_text = " "  # Single space creates minimal audio
            pause_filename = f"pause_{duration_seconds:.1f}s.mp3"
            pause_path = self.output_dir / pause_filename

            # Generate very short, quiet audio using default engine
            self._generate_with_pyttsx3(pause_text, str(pause_path))
            return str(pause_path)

        except Exception as e:
            console.print(f"[yellow]⚠️  Could not generate pause: {e}[/yellow]")
            return ""

    def _generate_with_pyttsx3(self, text: str, output_path: str) -> None:
        """Generate audio using pyttsx3 (cross-platform) with maximum reliability."""
        try:
            import pyttsx3
            import time
            import threading

            # Create a new engine instance for this generation (more reliable)
            engine = pyttsx3.init()

            # Set voice if specified
            if self.voice_profile.voice_id:
                voices = engine.getProperty("voices")
                if voices:  # Check if voices is not None
                    for voice in voices:
                        if voice and self.voice_profile.voice_id in voice.id:
                            engine.setProperty("voice", voice.id)
                            console.print(f"🎤 Using voice: {voice.name}")
                            break

            # Set properties with validation
            rate = engine.getProperty("rate")
            if rate:
                new_rate = int(rate * self.voice_profile.speed * self.voice_speed)
                # Clamp rate to reasonable bounds
                new_rate = max(50, min(500, new_rate))
                engine.setProperty("rate", new_rate)
                console.print(f"🎤 Speech rate: {new_rate} WPM")

            volume = engine.getProperty("volume")
            if volume is not None:
                new_volume = min(1.0, volume * 1.1)
                engine.setProperty("volume", new_volume)

            # Use WAV format for reliability (will convert to MP3 later if needed)
            if output_path.endswith(".mp3"):
                temp_wav_path = output_path.replace(".mp3", ".wav")
            else:
                temp_wav_path = output_path

            # Ensure directory exists
            os.makedirs(os.path.dirname(temp_wav_path), exist_ok=True)

            console.print(f"🎤 Generating {len(text.split())} words with pyttsx3...")

            # Use a more reliable approach with threading and timeout
            generation_complete = threading.Event()
            generation_error = None

            def generate_audio():
                nonlocal generation_error
                try:
                    engine.save_to_file(text, temp_wav_path)
                    engine.runAndWait()
                    generation_complete.set()
                except Exception as e:
                    generation_error = e
                    generation_complete.set()

            # Start generation in separate thread
            thread = threading.Thread(target=generate_audio)
            thread.daemon = True
            thread.start()

            # Wait for completion with timeout
            if not generation_complete.wait(timeout=120):  # 2 minute timeout
                raise RuntimeError("pyttsx3 generation timed out")

            if generation_error:
                raise generation_error

            # Additional wait for file system sync
            time.sleep(1.0)

            # Force cleanup
            try:
                engine.stop()
                del engine
            except:
                pass

            # Verify the WAV file was created
            retry_count = 0
            while retry_count < 5:
                if os.path.exists(temp_wav_path) and os.path.getsize(temp_wav_path) > 0:
                    break
                time.sleep(0.5)
                retry_count += 1

            if not os.path.exists(temp_wav_path):
                raise RuntimeError(f"pyttsx3 failed to create audio file: {temp_wav_path}")

            file_size = os.path.getsize(temp_wav_path)
            if file_size == 0:
                raise RuntimeError(f"pyttsx3 created empty audio file: {temp_wav_path}")

            console.print(f"✓ WAV file created: {file_size} bytes")

            # For better compatibility, output WAV files instead of MP3
            if output_path.endswith(".mp3") and temp_wav_path != output_path:
                console.print(f"🔄 Converting to playable format...")

                # Check if it's AIFF and convert to proper WAV
                if os.path.exists(temp_wav_path):
                    with open(temp_wav_path, 'rb') as f:
                        header = f.read(12)

                    if b'FORM' in header and (b'AIFF' in header or b'AIFC' in header):
                        # AIFF file - convert to proper MP3 format only
                        console.print(f"🔄 Converting AIFF to MP3: {output_path}")

                        # Convert AIFF to MP3 using robust conversion
                        self._convert_to_mp3_robust(temp_wav_path, output_path)
                        console.print(f"✅ Audio converted from AIFF to MP3")
                    else:
                        # Regular conversion for non-AIFF files
                        self._convert_to_mp3_robust(temp_wav_path, output_path)

                # Clean up temporary file
                if os.path.exists(temp_wav_path) and temp_wav_path != output_path.replace('.mp3', '.wav'):
                    os.unlink(temp_wav_path)

        except ImportError:
            raise RuntimeError(
                "pyttsx3 not available. Install with: pip install pyttsx3"
            )
        except Exception as e:
            raise RuntimeError(f"pyttsx3 generation failed: {e}")

    def _generate_with_espeak(self, text: str, output_path: str) -> None:
        """Generate audio using eSpeak (lightweight, fully offline)."""
        try:
            # Calculate speed in words per minute (eSpeak format)
            # eSpeak default is ~175 wpm, we'll scale based on our speed setting
            speed_wpm = int(175 * self.voice_profile.speed * self.voice_speed)

            # Get voice setting
            voice = self.voice_profile.voice_id or "en"

            # Prepare output path - eSpeak can output WAV directly
            if output_path.endswith('.mp3'):
                temp_wav = output_path.replace('.mp3', '.wav')
            else:
                temp_wav = output_path

            console.print(f"🎤 eSpeak: voice={voice}, speed={speed_wpm}wpm")

            # Build eSpeak command
            command = [
                "espeak",
                "-v", voice,
                "-s", str(speed_wpm),
                "-w", temp_wav,  # Write to WAV file
                text
            ]

            # Run eSpeak
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                raise RuntimeError(f"eSpeak command failed: {result.stderr}")

            # Verify WAV file was created
            if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) == 0:
                raise RuntimeError(f"eSpeak failed to create audio file: {temp_wav}")

            # Convert to MP3 if needed
            if output_path.endswith('.mp3') and temp_wav != output_path:
                self._convert_to_mp3(temp_wav, output_path)
                if os.path.exists(temp_wav):
                    os.unlink(temp_wav)

            file_size = os.path.getsize(output_path)
            console.print(f"✓ eSpeak generated: {file_size} bytes")

        except FileNotFoundError:
            raise RuntimeError(
                "eSpeak not found. Install with: sudo apt-get install espeak (Linux) or brew install espeak (macOS)"
            )
        except Exception as e:
            raise RuntimeError(f"eSpeak generation failed: {e}")

    def _generate_with_piper(self, text: str, output_path: str) -> None:
        """Generate audio using Piper TTS (high-quality offline neural TTS)."""
        try:
            import tempfile
            import json

            # Voice model file (downloaded once and cached)
            voice_model = self.voice_profile.voice_id or "en_US-amy-medium"

            # Piper models directory - create if doesn't exist
            models_dir = self.output_dir.parent / "piper_models"
            models_dir.mkdir(exist_ok=True)

            model_file = models_dir / f"{voice_model}.onnx"
            config_file = models_dir / f"{voice_model}.onnx.json"

            # Download model if not exists (this is a one-time setup)
            if not model_file.exists() or not config_file.exists():
                console.print(f"📥 Downloading Piper model {voice_model} (one-time setup)...")
                self._download_piper_model(voice_model, models_dir)

            # Calculate speaking rate
            speaking_rate = self.voice_profile.speed * self.voice_speed

            console.print(f"🎤 Piper: model={voice_model}, rate={speaking_rate:.2f}")

            # Prepare output - Piper outputs WAV by default
            if output_path.endswith('.mp3'):
                temp_wav = output_path.replace('.mp3', '.wav')
            else:
                temp_wav = output_path

            # Run Piper TTS
            command = [
                "piper",
                "--model", str(model_file),
                "--config", str(config_file),
                "--output_file", temp_wav,
                "--speaking_rate", str(speaking_rate)
            ]

            # Use subprocess with stdin for text input
            result = subprocess.run(
                command,
                input=text,
                text=True,
                capture_output=True,
                timeout=180
            )

            if result.returncode != 0:
                raise RuntimeError(f"Piper command failed: {result.stderr}")

            # Verify WAV file was created
            if not os.path.exists(temp_wav) or os.path.getsize(temp_wav) == 0:
                raise RuntimeError(f"Piper failed to create audio file: {temp_wav}")

            # Convert to MP3 if needed
            if output_path.endswith('.mp3') and temp_wav != output_path:
                self._convert_to_mp3(temp_wav, output_path)
                if os.path.exists(temp_wav):
                    os.unlink(temp_wav)

            file_size = os.path.getsize(output_path)
            console.print(f"✓ Piper generated: {file_size} bytes")

        except FileNotFoundError:
            raise RuntimeError(
                "Piper TTS not found. Install with: pip install piper-tts"
            )
        except Exception as e:
            raise RuntimeError(f"Piper generation failed: {e}")

    def _download_piper_model(self, voice_model: str, models_dir) -> None:
        """Download Piper voice model (one-time setup)."""
        # For security and offline requirements, we'll skip automatic downloading
        # and provide instructions for manual setup
        model_file = models_dir / f"{voice_model}.onnx"
        config_file = models_dir / f"{voice_model}.onnx.json"

        console.print(f"[dim]⚠️  Piper models not found - falling back to next TTS engine[/dim]")
        console.print(f"[dim]To enable Piper: Download models from https://github.com/rhasspy/piper/releases[/dim]")

        raise ImportError(f"Piper models not available - will fallback to other TTS engines")

    def _generate_with_gtts(self, text: str, output_path: str) -> None:
        """Generate audio using Google Text-to-Speech."""
        try:
            from gtts import gTTS

            # Split text into chunks if too long (gTTS has limits)
            max_chars = 5000
            if len(text) > max_chars:
                chunks = [
                    text[i : i + max_chars] for i in range(0, len(text), max_chars)
                ]
                audio_chunks = []

                for i, chunk in enumerate(chunks):
                    console.print(f"🔊 Processing chunk {i+1}/{len(chunks)}")
                    tts = gTTS(text=chunk, lang=self.voice_profile.language, slow=False)

                    # Save chunk to temporary file
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".mp3"
                    ) as tmp_file:
                        tts.save(tmp_file.name)
                        audio_chunks.append(tmp_file.name)

                # Combine chunks
                self._combine_audio_files(audio_chunks, output_path)

                # Clean up temporary files
                for chunk_file in audio_chunks:
                    os.unlink(chunk_file)
            else:
                tts = gTTS(text=text, lang=self.voice_profile.language, slow=False)
                tts.save(output_path)

        except ImportError:
            raise RuntimeError("gTTS not available. Install with: pip install gtts")
        except Exception as e:
            raise RuntimeError(f"gTTS generation failed: {e}")

    def _generate_with_say(self, text: str, output_path: str) -> None:
        """Generate audio using macOS 'say' command (improved)."""
        try:
            rate = int(self.voice_profile.speed * self.voice_speed * 200)
            voice = self.voice_profile.voice_id or "Alex"

            # Use AIFF format first, then convert
            temp_path = output_path.replace(".mp3", ".aiff")

            command = ["say", "-v", voice, "-r", str(rate), "-o", temp_path, text]

            result = subprocess.run(
                command, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                raise RuntimeError(f"say command failed: {result.stderr}")

            # Convert AIFF to MP3 using robust conversion
            self._convert_to_mp3_robust(temp_path, output_path)

            # Clean up temporary AIFF file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        except FileNotFoundError:
            raise RuntimeError("'say' command not found. This feature requires macOS.")
        except Exception as e:
            raise RuntimeError(f"macOS TTS generation failed: {e}")

    def _convert_to_mp3(self, input_path: str, output_path: str) -> None:
        """Convert audio file to MP3 format with enhanced reliability."""
        # Check if input file exists
        if not os.path.exists(input_path):
            raise RuntimeError(f"Input file does not exist: {input_path}")

        # If input is already MP3 and same path, no conversion needed
        if input_path == output_path and input_path.endswith(".mp3"):
            return

        # Get input file info for debugging
        input_size = os.path.getsize(input_path)
        console.print(f"🔍 Converting {input_path} ({input_size} bytes)")

        try:
            # Try using ffmpeg first with comprehensive settings to prevent truncation
            console.print(f"🔄 Converting {input_path} to MP3 using ffmpeg...")

            # Use more comprehensive ffmpeg settings to ensure full conversion
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", input_path,
                    "-codec:a", "libmp3lame",
                    "-b:a", "192k",  # Higher bitrate for better quality
                    "-ar", "44100",  # Standard sample rate
                    "-ac", "2",  # Stereo
                    "-f", "mp3",  # Force MP3 format
                    "-write_xing", "0",  # Disable Xing header that can cause issues
                    "-id3v2_version", "3",  # Use ID3v2.3 for better compatibility
                    "-map_metadata", "-1",  # Remove metadata that might cause issues
                    "-avoid_negative_ts", "make_zero",  # Fix potential timestamp issues
                    "-fflags", "+genpts",  # Generate presentation timestamps
                    "-max_muxing_queue_size", "1024",  # Prevent buffer issues
                    "-y",  # Overwrite output file
                    output_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,  # Longer timeout for complex conversions
            )

            if result.returncode == 0:
                # Verify the output file was created properly
                if os.path.exists(output_path):
                    output_size = os.path.getsize(output_path)
                    console.print(f"✓ Successfully converted to MP3: {output_path} ({output_size} bytes)")

                    # Basic sanity check - MP3 should be smaller but not dramatically so
                    if output_size == 0:
                        raise RuntimeError("ffmpeg created empty MP3 file")
                    elif output_size < (input_size * 0.1):  # Less than 10% of original seems wrong
                        console.print(f"[yellow]⚠️  MP3 file seems unusually small ({output_size} vs {input_size} input)[/yellow]")

                    return
                else:
                    raise RuntimeError("ffmpeg did not create output file")
            else:
                console.print(f"[yellow]⚠️  ffmpeg conversion failed: {result.stderr}[/yellow]")

        except FileNotFoundError:
            console.print("[yellow]⚠️  ffmpeg not found, trying alternative approach[/yellow]")
        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠️  ffmpeg conversion timed out, trying alternative approach[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  ffmpeg conversion error: {e}, trying alternative approach[/yellow]")

        # Try a simpler ffmpeg approach
        try:
            console.print("🔄 Trying simplified ffmpeg conversion...")
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", input_path,
                    "-codec:a", "mp3",
                    "-y",
                    output_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                console.print(f"✓ Simplified conversion successful: {output_path}")
                return
        except:
            pass

        # Fallback: just copy if already compatible or if all conversions failed
        if input_path != output_path:
            import shutil
            console.print(f"📋 Copying {input_path} to {output_path} as fallback")
            shutil.copy2(input_path, output_path)

            # If we copied a WAV as MP3, warn the user
            if input_path.endswith('.wav') and output_path.endswith('.mp3'):
                console.print("[yellow]⚠️  Warning: Copied WAV file as MP3 - may have compatibility issues[/yellow]")

    def _convert_to_mp3_robust(self, input_path: str, output_path: str) -> None:
        """Ultra-robust MP3 conversion with multiple fallback methods."""
        if not os.path.exists(input_path):
            raise RuntimeError(f"Input file does not exist: {input_path}")

        input_size = os.path.getsize(input_path)
        console.print(f"🔍 Converting {input_path} ({input_size} bytes) to MP3")

        # Method 1: Try ffmpeg with simple settings
        try:
            result = subprocess.run([
                "ffmpeg", "-i", input_path, "-codec:a", "mp3",
                "-b:a", "128k", "-y", output_path
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                console.print(f"✅ ffmpeg conversion successful")
                return
        except:
            pass

        # Method 2: Convert AIFF to WAV using Python built-in modules (most reliable)
        try:
            import aifc
            import wave

            with open(input_path, 'rb') as f:
                header = f.read(12)

            if b'FORM' in header and (b'AIFF' in header or b'AIFC' in header):
                console.print("🔄 Converting AIFF to WAV using Python audio modules")

                # Read AIFF file
                with aifc.open(input_path, 'rb') as aiff_file:
                    frames = aiff_file.readframes(aiff_file.getnframes())
                    sample_rate = aiff_file.getframerate()
                    channels = aiff_file.getnchannels()
                    sample_width = aiff_file.getsampwidth()

                # Write as WAV
                wav_output = output_path.replace('.mp3', '.wav') if output_path.endswith('.mp3') else output_path

                with wave.open(wav_output, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(sample_width)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(frames)

                # Also copy as MP3 for filename compatibility
                if wav_output != output_path:
                    import shutil
                    shutil.copy2(wav_output, output_path)

                console.print(f"✅ AIFF successfully converted to WAV format")
                return
        except Exception as e:
            console.print(f"⚠️  AIFF to WAV conversion failed: {e}")
            pass

        # Method 3: Try lame encoder directly
        try:
            result = subprocess.run([
                "lame", "-b", "128", input_path, output_path
            ], capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                console.print(f"✅ lame conversion successful")
                return
        except:
            pass

        # Method 4: Use pydub if available (try multiple formats)
        try:
            from pydub import AudioSegment

            # Detect file format from header
            with open(input_path, 'rb') as f:
                header = f.read(12)

            # Try different format loaders based on file header
            audio = None
            if b'FORM' in header and (b'AIFF' in header or b'AIFC' in header):
                console.print("🎵 Detected AIFF/AIFC format")
                audio = AudioSegment.from_file(input_path, format="aiff")
            elif b'RIFF' in header and b'WAVE' in header:
                console.print("🎵 Detected WAV format")
                audio = AudioSegment.from_wav(input_path)
            else:
                # Try generic file loader
                console.print("🎵 Trying generic audio format detection")
                audio = AudioSegment.from_file(input_path)

            if audio:
                audio.export(output_path, format="mp3", bitrate="128k")
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    console.print(f"✅ pydub conversion successful")
                    return
        except Exception as e:
            console.print(f"⚠️  pydub conversion failed: {e}")
            pass

        # Method 5: Try Python built-in audio modules
        try:
            import wave
            import aifc
            import struct

            console.print("🔧 Trying Python built-in audio conversion")

            # Detect format and read audio data
            audio_data = None
            sample_rate = None

            with open(input_path, 'rb') as f:
                header = f.read(12)
                f.seek(0)

                if b'FORM' in header and (b'AIFF' in header or b'AIFC' in header):
                    # Read AIFF file
                    with aifc.open(input_path, 'rb') as aiff_file:
                        sample_rate = aiff_file.getframerate()
                        frames = aiff_file.getnframes()
                        audio_data = aiff_file.readframes(frames)
                        sample_width = aiff_file.getsampwidth()
                        channels = aiff_file.getnchannels()
                elif b'RIFF' in header and b'WAVE' in header:
                    # Read WAV file
                    with wave.open(input_path, 'rb') as wav_file:
                        sample_rate = wav_file.getframerate()
                        frames = wav_file.getnframes()
                        audio_data = wav_file.readframes(frames)
                        sample_width = wav_file.getsampwidth()
                        channels = wav_file.getnchannels()

            if audio_data and sample_rate:
                # Convert to WAV first, then copy as MP3 fallback
                temp_wav = output_path.replace('.mp3', '_temp.wav')

                with wave.open(temp_wav, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(sample_width)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data)

                # Copy the properly formatted WAV as MP3
                import shutil
                shutil.copy2(temp_wav, output_path)

                # Clean up temp file
                if os.path.exists(temp_wav):
                    os.unlink(temp_wav)

                console.print("✅ Python built-in conversion successful")
                return

        except Exception as e:
            console.print(f"⚠️  Python built-in conversion failed: {e}")
            pass

        # Method 6: For AIFF files, create a simple WAV copy instead of MP3
        try:
            with open(input_path, 'rb') as f:
                header = f.read(12)

            if b'FORM' in header and (b'AIFF' in header or b'AIFC' in header):
                # For AIFF files, output as WAV instead of MP3 for better compatibility
                wav_output = output_path.replace('.mp3', '.wav')
                console.print(f"🔄 Converting AIFF to WAV format: {wav_output}")

                import shutil
                shutil.copy2(input_path, wav_output)

                # Also create a symlink or copy as MP3 for compatibility
                if wav_output != output_path:
                    shutil.copy2(wav_output, output_path)
                    console.print("✅ AIFF converted to WAV format (more compatible)")
                return
        except Exception as e:
            console.print(f"⚠️  AIFF to WAV conversion failed: {e}")

        # Method 7: Direct copy as last resort (may cause compatibility issues)
        console.print("[yellow]⚠️  All conversion methods failed, copying original as MP3[/yellow]")
        console.print("[yellow]   Note: This may create unplayable files. Install ffmpeg for proper conversion.[/yellow]")
        import shutil
        shutil.copy2(input_path, output_path)

    def _combine_audio_files(self, file_paths: List[str], output_path: str) -> None:
        """Combine multiple audio files into one with improved settings."""
        try:
            # Create a temporary file list for ffmpeg concat
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for file_path in file_paths:
                    f.write(f"file '{file_path}'\n")
                concat_file = f.name

            # Use ffmpeg concat demuxer for better results
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_file,
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",  # Higher bitrate
                    "-ar",
                    "44100",  # Standard sample rate
                    "-ac",
                    "2",  # Stereo
                    "-map_metadata",
                    "-1",  # Remove metadata
                    "-y",
                    output_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,  # Longer timeout for combining
            )

            # Clean up temp file
            os.unlink(concat_file)

            if result.returncode == 0:
                console.print(f"✓ Successfully combined {len(file_paths)} audio files")
                return
            else:
                console.print(f"[yellow]⚠️  ffmpeg concat failed: {result.stderr}[/yellow]")

        except FileNotFoundError:
            console.print("[yellow]⚠️  ffmpeg not found, using fallback method[/yellow]")
            console.print("[dim]💡 To install ffmpeg:[/dim]")
            console.print("[dim]   macOS: brew install ffmpeg[/dim]")
            console.print("[dim]   Ubuntu/Debian: sudo apt install ffmpeg[/dim]")
            console.print("[dim]   Windows: choco install ffmpeg[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️  ffmpeg concat error: {e}[/yellow]")

        # CRITICAL: Install pydub if not available - it's essential for audio combination
        try:
            from pydub import AudioSegment
        except ImportError:
            console.print("🚨 CRITICAL: pydub is required for audio combination without ffmpeg")
            console.print("📦 Installing pydub automatically...")
            try:
                import subprocess
                import sys
                result = subprocess.run([sys.executable, "-m", "pip", "install", "pydub"],
                                      capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    console.print("✅ pydub installed successfully, retrying...")
                    from pydub import AudioSegment
                else:
                    raise RuntimeError(f"Failed to install pydub: {result.stderr}")
            except Exception as install_error:
                console.print(f"❌ Could not install pydub: {install_error}")
                console.print("🔧 Please install manually: pip install pydub")
                raise RuntimeError("pydub is required for audio combination. Install with: pip install pydub")

        # Method 1: Professional audio combination using pydub
        console.print("🎵 Using pydub for professional audio combination...")
        try:
            combined_audio = AudioSegment.empty()
            successful_segments = 0

            for file_path in file_paths:
                try:
                    if not os.path.exists(file_path):
                        console.print(f"[yellow]⚠️  File not found: {file_path}[/yellow]")
                        continue

                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        console.print(f"[yellow]⚠️  Empty file: {file_path}[/yellow]")
                        continue

                    console.print(f"📁 Loading {os.path.basename(file_path)} ({file_size} bytes)...")

                    # Try loading as different formats
                    audio_segment = None

                    # First try as MP3
                    try:
                        audio_segment = AudioSegment.from_mp3(file_path)
                        console.print(f"✅ Loaded as MP3: {len(audio_segment)}ms")
                    except:
                        # Try as generic audio file
                        try:
                            audio_segment = AudioSegment.from_file(file_path)
                            console.print(f"✅ Loaded as audio: {len(audio_segment)}ms")
                        except Exception as load_error:
                            console.print(f"[yellow]⚠️  Could not load {file_path}: {load_error}[/yellow]")
                            continue

                    if audio_segment and len(audio_segment) > 0:
                        combined_audio += audio_segment
                        successful_segments += 1
                        console.print(f"🔗 Added to combination (total: {len(combined_audio)}ms)")
                    else:
                        console.print(f"[yellow]⚠️  Empty audio segment: {file_path}[/yellow]")

                except Exception as segment_error:
                    console.print(f"[yellow]⚠️  Error processing {file_path}: {segment_error}[/yellow]")
                    continue

            if successful_segments > 0 and len(combined_audio) > 0:
                console.print(f"🎵 Exporting combined audio ({len(combined_audio)}ms from {successful_segments} segments)...")

                # Export with high quality settings
                combined_audio.export(
                    output_path,
                    format="mp3",
                    bitrate="192k",
                    parameters=["-ar", "44100", "-ac", "2"]
                )

                # Verify the output
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    output_size = os.path.getsize(output_path)
                    console.print(f"✅ Successfully combined {successful_segments} audio files using pydub ({output_size} bytes)")
                    return
                else:
                    raise RuntimeError("pydub export created empty file")
            else:
                raise RuntimeError(f"No valid audio segments found (tried {len(file_paths)} files)")

        except Exception as pydub_error:
            console.print(f"❌ pydub combination failed: {pydub_error}")

            # Method 2: Fallback to WAV combination if possible
            console.print("🔄 Trying WAV-based combination as fallback...")
            try:
                # Convert all files to WAV first, then combine
                import tempfile
                wav_files = []

                for file_path in file_paths:
                    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                        continue

                    try:
                        # Load and convert to WAV
                        audio = AudioSegment.from_file(file_path)
                        if len(audio) > 0:
                            wav_temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                            wav_temp.close()
                            audio.export(wav_temp.name, format="wav")
                            wav_files.append(wav_temp.name)
                            console.print(f"✅ Converted {os.path.basename(file_path)} to WAV")
                    except Exception as conv_error:
                        console.print(f"[yellow]⚠️  Could not convert {file_path}: {conv_error}[/yellow]")
                        continue

                if wav_files:
                    # Combine WAV files
                    combined = AudioSegment.empty()
                    for wav_file in wav_files:
                        try:
                            wav_audio = AudioSegment.from_wav(wav_file)
                            combined += wav_audio
                        except Exception as wav_error:
                            console.print(f"[yellow]⚠️  Error combining WAV: {wav_error}[/yellow]")

                    if len(combined) > 0:
                        combined.export(output_path, format="mp3", bitrate="192k")
                        console.print(f"✅ Successfully combined using WAV fallback method")

                        # Clean up temporary WAV files
                        for wav_file in wav_files:
                            try:
                                os.unlink(wav_file)
                            except:
                                pass
                        return

            except Exception as wav_error:
                console.print(f"[yellow]⚠️  WAV fallback failed: {wav_error}[/yellow]")

            # Method 3: Create a simple audio file that references the segments
            console.print("🔄 Creating playlist-style output as final fallback...")
            try:
                # If we can't combine, at least use the first valid audio file
                for file_path in file_paths:
                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                        import shutil
                        shutil.copy2(file_path, output_path)
                        console.print(f"📋 Using first valid audio file: {os.path.basename(file_path)}")
                        console.print("[yellow]⚠️  Note: Only first segment used - install ffmpeg for full combination[/yellow]")
                        return

            except Exception as copy_error:
                console.print(f"[yellow]⚠️  Copy fallback failed: {copy_error}[/yellow]")

            raise RuntimeError("All audio combination methods failed. Please install ffmpeg or ensure pydub is working correctly.")

    def _validate_audio_file(self, file_path: str, expected_text: str = "") -> bool:
        """Validate that an audio file is complete and playable."""
        try:
            if not os.path.exists(file_path):
                console.print(f"[red]❌ Audio file does not exist: {file_path}[/red]")
                return False

            file_size = os.path.getsize(file_path)
            if file_size == 0:
                console.print(f"[red]❌ Audio file is empty: {file_path}[/red]")
                return False

            # Try to get audio duration using ffmpeg/ffprobe if available
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "csv=p=0", file_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0 and result.stdout.strip():
                    duration = float(result.stdout.strip())
                    console.print(f"✓ Audio duration: {duration:.2f} seconds")

                    # If we have expected text, check if duration makes sense
                    if expected_text:
                        word_count = len(expected_text.split())
                        expected_duration = word_count / 2.5  # ~2.5 words per second

                        if duration < (expected_duration * 0.5):  # Less than 50% of expected
                            console.print(f"[yellow]⚠️  Audio seems truncated: {duration:.2f}s vs expected ~{expected_duration:.2f}s[/yellow]")
                            return False
                        elif duration > (expected_duration * 3):  # More than 300% of expected
                            console.print(f"[yellow]⚠️  Audio seems unexpectedly long: {duration:.2f}s vs expected ~{expected_duration:.2f}s[/yellow]")

                    return True

            except FileNotFoundError:
                # ffprobe not available, use basic file size check
                pass
            except Exception as e:
                console.print(f"[yellow]⚠️  Could not probe audio file: {e}[/yellow]")

            # Basic file size validation when ffprobe is not available
            if expected_text:
                word_count = len(expected_text.split())
                # Very rough estimate: ~1KB per word for MP3
                min_expected_size = word_count * 1000

                if file_size < min_expected_size * 0.3:  # Less than 30% of expected
                    console.print(f"[yellow]⚠️  Audio file seems small: {file_size} bytes for {word_count} words[/yellow]")
                    return False

            console.print(f"✓ Audio file basic validation passed: {file_size} bytes")
            return True

        except Exception as e:
            console.print(f"[red]❌ Audio validation failed: {e}[/red]")
            return False

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        sanitized = re.sub(r"[^\w\s-]", "", filename)
        sanitized = re.sub(r"\s+", "-", sanitized)
        return sanitized.lower()[:50]

    def list_available_voices(self) -> Dict[str, VoiceProfile]:
        """List all available voice profiles."""
        return self.VOICE_PROFILES.copy()

    def generate_batch(
        self,
        episodes: List[PodcastEpisode],
        format_script: Callable[[PodcastEpisode], str],
    ) -> List[PodcastEpisode]:
        """Generate audio for multiple episodes."""
        results: List[PodcastEpisode] = []

        console.print(
            f"🎭 Using voice profile: [bold]{self.voice_profile.name}[/bold] ({self.voice_profile.engine.value})"
        )

        for episode in episodes:
            try:
                console.print(f"🎤 Generating audio for: [bold]{episode.title}[/bold]")
                script = format_script(episode)

                # Debug: show episode conversation status
                segment_count = len(episode.conversation_segments) if episode.conversation_segments else 0
                console.print(f"🔍 Episode has {segment_count} conversation segments")

                # Use conversation audio generation if available
                if episode.conversation_segments:
                    console.print("🎭 Using conversational audio generation")
                    console.print(f"🎭 Segments: {[seg.speaker for seg in episode.conversation_segments[:5]]}{'...' if len(episode.conversation_segments) > 5 else ''}")
                    audio_path = self.generate_conversation_audio(episode, script)
                else:
                    console.print("📻 Using standard audio generation (NO conversation segments)")
                    audio_path = self.generate_audio(episode, script)

                updated_episode = episode.model_copy()
                updated_episode.audio_path = audio_path
                results.append(updated_episode)

            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Skipping audio generation for '{episode.title}': {e}[/yellow]"
                )
                results.append(episode)

        return results
