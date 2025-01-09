from dataclasses import dataclass, field
from typing import ClassVar, List
import requests
import aiohttp
from bs4 import BeautifulSoup
from .base import Transform
from entities.base import Entity
from entities.website import Website
from entities.username import Username

@dataclass
class UsernameToWebsite(Transform):
    name: ClassVar[str] = "Username to Website"
    description: ClassVar[str] = "Extract website from username"
    input_types: ClassVar[List[str]] = ["Username"]
    output_types: ClassVar[List[str]] = ["Website"]
    
    async def run(self, entity: Username, graph) -> List[Entity]:
        """Async implementation using aiohttp"""
        if not isinstance(entity, Username):
            return []
        
        username = entity.properties.get("username", "")
        if not username:
            return []
        
        # Use run_in_thread for BeautifulSoup parsing which is CPU-bound
        return await self.run_in_thread(entity, graph)
    
    def _run_sync(self, entity: Username, graph) -> List[Entity]:
        """Synchronous implementation for CPU-bound operations"""
        username = entity.properties.get("username", "")
        search_url = f"https://www.bing.com/search?q={username}"
        
        # Use requests in the sync version
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("li", class_="b_algo")
        websites = []
        
        for result in results:
            url = result.find("a")["href"]
            domain = url.split("/")[2]
            title = result.find("h2").text
            description = result.find("p").text
            website = Website(properties={
                "url": url,
                "domain": domain,
                "title": title,
                "description": description,
                "source": "UsernameToWebsite transform"
            })
            websites.append(website)
        
        return websites