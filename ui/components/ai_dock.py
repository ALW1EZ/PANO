from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTextEdit
from PySide6.QtCore import Signal, QPointF
import g4f
import asyncio
import json
import logging
import math
import re

from entities import ENTITY_TYPES

logger = logging.getLogger(__name__)

class AIDock(QWidget):
    """AI-powered dock for natural language graph manipulation"""
    
    entities_updated = Signal()
    
    def __init__(self, graph_manager=None, timeline_manager=None, parent=None):
        super().__init__(parent)
        self.graph_manager = graph_manager
        self._setup_ui()
        
        # Build entity knowledge at initialization
        self.entity_info = self._build_entity_info()
        
    def _setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat history
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: none;
                padding: 10px;
            }
        """)
        layout.addWidget(self.chat_area)
        
        # Input area
        self.input_area = QLineEdit()
        self.input_area.setPlaceholderText("Describe what happened...")
        self.input_area.setStyleSheet("""
            QLineEdit {
                background-color: #363636;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
        """)
        self.input_area.returnPressed.connect(self._handle_input)
        layout.addWidget(self.input_area)
        
    def _add_message(self, text: str, is_user: bool = True):
        """Add a message to the chat area"""
        color = "#e0e0e0" if is_user else "#90CAF9"
        prefix = "You:" if is_user else "AI:"
        self.chat_area.append(f'<span style="color: {color}"><b>{prefix}</b> {text}</span>')

    def _build_entity_info(self):
        """Build information about available entities and their properties"""
        entity_info = {}
        
        for entity_name, entity_class in ENTITY_TYPES.items():
            try:
                # Create temporary instance to access property info
                temp_instance = entity_class()
                temp_instance.init_properties()
                
                # Get property information
                properties = {}
                for prop_name, prop_type in temp_instance.property_types.items():
                    if prop_name not in ['notes', 'source', 'image']:  # Skip standard properties
                        properties[prop_name] = prop_type.__name__
                
                # Store entity info
                entity_info[entity_name] = {
                    'description': entity_class.description,
                    'properties': properties
                }
                
            except Exception as e:
                logger.error(f"Error processing entity {entity_name}: {str(e)}")
                continue
            
        return entity_info
        
    async def _process_with_g4f(self, text: str):
        """Process text with G4F to understand the intent"""
        try:
            # Build entity type descriptions
            type_descriptions = []
            for entity_name, info in self.entity_info.items():
                props = [f"{name} ({type_name})" for name, type_name in info['properties'].items()]
                type_descriptions.append(f"{entity_name}:")
                type_descriptions.append(f"  Description: {info['description']}")
                type_descriptions.append(f"  Properties: {', '.join(props)}")

            system_prompt = f"""You are an AI assistant that helps create and connect entities in an investigative graph database. Your task is to analyze the text and create appropriate entities and relationships.

Available entity types and their properties:
{chr(10).join(type_descriptions)}

Guidelines:
1. For violent events:
   - Create an Event with a clear descriptive name
   - Connect victims with "victim_of" relationship to the event
   - Connect perpetrators with "perpetrator_of" relationship to the event
   - Connect vehicles/weapons with "used_in" relationship to the event
   - Use "accomplice_of" for relationships between perpetrators

2. For vehicles:
   - Set color, make, model as properties
   - Connect to events with "used_in" relationship
   - Connect to owners with "owned_by" relationship

3. For relationships between people:
   - Use specific relationship types like "perpetrator_of", "victim_of", "accomplice_of"
   - Connect people to events rather than directly to each other for actions
   - Use "knows", "friend_of", "related_to" for social relationships

4. For events:
   - Include all relevant details in event name and description
   - Connect all involved entities to the event
   - Use proper relationship types for each entity's role

IMPORTANT: You must respond with ONLY a JSON object in this exact format:
{{
    "action": "create",
    "entities": [
        {{
            "type": "Event",
            "properties": {{
                "name": "Murder of Alice",
                "description": "Two men killed Alice using a black SUV"
            }}
        }},
        {{
            "type": "Vehicle",
            "properties": {{
                "type": "SUV",
                "color": "black"
            }}
        }}
    ],
    "connections": [
        {{
            "from": 1,
            "to": 0,
            "relationship": "used_in"
        }}
    ]
}}

DO NOT include any other text, comments, or explanations in your response. ONLY the JSON object.

Process this text: {text}"""

            response = await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            )
            
            # Clean and parse JSON
            try:
                # Remove any non-JSON text
                json_str = response.strip()
                
                # Find the first { and last }
                start = json_str.find('{')
                end = json_str.rfind('}')
                
                if start != -1 and end != -1:
                    json_str = json_str[start:end+1]
                    
                    # Remove any trailing commas before closing braces/brackets
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                    
                    # Parse JSON
                    data = json.loads(json_str)
                    
                    # Validate basic structure
                    if "action" in data and "entities" in data:
                        return data
                    
                    logger.error(f"Invalid JSON structure: {json_str}")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {str(e)}")
                logger.error(f"Problematic JSON: {json_str}")
                return None
            except Exception as e:
                logger.error(f"Error processing response: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Error in G4F call: {str(e)}")
            return None

    def _create_entities(self, data):
        """Create entities from AI response data"""
        try:
            entities = []
            nodes = []
            edges = []
            edge_pairs = set()  # Track created edge pairs to prevent duplicates
            
            # Create entities
            for i, entity_data in enumerate(data["entities"]):
                try:
                    # Get entity type and create instance
                    entity_type = entity_data["type"]
                    if entity_type not in ENTITY_TYPES:
                        logger.warning(f"Unknown entity type: {entity_type}")
                        continue
                        
                    entity_class = ENTITY_TYPES[entity_type]
                    entity = entity_class()
                    
                    # Set properties
                    for prop, value in entity_data.get("properties", {}).items():
                        if value and value != "Unknown":
                            entity.properties[prop] = value
                    
                    # Special handling for Event entities
                    if entity_type == "Event":
                        if "name" not in entity.properties:
                            if "description" in entity.properties:
                                entity.properties["name"] = entity.properties["description"]
                            else:
                                entity.properties["name"] = "Unknown Event"
                        # Ensure description exists
                        if "description" not in entity.properties:
                            entity.properties["description"] = entity.properties["name"]
                    
                    # Update label
                    entity.update_label()
                    
                    # Add to graph
                    angle = (2 * math.pi * i) / max(len(data["entities"]), 1)
                    x = 200 * math.cos(angle)
                    y = 200 * math.sin(angle)
                    node = self.graph_manager.add_node(entity, QPointF(x, y))
                    
                    entities.append(entity)
                    nodes.append(node)
                    
                except Exception as e:
                    logger.error(f"Error creating entity: {str(e)}")
                    continue
            
            # Create connections
            for conn in data.get("connections", []):
                try:
                    if 0 <= conn["from"] < len(nodes) and 0 <= conn["to"] < len(nodes):
                        source = nodes[conn["from"]]
                        target = nodes[conn["to"]]
                        relationship = conn.get("relationship", "")
                        
                        # Check if this edge pair already exists
                        edge_pair = (source.node.data.id, target.node.data.id, relationship)
                        if edge_pair not in edge_pairs:
                            edge = self.graph_manager.add_edge(
                                source.node.data.id,
                                target.node.data.id,
                                relationship
                            )
                            if edge:
                                edges.append(edge)
                                edge_pairs.add(edge_pair)
                            
                except Exception as e:
                    logger.error(f"Error creating connection: {str(e)}")
                    continue
            
            return {'entities': entities, 'nodes': nodes, 'edges': edges}
            
        except Exception as e:
            logger.error(f"Error in create_entities: {str(e)}")
            return {'entities': [], 'nodes': [], 'edges': []}

    def _handle_input(self):
        """Handle user input"""
        text = self.input_area.text().strip()
        if not text:
            return
            
        # Add user message and clear input
        self._add_message(text, True)
        self.input_area.clear()
        
        # Process with G4F
        async def process():
            data = await self._process_with_g4f(text)
            if data and data.get("action") == "create":
                result = self._create_entities(data)
                if result['entities']:
                    self.entities_updated.emit()
                    
                    # Report what was created
                    self._add_message("Created:", False)
                    for entity in result['entities']:
                        self._add_message(f"- {entity.type}: {entity.label}", False)
                    
                    if result['edges']:
                        self._add_message("\nRelationships:", False)
                        for edge in result['edges']:
                            source = edge.source.node.label
                            target = edge.target.node.label
                            rel = edge.relationship
                            self._add_message(f"- {source} {rel} {target}", False)
                else:
                    self._add_message("I couldn't create any entities. Please try rephrasing.", False)
            else:
                self._add_message("Sorry, I couldn't understand that. Please try rephrasing.", False)
                
        asyncio.create_task(process()) 