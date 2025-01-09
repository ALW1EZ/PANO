from dataclasses import dataclass, field
from typing import ClassVar, List
import requests
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
        if not isinstance(entity, Username):
            return []
        
        username = entity.properties.get("username", "")
        if not username:
            return []
        
        # take username and search with bing
        search_url = f"https://www.bing.com/search?q={username}"
        response = requests.get(search_url)
        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.find_all("li", class_="b_algo")[:3]
        websites = []
        for result in results:
            url = result.find("a")["href"]
            domain = url.split("/")[2]
            title = result.find("h2").text
            description_elem = result.find("p", class_="b_lineclamp2")
            description = description_elem.get_text(strip=True) if description_elem else ""
            website = Website(properties={"url": url, "domain": domain, "title": title, "description": description, "source": "UsernameToWebsite transform"})
            websites.append(website)
        
        return websites