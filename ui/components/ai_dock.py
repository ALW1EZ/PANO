from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTextEdit, QScrollBar
from PySide6.QtCore import Signal, QPointF, Qt
from PySide6.QtGui import QColor
import g4f
import asyncio
import json
import logging
import math
import re
from typing import Dict, List, Optional, Any

from entities import ENTITY_TYPES
from ..managers.graph_manager import GraphManager
from ..managers.timeline_manager import TimelineManager

logger = logging.getLogger(__name__)

# Basic JSON template for the response format
RESPONSE_FORMAT = '''{
    "action": "create",
    "entities": [
        {
            "type": "Entity Type",
            "properties": {
                "property_name": "property_value"
            }
        }
    ],
    "connections": [
        {
            "from": 0,
            "to": 1,
            "relationship": "relationship_type"
        }
    ]
}'''

class AIDock(QWidget):
    """
    AI-powered dock for natural language graph manipulation.
    Allows users to describe scenarios in natural language and automatically creates
    corresponding graph entities and relationships.
    """
    
    entities_updated = Signal()
    processing_started = Signal()
    processing_finished = Signal()
    
    def __init__(self, graph_manager: Optional[GraphManager] = None, 
                 timeline_manager: Optional[TimelineManager] = None, 
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.graph_manager = graph_manager
        self.timeline_manager = timeline_manager
        self.entity_info = self._build_entity_info()
        self._setup_ui()
        self._setup_styles()
        
    def _setup_ui(self) -> None:
        """Initialize and configure UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setVerticalScrollBar(QScrollBar())
        layout.addWidget(self.chat_area)
        
        self.input_area = QLineEdit()
        self.input_area.setPlaceholderText("Describe what happened...")
        self.input_area.returnPressed.connect(self._handle_input)
        layout.addWidget(self.input_area)
        
    def _setup_styles(self) -> None:
        """Apply styles to UI components"""
        self.setStyleSheet("""
            AIDock {
                background-color: #1e1e1e;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: none;
                padding: 10px;
            }
            QLineEdit {
                background-color: #363636;
                color: white;
                border: none;
                border-radius: 5px;
                margin-top: 5px;
            }
        """)

    def _build_entity_info(self) -> Dict[str, Dict[str, Any]]:
        """Build information about available entities and their properties"""
        entity_info = {}
        
        for entity_name, entity_class in ENTITY_TYPES.items():
            try:
                temp_instance = entity_class()
                temp_instance.init_properties()
                
                properties = {
                    prop_name: prop_type.__name__
                    for prop_name, prop_type in temp_instance.property_types.items()
                }
                
                entity_info[entity_name] = {
                    'description': entity_class.description,
                    'properties': properties
                }
                
            except Exception as e:
                logger.error(f"Error processing entity {entity_name}: {str(e)}")
                continue
            
        return entity_info

    def _add_message(self, text: str, is_user: bool = True) -> None:
        """Add a message to the chat area"""
        color = "#e0e0e0" if is_user else "#90CAF9"
        prefix = "You:" if is_user else "PANAI:"
        self.chat_area.append(f'<span style="color: {color}"><b>{prefix}</b> {text}</span>')
        
        scrollbar = self.chat_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    async def _try_model(self, model: str, system_prompt: str, user_text: str) -> Optional[str]:
        """Try to get a response from a specific model"""
        try:
            response = await g4f.ChatCompletion.create_async(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ]
            )
            return response
        except Exception as e:
            logger.error(f"Model {model} failed: {str(e)}")
            return None

    async def _process_with_g4f(self, text: str) -> Optional[Dict[str, Any]]:
        """Process user input with G4F using fallback models"""
        try:
            # Build entity descriptions including existing entities
            type_descriptions = []
            existing_entities = []
            
            for entity_name, info in self.entity_info.items():
                props = [f"{name} ({type_name})" for name, type_name in info['properties'].items()]
                type_descriptions.append(f"{entity_name}:")
                type_descriptions.append(f"  Description: {info['description']}")
                type_descriptions.append(f"  Properties: {', '.join(props)}")
            
            # Add information about existing entities
            if self.graph_manager:
                for node in self.graph_manager.nodes.values():
                    existing_entities.append(f"- {node.node.type}: {node.node.label}")

            system_prompt = f"""You are an advanced AI investigator that helps analyze and map complex scenarios in a graph database.
Your task is to understand relationships, events, and entities, creating a coherent graph representation.

Available entity types and their properties:
{chr(10).join(type_descriptions)}

Current graph state:
{chr(10).join(existing_entities)}

CORE PRINCIPLES:
1. NEVER infer or guess - only use explicitly stated information
2. ALWAYS update existing entities instead of creating duplicates
3. NEVER add properties unless explicitly mentioned
4. ALWAYS use UPPERCASE for relationship types
5. ALWAYS create relationship chains that tell a complete story

ADVANCED REASONING PATTERNS:

1. Event Chains:
   When multiple events are connected:
   | Event1 -[LEADS_TO]-> Event2 -[LEADS_TO]-> Event3
   | Entity -[INVOLVED_IN]-> Event1
   | Entity -[ALSO_INVOLVED_IN]-> Event2
   Example: "After receiving the threat, Alice disappeared from the airport"
   | Text: "Threat message" -[PRECEDES]-> Event: "Alice Disappearance"
   | Location: "Airport" -[LOCATION_OF]-> Event: "Alice Disappearance"

2. Entity State Changes:
   When entities change over time:
   | Entity(before) -[BECOMES]-> Entity(after)
   | Event -[CAUSES]-> State_Change
   Example: "Julia's real name was Emily"
   Action: update
   | Update Person "Julia" to "Emily"
   | Preserve all existing relationships

3. Complex Relationships:
   When entities have multiple relationship layers:
   | Person1 -[RELATIONSHIP]-> Person2
   | Person1 -[OWNS]-> Object -[USED_BY]-> Person2
   Example: "John's black SUV was used to kidnap Alice"
   | John -[OWNS]-> Vehicle: "SUV"
   | SUV -[USED_IN]-> Event: "Alice Kidnapping"
   | Alice -[VICTIM_OF]-> Event

4. Information Flow:
   For communication and information exchange:
   | Source -[SENDS]-> Message -[RECEIVED_BY]-> Target
   | Message -[CONTAINS]-> Information
   | Message -[RELATES_TO]-> Event
   Example: "KClown sent a threatening message to Alice"
   | Username: "KClown" -[SENDS]-> Text: "Threat"
   | Text -[RECEIVED_BY]-> Person: "Alice"
   | Text -[TYPE]-> "THREAT"

5. Location Sequences:
   For tracking movement and locations:
   | Person -[AT]-> Location1 -[THEN_AT]-> Location2
   | Location -[PART_OF]-> Larger_Location
   Example: "Alice left New York airport and went to the parking lot"
   | Alice -[DEPARTS]-> Location: "New York Airport"
   | Alice -[ARRIVES_AT]-> Location: "Parking Lot"
   | "Parking Lot" -[PART_OF]-> "New York Airport"

6. Temporal Relationships:
   For time-based connections:
   | Event1 -[BEFORE]-> Event2 -[BEFORE]-> Event3
   | Entity -[STATE_AT(Event1)]-> State1
   | Entity -[STATE_AT(Event2)]-> State2
   Example: "Before disappearing, Alice received a threat"
   | Text: "Threat" -[PRECEDES]-> Event: "Disappearance"
   | Alice -[RECEIVES]-> Text
   | Alice -[VICTIM_OF]-> Event

RESPONSE RULES:
1. For new information:
   - Use "create" action
   - Only include explicitly mentioned properties
   - Connect to existing entities when possible

2. For updates:
   - Use "update" action
   - Only update specifically mentioned properties
   - Preserve all existing relationships

3. For relationships:
   - Use meaningful, descriptive relationship types
   - Create complete chains of relationships
   - Connect related events chronologically

Response format must be a JSON object with one of these structures:

For creating new entities:
{RESPONSE_FORMAT}

For updating existing entities:
{{
    "action": "update",
    "updates": [
        {{
            "type": "Entity Type",
            "current_label": "Current Entity Label",
            "new_properties": {{
                "property_name": "new_value"
            }}
        }}
    ]
}}

Process this text: {text}"""

            # List of models to try in order
            models = [
                "gpt-3.5-turbo",
                "llama_3_1_70b",
                "gpt-4",
                "mixtral-8x7b",
                "gemini-pro",
                "claude-2"
            ]

            # Try each model until one succeeds
            for model in models:
                response = await self._try_model(model, system_prompt, text)
                if response:
                    return self._parse_g4f_response(response)
                logger.warning(f"Model {model} failed, trying next model")
            
            logger.error("All models failed")
            return None
            
        except Exception as e:
            logger.error(f"Error in G4F call: {str(e)}")
            return None

    def _parse_g4f_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse and validate the G4F response"""
        try:
            json_str = response.strip()
            
            # Find the outermost valid JSON object
            stack = []
            start = -1
            end = -1
            
            for i, char in enumerate(json_str):
                if char == '{':
                    if start == -1:
                        start = i
                    stack.append(char)
                elif char == '}':
                    if stack:
                        stack.pop()
                        if not stack:  # Found complete JSON object
                            end = i + 1
                            break
            
            if start != -1 and end != -1:
                json_str = json_str[start:end]
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # Remove trailing commas
                json_str = re.sub(r'"\s*\.\s*}', '"}', json_str)    # Fix period before closing brace
                json_str = re.sub(r'"\s*\.\s*,', '",', json_str)    # Fix period before comma
                json_str = re.sub(r'\s+', ' ', json_str)            # Normalize whitespace
                
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try to fix common quote issues
                    json_str = re.sub(r'(?<!\\)"(?![:,}\]])\s*([^"]*?)\s*(?<!\\)"', r'"\1"', json_str)
                    data = json.loads(json_str)
                
                # Validate structure based on action type
                if "action" not in data:
                    logger.error("Missing action in response")
                    return None
                    
                if data["action"] == "create" and "entities" in data:
                    return data
                elif data["action"] == "update" and "updates" in data:
                    return data
                
                logger.error(f"Invalid JSON structure: {json_str}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            logger.error(f"Problematic JSON: {json_str}")
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            logger.debug(f"Full response: {response}")
            
        return None

    def _find_matching_entity(self, entity_type: str, label: str, nodes: Dict[str, Any]) -> Optional[Any]:
        """Find a matching entity node using flexible matching"""
        label = label.lower()
        # Try exact match first
        key = f"{entity_type}:{label}"
        if key in nodes:
            return nodes[key]
            
        # Try partial matches
        for node_key, node in nodes.items():
            node_type, node_label = node_key.split(':', 1)
            if node_type == entity_type.lower():
                # Check if the search label is part of the node label
                if label in node_label or node_label in label:
                    return node
                # For Person entities, check if first name matches
                if entity_type == "Person" and label.split()[0].lower() in node_label.split():
                    return node
        return None

    def _update_entities(self, data: Dict[str, Any]) -> Dict[str, List]:
        """Update existing entities with new properties"""
        try:
            updated_entities = []
            updated_nodes = []
            
            if not self.graph_manager:
                return {'entities': [], 'nodes': [], 'edges': []}
            
            # Create lookup for existing entities
            existing_entities = {}
            for node in self.graph_manager.nodes.values():
                key = f"{node.node.type}:{node.node.label}".lower()
                existing_entities[key] = node
            
            # Process updates
            for update in data.get("updates", []):
                try:
                    entity_type = update["type"]
                    current_label = update["current_label"]
                    new_properties = update.get("new_properties", {})
                    
                    # Find existing entity using flexible matching
                    existing_node = self._find_matching_entity(entity_type, current_label, existing_entities)
                    
                    if existing_node:
                        # Update properties
                        existing_node.node.properties.update(new_properties)
                        existing_node.node.update_label()
                        
                        # Force visual updates
                        try:
                            # Update main label
                            if hasattr(existing_node, 'label'):
                                existing_node.label.setPlainText(existing_node.node.label)
                            
                            # Update type label
                            if hasattr(existing_node, 'type_label'):
                                existing_node.type_label.setPlainText(existing_node.node.type_label)
                            
                            # Update properties display
                            if hasattr(existing_node, 'properties_item'):
                                # Get formatted properties text
                                props_text = []
                                for key, value in existing_node.node.properties.items():
                                    if key not in ['notes', 'source', 'image'] and value:
                                        props_text.append(f"{key}: {value}")
                                if props_text:
                                    existing_node.properties_item.setPlainText('\n'.join(props_text))
                            
                            # Update geometry and visuals
                            existing_node.update()
                            if hasattr(existing_node, 'updateGeometry'):
                                existing_node.updateGeometry()
                            if hasattr(existing_node, '_update_layout'):
                                existing_node._update_layout()
                            
                            updated_entities.append(existing_node.node)
                            updated_nodes.append(existing_node)
                                                        
                        except Exception as e:
                            logger.error(f"Error updating visual components: {str(e)}")
                            # Continue with update even if visual update fails
                            updated_entities.append(existing_node.node)
                            updated_nodes.append(existing_node)
                    else:
                        logger.warning(f"Could not find entity {entity_type}:{current_label} to update")
                    
                except Exception as e:
                    logger.error(f"Error updating entity: {str(e)}")
                    continue
            
            # Trigger scene update if any entities were updated
            if updated_nodes and self.graph_manager and hasattr(self.graph_manager, 'view'):
                scene = self.graph_manager.view.scene
                if scene:
                    scene.update()
                    # Force layout update
                    for node in updated_nodes:
                        try:
                            if hasattr(node, '_update_layout'):
                                node._update_layout()
                            node.update()
                        except Exception as e:
                            logger.error(f"Error in final layout update: {str(e)}")
            
            return {'entities': updated_entities, 'nodes': updated_nodes, 'edges': []}
            
        except Exception as e:
            logger.error(f"Error in update_entities: {str(e)}")
            return {'entities': [], 'nodes': [], 'edges': []}

    def _create_entities(self, data: Dict[str, Any]) -> Dict[str, List]:
        """Create entities and relationships from AI response data"""
        try:
            entities = []
            nodes = []
            edges = []
            edge_pairs = set()
            
            # First pass: collect existing entities
            existing_entities = {}
            if self.graph_manager:
                for node in self.graph_manager.nodes.values():
                    key = f"{node.node.type}:{node.node.label}".lower()
                    existing_entities[key] = node
            
            # Create entities
            for i, entity_data in enumerate(data["entities"]):
                try:
                    entity_type = entity_data["type"]
                    if entity_type not in ENTITY_TYPES:
                        continue
                    
                    # Create a temporary entity to get its label
                    temp_entity = ENTITY_TYPES[entity_type]()
                    temp_entity.properties.update({k: v for k, v in entity_data.get("properties", {}).items() if v and v != "Unknown"})
                    temp_entity.update_label()
                    
                    # Check if entity already exists using flexible matching
                    existing_node = self._find_matching_entity(entity_type, temp_entity.label, existing_entities)
                    
                    if existing_node:
                        # Use existing entity but update its properties
                        existing_node.node.properties.update(temp_entity.properties)
                        existing_node.node.update_label()
                        nodes.append(existing_node)
                        entities.append(existing_node.node)
                    else:
                        # Create new entity
                        entity = ENTITY_TYPES[entity_type]()
                        entity.properties.update(temp_entity.properties)
                        entity.update_label()
                        
                        # Position in circular layout
                        angle = (2 * math.pi * len(nodes)) / max(len(data["entities"]), 1)
                        radius = 200
                        pos = QPointF(radius * math.cos(angle), radius * math.sin(angle))
                        
                        node = self.graph_manager.add_node(entity, pos)
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
                        
                        if source.node.id == target.node.id:
                            continue
                            
                        edge_pair = (source.node.id, target.node.id, relationship)
                        if edge_pair not in edge_pairs:
                            edge = self.graph_manager.add_edge(
                                source.node.id,
                                target.node.id,
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

    def _handle_input(self) -> None:
        """Handle user input and process it through the AI pipeline"""
        text = self.input_area.text().strip()
        if not text:
            return
            
        self._add_message(text, True)
        self.input_area.clear()
        self.processing_started.emit()
        
        async def process():
            try:
                data = await self._process_with_g4f(text)
                if not data:
                    self._add_message("Sorry, I couldn't understand that. Please try rephrasing.", False)
                    return
                    
                if data.get("action") == "create":
                    result = self._create_entities(data)
                elif data.get("action") == "update":
                    result = self._update_entities(data)
                else:
                    self._add_message("Unknown action type. Please try rephrasing.", False)
                    return
                
                if result['entities']:
                    self.entities_updated.emit()
                    
                    if data.get("action") == "update":
                        self._add_message("Updated:", False)
                    else:
                        self._add_message("Created:", False)
                        
                    for entity in result['entities']:
                        self._add_message(f"- {entity.type}: {entity.label}", False)
                    
                    # Report relationships for create action
                    if data.get("action") == "create" and result['edges']:
                        self._add_message("\nRelationships:", False)
                        for edge in result['edges']:
                            source = edge.source.node.label
                            target = edge.target.node.label
                            rel = edge.relationship
                            self._add_message(f"- {source} {rel} {target}", False)
                else:
                    self._add_message("No changes were made. Please try rephrasing.", False)
            finally:
                self.processing_finished.emit()
                
        asyncio.create_task(process()) 