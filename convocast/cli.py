"""Command-line interface for ConvoCast."""

import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from .audio.tts_generator import TTSGenerator
from .config import get_config
from .confluence.client import ConfluenceClient
from .llm.vllm_client import VLLMClient
from .processors.content_processor import ContentProcessor

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main() -> None:
    """ConvoCast - Convert Confluence pages into onboarding podcasts."""
    pass


@main.command()
@click.option("-p", "--page-id", required=True, help="Root Confluence page ID")
@click.option("-o", "--output", default="./output", help="Output directory")
@click.option(
    "-m", "--max-pages", default=50, type=int, help="Maximum number of pages to process"
)
@click.option(
    "--text-only",
    is_flag=True,
    help="Generate text scripts only, skip audio generation",
)
def generate(page_id: str, output: str, max_pages: int, text_only: bool) -> None:
    """Generate podcast from Confluence pages."""
    try:
        console.print("🚀 [bold]Starting ConvoCast generation...[/bold]")

        # Load configuration
        config = get_config()
        config.output_dir = output
        config.max_pages = max_pages

        # Ensure output directory exists
        output_path = Path(config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Initialize clients
        console.print("📖 Connecting to Confluence...")
        confluence_client = ConfluenceClient(config.confluence)

        console.print("🤖 Initializing VLLM client...")
        vllm_client = VLLMClient(config.vllm)

        console.print("⚙️ Setting up content processor...")
        content_processor = ContentProcessor(vllm_client)

        # Fetch pages
        console.print(f"📝 Fetching pages starting from: [bold]{page_id}[/bold]")
        pages = confluence_client.traverse_pages(page_id, config.max_pages)

        if not pages:
            console.print("[red]❌ No pages found to process[/red]")
            return

        console.print(f"📄 Found [bold]{len(pages)}[/bold] pages to process")

        # Process content
        console.print("🔄 Processing content to Q&A format...")
        episodes = content_processor.process_pages(pages)

        if not episodes:
            console.print("[red]❌ No content could be processed into episodes[/red]")
            return

        console.print(f"✅ Generated [bold]{len(episodes)}[/bold] episodes")

        # Save scripts
        scripts_dir = output_path / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        for episode in episodes:
            script = content_processor.format_for_podcast(episode)
            script_file = scripts_dir / f"{episode.title.replace(' ', '-')}.txt"
            script_file.write_text(script, encoding="utf-8")
            console.print(f"📝 Script saved: [blue]{script_file}[/blue]")

        # Generate audio if requested
        if not text_only:
            console.print("🎤 Generating audio files...")
            tts_generator = TTSGenerator(config.output_dir, config.voice_speed)

            final_episodes = tts_generator.generate_batch(
                episodes, content_processor.format_for_podcast
            )

            # Save summary
            summary_file = output_path / "summary.json"
            summary_data = [episode.model_dump() for episode in final_episodes]
            summary_file.write_text(
                json.dumps(summary_data, indent=2), encoding="utf-8"
            )
            console.print(f"📊 Summary saved: [blue]{summary_file}[/blue]")

        console.print("🎉 [bold green]ConvoCast generation complete![/bold green]")
        console.print(f"📁 Output directory: [blue]{config.output_dir}[/blue]")

    except Exception as e:
        console.print(f"[red]❌ Error during generation: {e}[/red]")
        raise click.ClickException(str(e))


@main.command()
def validate() -> None:
    """Validate configuration and connections."""
    try:
        console.print("🔍 Validating configuration...")

        config = get_config()
        console.print("✅ Configuration loaded successfully")

        console.print("🔗 Testing Confluence connection...")
        confluence_client = ConfluenceClient(config.confluence)

        console.print("🤖 Testing VLLM connection...")
        vllm_client = VLLMClient(config.vllm)
        response = vllm_client.generate_completion(
            "Hello, this is a test.", "Respond with 'Connection successful'"
        )
        console.print(f"VLLM Response: {response}")

        console.print(
            "✅ [bold green]All connections validated successfully![/bold green]"
        )

    except Exception as e:
        console.print(f"[red]❌ Validation failed: {e}[/red]")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
