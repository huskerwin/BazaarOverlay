from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse, quote

import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning
from urllib3.util.retry import Retry

BASE_URL = "https://bazaardb.gg"
SEARCH_URL = "https://bazaardb.gg/search?c=items"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36 BazaarTemplateScraper/1.0"
)

SIZE_MAP = {
    "small": 256,
    "medium": 256,
    "large": 400,
}

SIZE_URLS = {
    "small": "https://bazaardb.gg/search?c=items&q=s:small",
    "medium": "https://bazaardb.gg/search?c=items&q=s:medium",
    "large": "https://bazaardb.gg/search?c=items&q=s:large",
}

INVALID_FILENAME_CHARS = re.compile(r"[<>:\"/\|?*\x00-\x1f]")
MULTI_UNDERSCORE = re.compile(r"_+")


@dataclass(frozen=True)
class ItemImageEntry:
    item_name: str
    source_page_url: str
    image_url: str
    size: str = "medium"  # small, medium, or large


@dataclass(frozen=True)
class DownloadRecord:
    item_name: str
    source_page_url: str
    image_url: str
    local_filename: str
    status: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape BazaarDB item images into a local templates folder."
    )
    parser.add_argument(
        "--url",
        default=SEARCH_URL,
        help="Start URL for item search.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "requests", "playwright"),
        default="auto",
        help="Scraping mode. 'auto' inspects static content first.",
    )
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=Path("templates"),
        help="Folder where downloaded templates are saved.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum pages to crawl in requests mode.",
    )
    parser.add_argument(
        "--max-scrolls",
        type=int,
        default=300,
        help="Maximum scroll iterations in playwright mode.",
    )
    parser.add_argument(
        "--scroll-wait-ms",
        type=int,
        default=1100,
        help="Wait time after each scroll in playwright mode.",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run browser in visible mode for debugging.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=20.0,
        help="HTTP request timeout in seconds.",
    )
    parser.add_argument(
        "--download-delay",
        type=float,
        default=0.20,
        help="Delay between image downloads in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retry attempts for transient HTTP failures.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of items to download (0 means no limit).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL cert verification (only if your environment requires it).",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Inspect page rendering style and exit without downloading.",
    )
    parser.add_argument(
        "--metadata-csv",
        type=Path,
        default=None,
        help="Path for metadata CSV output (default: <templates-dir>/items.csv).",
    )
    parser.add_argument(
        "--metadata-json",
        type=Path,
        default=None,
        help="Path for metadata JSON output (default: <templates-dir>/items.json).",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header used for HTTP requests.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity.",
    )
    parser.add_argument(
        "--size",
        default="medium",
        choices=("small", "medium", "large"),
        help="Image size to download (small=256, medium=256, large=400).",
    )
    parser.add_argument(
        "--auto-size",
        action="store_true",
        help="Automatically detect item sizes and download appropriate resolution.",
    )
    return parser.parse_args()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def create_session(user_agent: str, retries: int) -> requests.Session:
    retry = Retry(
        total=max(0, retries),
        connect=max(0, retries),
        read=max(0, retries),
        status=max(0, retries),
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": user_agent})
    return session


def sanitize_filename(name: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("_", name.strip())
    cleaned = cleaned.replace(" ", "_")
    cleaned = MULTI_UNDERSCORE.sub("_", cleaned)
    cleaned = cleaned.strip("._")
    if not cleaned:
        return "item"
    return cleaned


def fallback_name_from_url(url: str) -> str:
    path = urlparse(url).path
    slug = path.rstrip("/").split("/")[-1]
    slug = slug.replace("-", " ").strip()
    return slug if slug else "Unknown Item"


def normalize_item_name(raw_name: str, source_page_url: str) -> str:
    normalized = " ".join(raw_name.split()).strip()
    if normalized:
        return normalized
    return fallback_name_from_url(source_page_url)


def normalize_image_url(raw_url: str, base_url: str) -> str:
    candidate = (raw_url or "").strip()
    if not candidate:
        return ""
    if candidate.startswith("data:"):
        return ""
    if candidate.startswith("//"):
        candidate = f"https:{candidate}"
    return urljoin(base_url, candidate)


def convert_image_url_size(image_url: str, size: int) -> str:
    """Convert image URL to requested size by replacing the @xxx pattern."""
    if size == 400:
        return re.sub(r'@\d+', '@400L', image_url)
    else:
        return re.sub(r'@(\d+)L*\.webp', f'@{size}.webp', image_url)


def parse_img_candidate(img_tag) -> str:
    if img_tag is None:
        return ""

    candidates: list[str] = []
    for attr in ("src", "data-src", "data-original", "data-lazy-src"):
        value = img_tag.get(attr)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())

    srcset = img_tag.get("srcset")
    if isinstance(srcset, str) and srcset.strip():
        for entry in srcset.split(","):
            token = entry.strip().split(" ")[0].strip()
            if token:
                candidates.append(token)

    for candidate in candidates:
        if candidate.startswith("data:"):
            continue
        return candidate

    return ""


def extract_image_from_anchor(anchor) -> str:
    img_tags = anchor.find_all("img")
    for img_tag in img_tags:
        image_raw = parse_img_candidate(img_tag)
        image_url = normalize_image_url(image_raw, BASE_URL)
        if image_url:
            return image_url
    return ""


def extract_entries_from_soup(soup: BeautifulSoup, page_url: str) -> list[ItemImageEntry]:
    entries: list[ItemImageEntry] = []

    for anchor in soup.select('a[href*="/card/"]'):
        href = anchor.get("href")
        if not isinstance(href, str) or not href.strip():
            continue

        source_page_url = urljoin(BASE_URL, href.strip())
        raw_name = ""

        header = anchor.find("h3")
        if header is not None:
            raw_name = header.get_text(" ", strip=True)
        if not raw_name:
            aria_label = anchor.get("aria-label")
            raw_name = aria_label if isinstance(aria_label, str) else ""
        if not raw_name:
            raw_name = anchor.get_text(" ", strip=True)

        image_url = extract_image_from_anchor(anchor)
        if not image_url:
            continue

        item_name = normalize_item_name(raw_name, source_page_url)
        entries.append(
            ItemImageEntry(
                item_name=item_name,
                source_page_url=source_page_url,
                image_url=image_url,
            )
        )

    return dedupe_entries(entries)


def dedupe_entries(entries: Iterable[ItemImageEntry]) -> list[ItemImageEntry]:
    deduped: list[ItemImageEntry] = []
    seen: set[tuple[str, str]] = set()

    for entry in entries:
        key = (entry.source_page_url, entry.image_url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)

    return deduped


def inspect_render_mode(
    session: requests.Session,
    start_url: str,
    timeout: float,
    verify_ssl: bool,
) -> dict[str, object]:
    response = session.get(start_url, timeout=timeout, verify=verify_ssl)
    response.raise_for_status()

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    entries = extract_entries_from_soup(soup, start_url)
    next_like_links: set[str] = set()
    for anchor in soup.select('a[href*="search?c=items"]'):
        href_value = anchor.get("href")
        if isinstance(href_value, str):
            next_like_links.add(urljoin(BASE_URL, href_value))

    report = {
        "status_code": response.status_code,
        "html_length": len(html),
        "static_item_entries_detected": len(entries),
        "pagination_links_detected": len(next_like_links),
        "nextjs_hint": "_next" in html or "self.__next_f.push" in html,
        "recommendation": "playwright" if len(entries) < 100 else "requests",
    }
    return report


def crawl_requests_mode(
    session: requests.Session,
    start_url: str,
    timeout: float,
    verify_ssl: bool,
    max_pages: int,
    polite_delay: float,
) -> list[ItemImageEntry]:
    queue: list[str] = [start_url]
    visited: set[str] = set()
    all_entries: list[ItemImageEntry] = []

    while queue and len(visited) < max_pages:
        page_url = queue.pop(0)
        if page_url in visited:
            continue

        visited.add(page_url)
        logging.info("[requests] Fetching %s", page_url)
        response = session.get(page_url, timeout=timeout, verify=verify_ssl)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        entries = extract_entries_from_soup(soup, page_url)
        all_entries.extend(entries)
        logging.info(
            "[requests] Found %d entries on page (%d total before dedupe)",
            len(entries),
            len(all_entries),
        )

        discovered: set[str] = set()
        for anchor in soup.select('a[href*="search?c=items"]'):
            href_value = anchor.get("href")
            if not isinstance(href_value, str):
                continue
            absolute = urljoin(BASE_URL, href_value)
            if absolute in visited:
                continue

            parsed = urlparse(absolute)
            query = parse_qs(parsed.query)
            if query.get("c", [""])[0] != "items":
                continue
            discovered.add(absolute)

        for link in sorted(discovered):
            if link not in queue:
                queue.append(link)

        if polite_delay > 0:
            time.sleep(polite_delay)

    deduped = dedupe_entries(all_entries)
    logging.info("[requests] Completed crawl: %d unique entries", len(deduped))
    return deduped


def _collect_playwright_cards(page) -> list[dict[str, str]]:
    return page.evaluate(
        """
        () => {
            const cards = [];
            const anchors = Array.from(document.querySelectorAll('a[href*="/card/"]'));
            for (const anchor of anchors) {
                const heading = anchor.querySelector('h3');
                const rawName = (heading?.textContent || anchor.getAttribute('aria-label') || anchor.textContent || '').trim();

                const candidates = [];
                const images = Array.from(anchor.querySelectorAll('img'));
                for (const img of images) {
                    const attrs = ['src', 'data-src', 'data-original', 'data-lazy-src'];
                    for (const attr of attrs) {
                        const value = img.getAttribute(attr);
                        if (value) candidates.push(value.trim());
                    }
                    const srcset = img.getAttribute('srcset') || '';
                    if (srcset) {
                        for (const part of srcset.split(',')) {
                            const token = part.trim().split(' ')[0]?.trim();
                            if (token) candidates.push(token);
                        }
                    }
                }

                let imageUrl = '';
                for (const candidate of candidates) {
                    if (!candidate || candidate.startsWith('data:')) continue;
                    imageUrl = candidate;
                    break;
                }

                if (!imageUrl) continue;
                cards.push({
                    item_name: rawName,
                    source_page_url: anchor.href,
                    image_url: imageUrl,
                });
            }
            return cards;
        }
        """
    )


def crawl_playwright_mode(
    start_url: str,
    max_scrolls: int,
    scroll_wait_ms: int,
    headless: bool,
    user_agent: str,
) -> list[ItemImageEntry]:
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for dynamic scraping. Install with: pip install playwright"
        ) from exc

    collected: dict[tuple[str, str], ItemImageEntry] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()

        logging.info("[playwright] Opening %s", start_url)
        page.goto(start_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(1500)

        stale_rounds = 0
        for index in range(max_scrolls):
            cards = _collect_playwright_cards(page)
            before = len(collected)
            for card in cards:
                image_url = normalize_image_url(card.get("image_url", ""), BASE_URL)
                source_page_url = urljoin(BASE_URL, card.get("source_page_url", ""))
                if not image_url or not source_page_url:
                    continue

                item_name = normalize_item_name(card.get("item_name", ""), source_page_url)
                key = (source_page_url, image_url)
                collected[key] = ItemImageEntry(
                    item_name=item_name,
                    source_page_url=source_page_url,
                    image_url=image_url,
                )

            discovered_now = len(collected) - before
            logging.info(
                "[playwright] Scroll %d/%d -> %d unique entries (+%d)",
                index + 1,
                max_scrolls,
                len(collected),
                discovered_now,
            )

            if discovered_now == 0:
                stale_rounds += 1
            else:
                stale_rounds = 0

            if stale_rounds >= 5:
                break

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(max(150, scroll_wait_ms))

        context.close()
        browser.close()

    return list(collected.values())


def crawl_playwright_by_size(
    max_scrolls: int,
    scroll_wait_ms: int,
    headless: bool,
    user_agent: str,
) -> list[ItemImageEntry]:
    """Crawl items grouped by size category using separate URLs."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for dynamic scraping. Install with: pip install playwright"
        ) from exc

    collected: dict[tuple[str, str], ItemImageEntry] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=user_agent)
        
        for size_name, size_url in SIZE_URLS.items():
            logging.info("[playwright] Fetching %s items from %s", size_name, size_url)
            page = context.new_page()
            page.goto(size_url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(1500)
            
            stale_rounds = 0
            for index in range(max_scrolls):
                cards = _collect_playwright_cards(page)
                before = len(collected)
                for card in cards:
                    image_url = normalize_image_url(card.get("image_url", ""), BASE_URL)
                    source_page_url = urljoin(BASE_URL, card.get("source_page_url", ""))
                    if not image_url or not source_page_url:
                        continue

                    item_name = normalize_item_name(card.get("item_name", ""), source_page_url)
                    key = (source_page_url, image_url)
                    
                    # Only add if not already present (first size wins)
                    if key not in collected:
                        collected[key] = ItemImageEntry(
                            item_name=item_name,
                            source_page_url=source_page_url,
                            image_url=image_url,
                            size=size_name,
                        )

                discovered_now = len(collected) - before
                logging.info(
                    "[playwright] %s scroll %d/%d -> %d total (+%d)",
                    size_name, index + 1, max_scrolls, len(collected), discovered_now,
                )

                if discovered_now == 0:
                    stale_rounds += 1
                else:
                    stale_rounds = 0

                if stale_rounds >= 3:
                    break

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(max(150, scroll_wait_ms))
            
            page.close()
        
        context.close()
        browser.close()

    return list(collected.values())


def choose_mode(requested_mode: str, inspection: dict[str, object]) -> str:
    if requested_mode != "auto":
        return requested_mode
    recommendation = inspection.get("recommendation")
    if isinstance(recommendation, str) and recommendation in {"requests", "playwright"}:
        return recommendation
    return "playwright"


def load_existing_hashes(templates_dir: Path) -> dict[str, str]:
    hash_to_filename: dict[str, str] = {}
    if not templates_dir.exists():
        return hash_to_filename

    for file_path in templates_dir.glob("*.png"):
        try:
            digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        except OSError:
            continue
        hash_to_filename[digest] = file_path.name

    return hash_to_filename


def build_unique_filename(base_name: str, used_names: set[str], templates_dir: Path) -> str:
    candidate = f"{base_name}.png"
    index = 2
    while candidate in used_names or (templates_dir / candidate).exists():
        candidate = f"{base_name}__{index}.png"
        index += 1
    used_names.add(candidate)
    return candidate


def decode_and_encode_png(image_bytes: bytes) -> bytes | None:
    np_buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(np_buffer, cv2.IMREAD_UNCHANGED)
    if image is None:
        return None

    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        return None
    return bytes(encoded)


def download_images(
    entries: list[ItemImageEntry],
    session: requests.Session,
    templates_dir: Path,
    timeout: float,
    verify_ssl: bool,
    polite_delay: float,
    limit: int,
    size: str = "medium",
) -> list[DownloadRecord]:
    templates_dir.mkdir(parents=True, exist_ok=True)

    default_size_value = SIZE_MAP.get(size, 256)
    has_auto_size = any(getattr(e, 'size', None) for e in entries)
    if has_auto_size:
        logging.info("Downloading images with auto-size detection")
    else:
        logging.info("Downloading images at size: %s (%dpx)", size, default_size_value)

    hash_to_filename = load_existing_hashes(templates_dir)
    image_url_to_filename: dict[str, str] = {}
    used_names: set[str] = {path.name for path in templates_dir.glob("*.png")}

    records: list[DownloadRecord] = []
    selected_entries = entries if limit <= 0 else entries[:limit]

    for idx, entry in enumerate(selected_entries, start=1):
        # Use item's size attribute if available, otherwise use global size
        item_size = getattr(entry, 'size', None) or size
        size_value = SIZE_MAP.get(item_size, default_size_value)
        
        # Try primary size first
        sized_url = convert_image_url_size(entry.image_url, size_value)
        
        # If requesting large (400L) and not available, fall back to 256
        if size_value == 400:
            response = session.head(sized_url, timeout=timeout, verify=verify_ssl, allow_redirects=True)
            if response.status_code == 404:
                sized_url = convert_image_url_size(entry.image_url, 256)
                logging.debug("400L not available, falling back to 256 for %s", entry.item_name)
        
        logging.info("[download] %d/%d %s (size: %s)", idx, len(selected_entries), entry.item_name, item_size)

        existing_from_url = image_url_to_filename.get(sized_url)
        if existing_from_url:
            records.append(
                DownloadRecord(
                    item_name=entry.item_name,
                    source_page_url=entry.source_page_url,
                    image_url=sized_url,
                    local_filename=existing_from_url,
                    status="skipped",
                    reason="duplicate-image-url",
                )
            )
            continue

        try:
            response = session.get(sized_url, timeout=timeout, verify=verify_ssl)
            response.raise_for_status()
        except Exception as exc:
            records.append(
                DownloadRecord(
                    item_name=entry.item_name,
                    source_page_url=entry.source_page_url,
                    image_url=sized_url,
                    local_filename="",
                    status="failed",
                    reason=f"http-error: {exc}",
                )
            )
            continue

        png_bytes = decode_and_encode_png(response.content)
        if png_bytes is None:
            records.append(
                DownloadRecord(
                    item_name=entry.item_name,
                    source_page_url=entry.source_page_url,
                    image_url=sized_url,
                    local_filename="",
                    status="failed",
                    reason="decode-or-encode-failed",
                )
            )
            continue

        digest = hashlib.sha256(png_bytes).hexdigest()
        existing_from_hash = hash_to_filename.get(digest)
        if existing_from_hash:
            image_url_to_filename[sized_url] = existing_from_hash
            records.append(
                DownloadRecord(
                    item_name=entry.item_name,
                    source_page_url=entry.source_page_url,
                    image_url=sized_url,
                    local_filename=existing_from_hash,
                    status="skipped",
                    reason="duplicate-image-content",
                )
            )
            continue

        base_name = sanitize_filename(entry.item_name)
        local_filename = build_unique_filename(base_name, used_names, templates_dir)
        output_path = templates_dir / local_filename
        output_path.write_bytes(png_bytes)

        hash_to_filename[digest] = local_filename
        image_url_to_filename[sized_url] = local_filename

        records.append(
            DownloadRecord(
                item_name=entry.item_name,
                source_page_url=entry.source_page_url,
                image_url=sized_url,
                local_filename=local_filename,
                status="downloaded",
                reason="ok",
            )
        )

        if polite_delay > 0:
            time.sleep(polite_delay)

    return records


def write_metadata(records: list[DownloadRecord], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "item_name",
                "source_page_url",
                "image_url",
                "local_filename",
                "status",
                "reason",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))

    json_path.write_text(
        json.dumps([asdict(record) for record in records], indent=2),
        encoding="utf-8",
    )


def summarize(records: list[DownloadRecord]) -> dict[str, int]:
    summary = {"downloaded": 0, "skipped": 0, "failed": 0}
    for record in records:
        if record.status in summary:
            summary[record.status] += 1
    return summary


def main() -> int:
    args = parse_args()
    configure_logging(args.log_level)

    verify_ssl = not args.insecure
    if not verify_ssl:
        disable_warnings(InsecureRequestWarning)
        logging.warning("SSL verification disabled (--insecure).")

    session = create_session(user_agent=args.user_agent, retries=args.retries)

    try:
        inspection = inspect_render_mode(
            session=session,
            start_url=args.url,
            timeout=args.request_timeout,
            verify_ssl=verify_ssl,
        )
    except Exception as exc:
        logging.error("Inspection failed: %s", exc)
        return 1

    logging.info("Inspection: %s", json.dumps(inspection, indent=2))
    if args.inspect_only:
        return 0

    mode = choose_mode(args.mode, inspection)
    logging.info("Using mode: %s", mode)

    try:
        if mode == "requests":
            entries = crawl_requests_mode(
                session=session,
                start_url=args.url,
                timeout=args.request_timeout,
                verify_ssl=verify_ssl,
                max_pages=max(1, int(args.max_pages)),
                polite_delay=max(0.0, float(args.download_delay)),
            )
        else:
            if args.auto_size:
                entries = crawl_playwright_by_size(
                    max_scrolls=max(1, int(args.max_scrolls)),
                    scroll_wait_ms=max(100, int(args.scroll_wait_ms)),
                    headless=not bool(args.headful),
                    user_agent=args.user_agent,
                )
            else:
                entries = crawl_playwright_mode(
                    start_url=args.url,
                    max_scrolls=max(1, int(args.max_scrolls)),
                    scroll_wait_ms=max(100, int(args.scroll_wait_ms)),
                    headless=not bool(args.headful),
                    user_agent=args.user_agent,
                )
    except Exception as exc:
        logging.error("Discovery failed in %s mode: %s", mode, exc)
        if mode == "playwright":
            logging.error("Hint: run 'playwright install chromium' after installing dependencies.")
        return 1

    if not entries:
        logging.warning("No item entries discovered; nothing to download.")
        return 0

    logging.info("Discovered %d unique item image entries.", len(entries))

    records = download_images(
        entries=entries,
        session=session,
        templates_dir=args.templates_dir,
        timeout=args.request_timeout,
        verify_ssl=verify_ssl,
        polite_delay=max(0.0, float(args.download_delay)),
        limit=max(0, int(args.limit)),
        size=args.size,
    )

    csv_path = args.metadata_csv or (args.templates_dir / "items.csv")
    json_path = args.metadata_json or (args.templates_dir / "items.json")
    write_metadata(records=records, csv_path=csv_path, json_path=json_path)

    summary = summarize(records)
    logging.info(
        "Complete. downloaded=%d skipped=%d failed=%d",
        summary["downloaded"],
        summary["skipped"],
        summary["failed"],
    )
    logging.info("Metadata written: %s and %s", csv_path, json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
