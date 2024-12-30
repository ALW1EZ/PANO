from dataclasses import dataclass, field
from typing import ClassVar, List
from .base import Transform
from entities.base import Entity
from entities.person import Person
from entities.email import Email

@dataclass
class EmailToPerson(Transform):
    name: ClassVar[str] = "Email to Person"
    description: ClassVar[str] = "Extract person information from email address"
    input_types: ClassVar[List[str]] = ["Email"]
    output_types: ClassVar[List[str]] = ["Person"]
    
    async def run(self, entity: Email, graph) -> List[Entity]:
        if not isinstance(entity, Email):
            return []
            
        email_address = entity.properties.get("address", "")
        if not email_address or "@" not in email_address:
            return []
            
        # Extract name from email (e.g., john.doe@example.com -> John Doe)
        name_part = email_address.split("@")[0]
        name_parts = name_part.replace(".", " ").replace("_", " ").split()
        full_name = " ".join(part.capitalize() for part in name_parts)
        
        # Create person entity
        person = Person(
            label=f"{full_name}",
            properties={
                "full_name": full_name,
                "source": "Email transform",
            }
        )
        
        # Return the new entity - let the UI handle graph operations
        return [person] 