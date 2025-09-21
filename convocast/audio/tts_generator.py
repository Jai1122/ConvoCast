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

from ..types import PodcastEpisode, TTSEngine, VoiceProfile

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
            speed=1.0,
            pitch=1.0,
        ),
        "gtts_british": VoiceProfile(
            name="Google TTS British",
            engine=TTSEngine.GTTS,
            language="en-uk",
            speed=1.0,
            pitch=1.0,
        ),
        "macos_alex": VoiceProfile(
            name="macOS Alex",
            engine=TTSEngine.MACOS_SAY,
            voice_id="Alex",
            language="en",
            speed=1.0,
            pitch=1.0,
        ),
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

        # Initialize pygame mixer for audio handling
        pygame.mixer.init()

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

            if self.voice_profile.engine == TTSEngine.PYTTSX3:
                self._generate_with_pyttsx3(script, str(audio_path))
            elif self.voice_profile.engine == TTSEngine.GTTS:
                self._generate_with_gtts(script, str(audio_path))
            elif self.voice_profile.engine == TTSEngine.MACOS_SAY:
                self._generate_with_say(script, str(audio_path))
            else:
                raise ValueError(f"Unsupported TTS engine: {self.voice_profile.engine}")

            console.print(f"🎵 Audio generated: [green]{audio_path}[/green]")
            return str(audio_path)
        except Exception as e:
            console.print(
                f"[red]❌ Failed to generate audio for '{episode.title}': {e}[/red]"
            )
            raise

    def _generate_with_pyttsx3(self, text: str, output_path: str) -> None:
        """Generate audio using pyttsx3 (cross-platform)."""
        try:
            import pyttsx3

            engine = pyttsx3.init()

            # Set voice if specified
            if self.voice_profile.voice_id:
                voices = engine.getProperty("voices")
                for voice in voices:
                    if self.voice_profile.voice_id in voice.id:
                        engine.setProperty("voice", voice.id)
                        break

            # Set properties
            rate = engine.getProperty("rate")
            engine.setProperty(
                "rate", int(rate * self.voice_profile.speed * self.voice_speed)
            )

            volume = engine.getProperty("volume")
            engine.setProperty(
                "volume", min(1.0, volume * 1.1)
            )  # Slightly boost volume

            # Save to file
            engine.save_to_file(text, output_path)
            engine.runAndWait()

            # Convert to MP3 if needed
            if not output_path.endswith(".mp3"):
                self._convert_to_mp3(output_path, output_path.replace(".wav", ".mp3"))

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
        try:
            # Try using ffmpeg first
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    input_path,
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    output_path,
                    "-y",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return
        except FileNotFoundError:
            pass

        # Fallback: just copy if already compatible
        if input_path != output_path:
            import shutil

            shutil.copy2(input_path, output_path)

    def _combine_audio_files(self, file_paths: List[str], output_path: str) -> None:
        """Combine multiple audio files into one."""
        try:
            # Try using ffmpeg to concatenate
            concat_list = "|".join(file_paths)
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    f"concat:{concat_list}",
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "128k",
                    output_path,
                    "-y",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return
        except FileNotFoundError:
            pass

        # Fallback: use pygame to combine
        combined = io.BytesIO()
        for file_path in file_paths:
            with open(file_path, "rb") as f:
                combined.write(f.read())

        with open(output_path, "wb") as f:
            f.write(combined.getvalue())

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
