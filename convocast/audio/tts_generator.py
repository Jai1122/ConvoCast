"""Text-to-speech generator for podcast audio."""

import os
import re
import subprocess
from pathlib import Path
from typing import Callable, List

from rich.console import Console

from ..types import PodcastEpisode

console = Console()


class TTSGenerator:
    """Text-to-speech generator for creating podcast audio files."""

    def __init__(self, output_dir: str, voice_speed: float = 1.0) -> None:
        """Initialize TTS generator."""
        self.output_dir = Path(output_dir)
        self.voice_speed = voice_speed

    def generate_audio(self, episode: PodcastEpisode, script: str) -> str:
        """Generate audio file for a single episode."""
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        filename = self._sanitize_filename(episode.title)
        audio_path = self.output_dir / f"{filename}.wav"
        script_path = self.output_dir / f"{filename}.txt"

        # Save script file
        script_path.write_text(script, encoding="utf-8")

        try:
            self._generate_with_say(script, str(audio_path))
            console.print(f"🎵 Audio generated: [green]{audio_path}[/green]")
            return str(audio_path)
        except Exception as e:
            console.print(
                f"[red]❌ Failed to generate audio for '{episode.title}': {e}[/red]"
            )
            raise

    def _generate_with_say(self, text: str, output_path: str) -> None:
        """Generate audio using macOS 'say' command."""
        try:
            # Escape quotes in text for shell
            escaped_text = text.replace('"', '\\"')

            # Calculate rate (say uses words per minute, default ~200)
            rate = int(self.voice_speed * 200)

            command = [
                "say",
                "-v",
                "Alex",
                "-r",
                str(rate),
                "-o",
                output_path,
                escaped_text,
            ]

            result = subprocess.run(
                command, capture_output=True, text=True, timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"say command failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Text-to-speech generation timed out")
        except FileNotFoundError:
            raise RuntimeError(
                "'say' command not found. This feature requires macOS or compatible TTS engine."
            )
        except Exception as e:
            raise RuntimeError(f"Text-to-speech generation failed: {e}")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Remove or replace invalid characters
        sanitized = re.sub(r"[^\w\s-]", "", filename)
        # Replace spaces with hyphens
        sanitized = re.sub(r"\s+", "-", sanitized)
        # Convert to lowercase and limit length
        return sanitized.lower()[:50]

    def generate_batch(
        self,
        episodes: List[PodcastEpisode],
        format_script: Callable[[PodcastEpisode], str],
    ) -> List[PodcastEpisode]:
        """Generate audio for multiple episodes."""
        results: List[PodcastEpisode] = []

        for episode in episodes:
            try:
                console.print(f"🎤 Generating audio for: [bold]{episode.title}[/bold]")
                script = format_script(episode)
                audio_path = self.generate_audio(episode, script)

                # Update episode with audio path
                updated_episode = episode.model_copy()
                updated_episode.audio_path = audio_path
                results.append(updated_episode)

            except Exception as e:
                console.print(
                    f"[yellow]⚠️  Skipping audio generation for '{episode.title}': {e}[/yellow]"
                )
                # Add episode without audio path
                results.append(episode)

        return results
