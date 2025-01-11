from dataclasses import dataclass, field
from typing import ClassVar, List
import requests
from bs4 import BeautifulSoup
import urllib.parse
import json
import re
from .base import Transform
from entities.base import Entity
from entities.image import Image
from ui.managers.status_manager import StatusManager

@dataclass
class ReverseImage(Transform):
    name: ClassVar[str] = "Reverse Image"
    description: ClassVar[str] = "Find similar images using Yandex reverse image search"
    input_types: ClassVar[List[str]] = ["Image"]
    output_types: ClassVar[List[str]] = ["Image"]
    
    async def run(self, entity: Image, graph) -> List[Entity]:
        """Async implementation using aiohttp"""
        image_url = entity.properties.get("image", "")
        if not image_url:
            return []
        
        status = StatusManager.get()
        operation_id = status.start_loading("Reverse Image")
        
        try:
            results = await self.run_in_thread(entity, graph)
            if results:
                status.set_text(f"Reverse Image: Found {len(results)} similar images")
            else:
                status.set_text("Reverse Image: No similar images found")
            return results
        except Exception as e:
            status.set_text("Reverse Image: Search failed")
            return []
        finally:
            status.stop_loading(operation_id)
    
    def _run_sync(self, entity: Image, graph) -> List[Entity]:
        """Synchronous implementation for CPU-bound operations"""
        image_url = entity.properties.get("image", "")
        similar_images = []
        status = StatusManager.get()
        
        yandex_url = "https://yandex.com/images/search"
        params = {
            "rpt": "imageview",
            "url": image_url,
            "source": "collections"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        try:
            response = requests.get(yandex_url, params=params, headers=headers, allow_redirects=True)
            
            if response.status_code != 200:
                status.set_text("Reverse Image: Failed to get response from Yandex")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all CbirSites-Item elements
            items = soup.find_all("li", class_="CbirSites-Item")
            
            for item in items:
                try:
                    # Get image URL from thumbnail
                    thumb_div = item.find("div", class_="CbirSites-ItemThumb")
                    if not thumb_div:
                        continue
                        
                    thumb_link = thumb_div.find("a")
                    if not thumb_link:
                        continue
                        
                    img_url = thumb_link.get("href", "")
                    if not img_url:
                        continue
                    
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url
                    
                    # Get title and source URL from info div
                    info_div = item.find("div", class_="CbirSites-ItemInfo")
                    if not info_div:
                        continue
                        
                    title_div = info_div.find("div", class_="CbirSites-ItemTitle")
                    if not title_div:
                        continue
                        
                    title_link = title_div.find("a")
                    if not title_link:
                        continue
                        
                    source_url = title_link.get("href", "")
                    title = title_link.get_text(strip=True)
                    description = title_link.get_text(strip=True)
                    
                    similar_image = Image(properties={
                        "title": title,
                        "description": description,
                        "url": source_url,
                        "image": img_url,
                        "source": "ReverseImage transform (Yandex)"
                    })
                    similar_images.append(similar_image)
                    
                except Exception as e:
                    continue

        except Exception as e:
            status.set_text("Reverse Image: Search failed")
        
        return similar_images
