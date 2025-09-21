"""Confluence API client for secure access and page traversal."""

import re
from typing import List, Set
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from rich.console import Console

from ..types import ConfluenceConfig, ConfluencePage

console = Console()


class ConfluenceClient:
    """Client for interacting with Confluence API."""

    def __init__(self, config: ConfluenceConfig) -> None:
        """Initialize Confluence client with configuration."""
        self.config = config
        self.base_api_url = f"{config.base_url}/wiki/rest/api"
        self.session = requests.Session()
        self.session.auth = (config.username, config.api_token)
        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    def get_page(self, page_id: str) -> ConfluencePage:
        """Fetch a single Confluence page by ID."""
        try:
            response = self.session.get(
                f"{self.base_api_url}/content/{page_id}",
                params={"expand": "body.storage,children.page"},
                timeout=30,
            )
            response.raise_for_status()

            page_data = response.json()
            content = self._extract_text_from_html(
                page_data["body"]["storage"]["value"]
            )

            return ConfluencePage(
                id=page_data["id"],
                title=page_data["title"],
                content=content,
                url=urljoin(
                    self.config.base_url, f"/wiki{page_data['_links']['webui']}"
                ),
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch page {page_id}: {e}")

    def get_child_pages(self, page_id: str) -> List[str]:
        """Get child page IDs for a given page."""
        try:
            response = self.session.get(
                f"{self.base_api_url}/content/{page_id}/child/page", timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return [page["id"] for page in data["results"]]
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch child pages for {page_id}: {e}")

    def traverse_pages(
        self, root_page_id: str, max_pages: int = 50
    ) -> List[ConfluencePage]:
        """Traverse pages recursively starting from root page."""
        pages: List[ConfluencePage] = []
        visited: Set[str] = set()
        queue = [root_page_id]

        while queue and len(pages) < max_pages:
            page_id = queue.pop(0)

            if page_id in visited:
                continue

            visited.add(page_id)

            try:
                page = self.get_page(page_id)
                pages.append(page)
                console.print(f"✓ Processed: [bold]{page.title}[/bold]")

                # Add child pages to queue
                child_page_ids = self.get_child_pages(page_id)
                queue.extend(
                    [child_id for child_id in child_page_ids if child_id not in visited]
                )

            except Exception as e:
                console.print(f"[red]✗ Error processing page {page_id}: {e}[/red]")

        return pages

    def _extract_text_from_html(self, html: str) -> str:
        """Extract clean text content from Confluence HTML."""
        soup = BeautifulSoup(html, "lxml")

        # Remove script, style, and metadata elements
        for element in soup(["script", "style"]):
            element.decompose()

        # Remove elements with class 'metadata'
        for element in soup.find_all(class_="metadata"):
            element.decompose()

        # Get text and clean whitespace
        text = soup.get_text()
        # Replace multiple whitespace with single space
        text = re.sub(r"\s+", " ", text).strip()

        return text
