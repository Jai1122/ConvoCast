"""Text-to-speech generator for podcast audio."""

import io
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pygame
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
            speed=1.4,
            pitch=0.8,
        ),
        "narrator_female": VoiceProfile(
            name="Professional Female Narrator",
            engine=TTSEngine.PYTTSX3,
            voice_id=(
                "com.apple.voice.compact.en-US.Alex" if os.name == "posix" else None
            ),
            language="en",
            speed=1.35,
            pitch=1.1,
        ),
        "gtts_default": VoiceProfile(
            name="Google TTS Default",
            engine=TTSEngine.GTTS,
            language="en",
            speed=1.3,
            pitch=1.0,
        ),
        "gtts_british": VoiceProfile(
            name="Google TTS British",
            engine=TTSEngine.GTTS,
            language="en-uk",
            speed=1.3,
            pitch=1.0,
        ),
        "macos_alex": VoiceProfile(
            name="macOS Alex",
            engine=TTSEngine.MACOS_SAY,
            voice_id="Alex",
            language="en",
            speed=1.4,
            pitch=1.0,
        ),
        # Conversation-specific voices with distinct characteristics
        "alex_female": VoiceProfile(
            name="Alex - Curious Female Host",
            engine=TTSEngine.GTTS,
            language="en",  # Standard English for female voice
            speed=1.4,  # Faster, more energetic
            pitch=1.2,   # Higher pitch for female voice
        ),
        "sam_male": VoiceProfile(
            name="Sam - Knowledgeable Male Expert",
            engine=TTSEngine.MACOS_SAY,  # Use macOS say for male voice
            voice_id="Daniel",  # More professional male voice
            language="en",
            speed=1.3,   # Faster, but still thoughtful pace
            pitch=0.8,   # Lower pitch for male voice
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

        # Initialize pygame mixer for audio handling (improved settings)
        try:
            import os
            # Disable pygame's welcome message and potential audio device issues
            os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
            # Use better audio settings to prevent stopping issues
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
            pygame.mixer.init()
            # Set additional mixer settings for better playback
            pygame.mixer.set_num_channels(8)
        except Exception as e:
            console.print(f"[yellow]⚠️  Pygame mixer initialization failed: {e}[/yellow]")
            console.print("[yellow]   Audio combination features may be limited[/yellow]")

    def generate_audio(self, episode: PodcastEpisode, script: str) -> str:
        """Generate audio file for a single episode."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        filename = self._sanitize_filename(episode.title)
        audio_path = self.output_dir / f"{filename}.mp3"
        script_path = self.output_dir / f"{filename}.txt"

        # Save script file
        script_path.write_text(script, encoding="utf-8")

        try:
            console.print(
                f"🎤 Using {self.voice_profile.engine.value} engine with profile '{self.voice_profile.name}'"
            )

            # Clean the script before TTS generation to remove asterisks and formatting
            cleaned_script = self._clean_audio_cues(script)
            console.print(f"🧹 Cleaned script: {len(script)} → {len(cleaned_script)} characters")

            if self.voice_profile.engine == TTSEngine.PYTTSX3:
                self._generate_with_pyttsx3(cleaned_script, str(audio_path))
            elif self.voice_profile.engine == TTSEngine.GTTS:
                self._generate_with_gtts(cleaned_script, str(audio_path))
            elif self.voice_profile.engine == TTSEngine.MACOS_SAY:
                self._generate_with_say(cleaned_script, str(audio_path))
            else:
                raise ValueError(f"Unsupported TTS engine: {self.voice_profile.engine}")

            console.print(f"🎵 Audio generated: [green]{audio_path}[/green]")
            return str(audio_path)
        except Exception as e:
            console.print(
                f"[red]❌ Failed to generate audio for '{episode.title}': {e}[/red]"
            )
            raise

    def generate_conversation_audio(self, episode: PodcastEpisode, script: str) -> str:
        """Generate multi-speaker audio for conversational episodes."""
        if not episode.conversation_segments:
            console.print(
                "[yellow]⚠️  No conversation segments found, using standard generation[/yellow]"
            )
            return self.generate_audio(episode, script)

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

        # Clean up temporary segment files
        for segment_file in segment_files:
            if os.path.exists(segment_file) and "segment_" in segment_file:
                os.unlink(segment_file)

        console.print(
            f"🎵 Conversation audio generated: [green]{final_audio_path}[/green]"
        )
        return str(final_audio_path)

    def _generate_segment_with_voice(
        self, text: str, output_path: str, voice_profile: VoiceProfile
    ) -> None:
        """Generate audio segment with specific voice profile."""
        # Temporarily switch to the segment's voice profile
        original_voice = self.voice_profile
        self.voice_profile = voice_profile

        try:
            if voice_profile.engine == TTSEngine.PYTTSX3:
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
        """Generate audio using pyttsx3 (cross-platform)."""
        try:
            import pyttsx3

            engine = pyttsx3.init()

            # Set voice if specified
            if self.voice_profile.voice_id:
                voices = engine.getProperty("voices")
                if voices:  # Check if voices is not None
                    for voice in voices:
                        if voice and self.voice_profile.voice_id in voice.id:
                            engine.setProperty("voice", voice.id)
                            break

            # Set properties
            rate = engine.getProperty("rate")
            if rate:  # Check if rate is not None
                engine.setProperty(
                    "rate", int(rate * self.voice_profile.speed * self.voice_speed)
                )

            volume = engine.getProperty("volume")
            if volume:  # Check if volume is not None
                engine.setProperty(
                    "volume", min(1.0, volume * 1.1)
                )  # Slightly boost volume

            # pyttsx3 typically saves to WAV format, so use a temp WAV file first
            if output_path.endswith(".mp3"):
                temp_wav_path = output_path.replace(".mp3", ".wav")
            else:
                temp_wav_path = output_path

            # Save to file
            console.print(f"🎤 Generating audio with pyttsx3 to: {temp_wav_path}")
            engine.save_to_file(text, temp_wav_path)
            engine.runAndWait()

            # Verify the WAV file was created
            if not os.path.exists(temp_wav_path) or os.path.getsize(temp_wav_path) == 0:
                raise RuntimeError(f"pyttsx3 failed to create audio file: {temp_wav_path}")

            # Convert to MP3 if needed
            if output_path.endswith(".mp3") and temp_wav_path != output_path:
                console.print(f"🔄 Converting WAV to MP3: {temp_wav_path} -> {output_path}")
                self._convert_to_mp3(temp_wav_path, output_path)
                # Clean up temporary WAV file
                if os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)

        except ImportError:
            raise RuntimeError(
                "pyttsx3 not available. Install with: pip install pyttsx3"
            )
        except Exception as e:
            raise RuntimeError(f"pyttsx3 generation failed: {e}")

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

            # Convert AIFF to MP3
            self._convert_to_mp3(temp_path, output_path)

            # Clean up temporary AIFF file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        except FileNotFoundError:
            raise RuntimeError("'say' command not found. This feature requires macOS.")
        except Exception as e:
            raise RuntimeError(f"macOS TTS generation failed: {e}")

    def _convert_to_mp3(self, input_path: str, output_path: str) -> None:
        """Convert audio file to MP3 format."""
        # Check if input file exists
        if not os.path.exists(input_path):
            raise RuntimeError(f"Input file does not exist: {input_path}")

        # If input is already MP3 and same path, no conversion needed
        if input_path == output_path and input_path.endswith(".mp3"):
            return

        try:
            # Try using ffmpeg first with improved settings for better playback
            console.print(f"🔄 Converting {input_path} to MP3 using ffmpeg...")
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    input_path,
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",  # Higher bitrate for better quality
                    "-ar",
                    "44100",  # Standard sample rate
                    "-ac",
                    "2",  # Stereo
                    "-map_metadata",
                    "-1",  # Remove metadata that might cause issues
                    "-y",  # Overwrite output file
                    output_path,
                ],
                capture_output=True,
                text=True,
                timeout=60,  # Add timeout to prevent hanging
            )

            if result.returncode == 0:
                console.print(f"✓ Successfully converted to MP3: {output_path}")
                return
            else:
                console.print(f"[yellow]⚠️  ffmpeg conversion failed: {result.stderr}[/yellow]")
        except FileNotFoundError:
            console.print("[yellow]⚠️  ffmpeg not found, using fallback copy[/yellow]")
        except subprocess.TimeoutExpired:
            console.print("[yellow]⚠️  ffmpeg conversion timed out, using fallback copy[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  ffmpeg conversion error: {e}, using fallback copy[/yellow]")

        # Fallback: just copy if already compatible or if ffmpeg failed
        if input_path != output_path:
            import shutil
            console.print(f"📋 Copying {input_path} to {output_path}")
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
        except Exception as e:
            console.print(f"[yellow]⚠️  ffmpeg concat error: {e}[/yellow]")

        # Fallback: use pygame to combine with better buffering
        console.print("🔄 Using fallback audio combination method...")
        combined = io.BytesIO()
        for file_path in file_paths:
            try:
                with open(file_path, "rb") as f:
                    combined.write(f.read())
            except Exception as e:
                console.print(f"[yellow]⚠️  Error reading {file_path}: {e}[/yellow]")
                continue

        with open(output_path, "wb") as f:
            f.write(combined.getvalue())

        console.print(f"✓ Combined {len(file_paths)} audio files using fallback method")

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

                # Use conversation audio generation if available
                if episode.conversation_segments:
                    console.print("🎭 Using conversational audio generation")
                    audio_path = self.generate_conversation_audio(episode, script)
                else:
                    console.print("📻 Using standard audio generation")
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
