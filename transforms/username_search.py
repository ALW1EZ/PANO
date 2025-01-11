from dataclasses import dataclass, field
from typing import ClassVar, List, Dict, Any
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from .base import Transform
from entities.base import Entity
from entities.website import Website
from entities.username import Username
from ui.managers.status_manager import StatusManager

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

@dataclass
class UsernameToWebsite(Transform):
    name: ClassVar[str] = "Username to Website"
    description: ClassVar[str] = "Extract website or social media usernames from username using Bing and Google search"
    input_types: ClassVar[List[str]] = ["Username"]
    output_types: ClassVar[List[str]] = ["Website", "Username"]
    
    async def run(self, entity: Username, graph) -> List[Entity]:
        """Async implementation using aiohttp"""
        if not isinstance(entity, Username):
            return []
        
        username = entity.properties.get("username", "")
        if not username:
            return []
        
        return await self.run_in_thread(entity, graph)

    def _search_bing(self, username: str) -> List[Dict[str, Any]]:
        """Perform Bing search and return results"""
        results = []
        search_url = f"https://www.bing.com/search?q={username}"
        
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

    def _search_google(self, username: str) -> List[Dict[str, Any]]:
        """Perform Google search and return results"""
        results = []
        
        try:
            google_results = search(username, num_results=10)
            for url in google_results:
                response = requests.get(url, timeout=5)
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.title.string if soup.title else url
                description = ""
                meta_desc = soup.find("meta", {"name": "description"})
                if meta_desc:
                    description = meta_desc.get("content", "")
                
                results.append({
                    "url": url,
                    "title": title,
                    "description": description,
                    "source": "Google"
                })
        except Exception as e:
            print(f"Google search failed: {str(e)}")
            
        return results

    def _create_entity(self, result: Dict[str, Any]) -> Entity:
        """Create appropriate entity from search result"""
        url = result["url"]
        domain = url.split("/")[2]
        
        if domain == "www.instagram.com" and url.split("/")[3] not in ["p", "stories"]:
            username = url.split("/")[3]
            return Username(properties={
                "username": username,
                "platform": "instagram",
                "link": url,
                "source": f"UsernameToWebsite transform ({result['source']})"
            })
        elif domain == "twitter.com" and "/status/" not in url:
            username = url.split("/")[3].split("?")[0]
            return Username(properties={
                "username": username,
                "platform": "twitter", 
                "link": url,
                "source": f"UsernameToWebsite transform ({result['source']})"
            })
        elif domain == "x.com":
            username = url.split("/")[3].split("?")[0]
            return Username(properties={
                "username": username,
                "platform": "x", 
                "link": url,
                "source": f"UsernameToWebsite transform ({result['source']})"
            })
        else:
            return Website(properties={
                "url": url,
                "domain": domain,
                "title": result["title"],
                "description": result["description"],
                "source": f"UsernameToWebsite transform ({result['source']})"
            })
    
    def _run_sync(self, entity: Username, graph) -> List[Entity]:
        """Synchronous implementation for CPU-bound operations"""
        username = entity.properties.get("username", "")
        
        # Collect search results
        status = StatusManager.get()
        operation_id = status.start_loading("Username Search")
        status.set_text("Searching for username...")
        search_results = []
        search_results.extend(self._search_bing(username))
        search_results.extend(self._search_google(username))
        status.set_text(f"Username search done with {len(search_results)} results")
        status.stop_loading(operation_id)

        # Process results and create entities
        entities = []
        for result in search_results:
            try:
                entity = self._create_entity(result)
                entities.append(entity)
            except Exception:
                continue
                
        return entities