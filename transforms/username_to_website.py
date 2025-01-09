from dataclasses import dataclass, field
from typing import ClassVar, List
from googlesearch import search
from urllib.parse import urlparse
from .base import Transform
from entities.base import Entity
from entities.website import Website
from entities.username import Username

@dataclass
class UsernameToWebsite(Transform):
    name: ClassVar[str] = "Username to Website"
    description: ClassVar[str] = "Extract website from username using Google Search"
    input_types: ClassVar[List[str]] = ["Username"]
    output_types: ClassVar[List[str]] = ["Website"]
    
    async def run(self, entity: Username, graph) -> List[Entity]:
        """Async implementation using googlesearch"""
        if not isinstance(entity, Username):
            return []
        
        username = entity.properties.get("username", "")
        if not username:
            return []
        
        # Use run_in_thread since googlesearch is synchronous
        return await self.run_in_thread(entity, graph)
    
    def _run_sync(self, entity: Username, graph) -> List[Entity]:
        """Synchronous implementation for Google search operations"""
        username = entity.properties.get("username", "")
        websites = []
        
        # Search Google for the username, limit to first 10 results
        try:
            search_results = search(username, num_results=10, safe=False)
        except Exception as e:
            print(f"Error searching for {username}: {e}")
            return []
        
        for url in search_results:
            try:
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                website = Website(properties={
                    "url": url,
                    "domain": domain,
                    "source": "UsernameToWebsite transform"
                })
                websites.append(website)
            except Exception as e:
                continue
        
        return websites