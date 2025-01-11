from dataclasses import dataclass, field
from typing import ClassVar, List, Dict, Any
from .base import Transform
from entities.base import Entity
from entities.website import Website
from entities.username import Username
from entities.image import Image
from entities.text import Text
from ui.managers.status_manager import StatusManager

import requests
from bs4 import BeautifulSoup
from googlesearch import search

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

@dataclass
class TextSearch(Transform):
    name: ClassVar[str] = "Text Search"
    description: ClassVar[str] = "Search for websites and usernames using Bing and Google search"
    input_types: ClassVar[List[str]] = ["Text"]
    output_types: ClassVar[List[str]] = ["Website", "Username", "Image"]
    
    async def run(self, entity: Text, graph) -> List[Entity]:
        if not isinstance(entity, Text):
            return []
        
        text = entity.properties.get("text", "")
        if not text:
            return []
        
        return await self.run_in_thread(entity, graph)
    

    def _search_bing(self, text: str) -> List[Dict[str, Any]]:
        """Perform Bing search and return results"""
        results = []
        search_url = f"https://www.bing.com/search?q={text}"
        
        try:
            response = requests.get(search_url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                search_items = soup.find_all("li", class_="b_algo")
                
                for item in search_items:
                    url = item.find("a")["href"]
                    title = item.find("h2").text
                    description = item.find("p").text
                    results.append({
                        "url": url,
                        "title": title,
                        "description": description,
                        "source": "Bing"
                    })
        except Exception as e:
            print(f"Bing search failed: {str(e)}")

        return results

    def _search_google(self, text: str) -> List[Dict[str, Any]]:
        """Perform Google search and return results"""
        results = []
        search_url = f"https://www.google.com/search?q={text}"
        
        try:
            response = requests.get(search_url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                search_items = soup.find_all("li", class_="g")
                
                for item in search_items:
                    url = item.find("a")["href"]
                    title = item.find("h3").text
                    description = item.find("span").text
                    results.append({
                        "url": url,
                        "title": title,
                        "description": description,
                        "source": "Google"
                    })
        except Exception as e:
            print(f"Google search failed: {str(e)}")

        return results

    def _search_image(self, text: str) -> List[Dict[str, Any]]:
        """Perform image search and return results"""
        results = []
        search_url = f"https://www.bing.com/images/search?q={text}"
        try:
            response = requests.get(search_url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                images = soup.find_all("img")
                for img in images:
                    if 'src' in img.attrs and img['src'].startswith("http"):
                        results.append({
                            "title": img.get('alt', ''),
                            "url": img['src'],
                            "description": img.get('alt', ''),
                            "source": "Bing Images"
                        })
        except Exception as e:
            print(f"Image search failed: {str(e)}")
        return results

    def _create_entity(self, result: Dict[str, Any]) -> Entity:
        """Create an entity based on the search result"""

        # Handle image results
        if result.get("source") == "Bing Images":
            title = result["title"]
            if "Image result for" not in title:
                return None
            return Image(properties={
                "title": title.replace("Image result for", "").strip(),
                "url": result["url"],
                "source": "TextSearch transform (Bing Images)",
                "image": result["url"]
            })
            
        # Handle website/username results
        url = result["url"]
        domain = url.split("/")[2]
        
        if domain == "www.instagram.com" and url.split("/")[3] not in ["p", "stories"]:
            username = url.split("/")[3]
            return Username(properties={
                "username": username,
                "platform": "instagram",
                "link": url,
                "source": f"TextSearch transform ({result['source']})"
            })
        elif domain in ["x.com", "twitter.com"]:
            username = url.split("/")[3].split("?")[0]
            return Username(properties={
                "username": username,
                "platform": "twitter",
                "link": url,
                "source": f"TextSearch transform ({result['source']})"
            })
        else:
            return Website(properties={
                "url": url,
                "domain": domain,
                "title": result["title"],
                "description": result["description"],
                "source": f"TextSearch transform ({result['source']})"
            })
    
    def _run_sync(self, entity: Text, graph) -> List[Entity]:
        """Synchronous implementation for CPU-bound operations"""
        text = entity.properties.get("text", "")
        
        # Collect search results
        status = StatusManager.get()
        status.set_text("Searching for text...")
        operation_id = status.start_loading("Text Search")

        search_results = []
        search_results.extend(self._search_bing(text))
        search_results.extend(self._search_google(text))
        search_results.extend(self._search_image(text))
        status.set_text(f"Searching for text done with {len(search_results)} results")
        status.stop_loading(operation_id)

        # Process results and create entities
        entities = []
        for result in search_results:
            try:
                entity = self._create_entity(result)
                if entity is not None:
                    entities.append(entity)
            except Exception:
                continue
                
        return entities