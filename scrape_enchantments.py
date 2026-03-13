import json
import time
import asyncio
import re
from playwright.async_api import async_playwright
import requests

BASE_URL = "https://bazaardb.gg"

async def get_all_item_urls():
    """Get all item URLs from search results."""
    items = []
    page = 1
    max_pages = 50
    
    while page <= max_pages:
        url = f"{BASE_URL}/search?c=items&page={page}"
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            links = soup.find_all("a", href=re.compile(r"^/card/"))
            
            if not links:
                break
            
            new_items = 0
            for link in links:
                href = link.get("href")
                if href and href not in items and "/card/" in href:
                    items.append(href)
                    new_items += 1
            
            if new_items == 0:
                break
            
            print(f"Page {page}: found {new_items} items (total: {len(items)})")
            page += 1
            time.sleep(0.3)
            
        except Exception as e:
            print(f"Error getting page {page}: {e}")
            break
    
    return items

async def get_item_enchantments(page, item_url):
    """Get enchantments for a specific item using Playwright."""
    try:
        await page.goto(BASE_URL + item_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1500)
        
        # Check if enchantments section exists
        section = await page.query_selector("#section-enchantments")
        if not section:
            return {}
        
        enchantments = {}
        ench_ids = ['golden', 'heavy', 'icy', 'turbo', 'shielded', 'restorative', 'toxic', 'fiery', 'shiny', 'deadly', 'radiant', 'obsidian']
        
        for ench_id in ench_ids:
            try:
                elem = await page.query_selector(f"#engine-{ench_id}")
                if elem:
                    text = await elem.text_content()
                    if text:
                        text = text.strip()
                        if "Tooltip" in text:
                            idx = text.find("Tooltip")
                            text = text[idx + 7:]
                            for stop in ["Tags", "Attribute", "Ability", "Aura", "Trigger"]:
                                if stop in text:
                                    text = text[:text.find(stop)]
                                    break
                        
                        text = ' '.join(text.split())
                        if text and len(text) > 3:
                            enchantments[ench_id] = text
            except:
                pass
        
        return enchantments
    except Exception as e:
        return {}

async def main():
    print("Fetching all item URLs...")
    # Get item URLs first
    items = []
    page = 1
    max_pages = 100
    
    while page <= max_pages:
        url = f"{BASE_URL}/search?c=items&page={page}"
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            
            links = soup.find_all("a", href=re.compile(r"^/card/"))
            
            if not links:
                break
            
            new_items = 0
            for link in links:
                href = link.get("href")
                if href and href not in items and "/card/" in href:
                    items.append(href)
                    new_items += 1
            
            if new_items == 0:
                break
            
            print(f"Page {page}: found {new_items} items (total: {len(items)})")
            page += 1
            time.sleep(0.3)
            
        except Exception as e:
            print(f"Error getting page {page}: {e}")
            break
    
    item_urls = items
    print(f"Found {len(item_urls)} items")
    
    # Load existing data to resume
    try:
        with open("data/item_enchantments.json", "r") as f:
            all_enchantments = json.load(f)
        print(f"Resuming with {len(all_enchantments)} items already scraped")
    except:
        all_enchantments = {}
    
    save_interval = 25
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        start_idx = len(all_enchantments)
        print(f"Starting from index {start_idx}")
        
        for i, item_url in enumerate(item_urls):
            # Skip already scraped items
            if item_url in all_enchantments:
                continue
            
            print(f"[{i+1}/{len(item_urls)}] {item_url}")
            enchs = await get_item_enchantments(page, item_url)
            if enchs:
                all_enchantments[item_url] = enchs
            
            # Save progress every N items
            if len(all_enchantments) % save_interval == 0 and len(all_enchantments) > 0:
                with open("data/item_enchantments.json", "w") as f:
                    json.dump(all_enchantments, f, indent=2)
                print(f"  -> Progress saved ({len(all_enchantments)} items)")
            
            await asyncio.sleep(0.2)
        
        await browser.close()
    
    # Save results
    with open("data/item_enchantments.json", "w") as f:
        json.dump(all_enchantments, f, indent=2)
    
    print(f"\nSaved {len(all_enchantments)} items to data/item_enchantments.json")

if __name__ == "__main__":
    asyncio.run(main())
