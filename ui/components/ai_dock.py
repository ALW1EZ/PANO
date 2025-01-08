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
from datetime import datetime, timedelta

from entities import ENTITY_TYPES
from ..managers.graph_manager import GraphManager
from ..managers.timeline_manager import TimelineManager

logger = logging.getLogger(__name__)

def get_relative_datetime(reference_time: datetime, offset_hours: int = 0) -> str:
    """Calculate a datetime relative to a reference time"""
    result_time = reference_time + timedelta(hours=offset_hours)
    return result_time.strftime("%Y-%m-%d %H:%M")

# Basic JSON template for the response format
RESPONSE_FORMAT = '''{
    "operations": [
        {
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
        },
        {
            "action": "update",
            "updates": [
                {
                    "type": "Entity Type",
                    "current_label": "Current Entity Label",
                    "new_properties": {
                        "property_name": "new_value"
                    }
                }
            ]
        }
    ]
}'''

class AIDock(QWidget):
    """AI-powered dock for natural language graph manipulation"""
    
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
        self.last_event_time = None  # Track the last event time for relative references
        
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

            # Get current time for reference
            current_time = datetime.now()
            # Use last event time if available, otherwise use current time
            reference_time = self.last_event_time or current_time

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
6. ALWAYS create events for events or incidents with type "Event" and appropriate name property

DATE AND TIME RULES:
1. All event dates MUST be in format "YYYY-MM-DD HH:mm" (e.g. "2023-12-25 14:30")
2. Current reference time is {reference_time.strftime("%Y-%m-%d %H:%M")}
3. For "last night" or "yesterday", use {(reference_time - timedelta(days=1)).strftime("%Y-%m-%d")} 20:00
4. For "this morning", use {reference_time.strftime("%Y-%m-%d")} 08:00
5. For relative times (e.g. "X hours later"), add to the last event time
6. For ongoing events, use the reference time
7. If no specific time given, use 00:00 for start and end times

Response format must be a JSON object with one of these structures:
{RESPONSE_FORMAT}

Process this text: {text}"""

            # List of models to try in order
            models = [
                "gpt-4",
            ]

            # Try each model until one succeeds
            for model in models:
                response = await self._try_model(model, system_prompt, text)
                if response:
                    data = self._parse_g4f_response(response)
                    if data:
                        # Update last event time if this was a successful event creation
                        for operation in data.get("operations", []):
                            if operation.get("action") == "create":
                                for entity in operation.get("entities", []):
                                    if entity.get("type") == "Event":
                                        props = entity.get("properties", {})
                                        if "end_date" in props:
                                            try:
                                                self.last_event_time = datetime.strptime(props["end_date"], "%Y-%m-%d %H:%M")
                                            except (ValueError, TypeError):
                                                pass
                    return data
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
                
                # Support both old and new format
                if "operations" in data:
                    return data
                elif "action" in data:
                    # Convert old format to new format
                    return {"operations": [data]}
                
                logger.error(f"Invalid JSON structure: {json_str}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            logger.error(f"Problematic JSON: {json_str}")
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            logger.debug(f"Full response: {response}")
            
        return None

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison by removing special chars and extra spaces"""
        # Convert to lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text

    def _get_similarity_score(self, words1: set, words2: set) -> float:
        """Calculate similarity score between two sets of words"""
        if not words1 or not words2:
            return 0.0
            
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        jaccard = intersection / union if union > 0 else 0
        
        # Calculate word length similarity
        avg_len1 = sum(len(word) for word in words1) / len(words1)
        avg_len2 = sum(len(word) for word in words2) / len(words2)
        len_ratio = min(avg_len1, avg_len2) / max(avg_len1, avg_len2)
        
        # Calculate overlap coefficient
        overlap = intersection / min(len(words1), len(words2)) if min(len(words1), len(words2)) > 0 else 0
        
        # Combine scores with weights
        return (jaccard * 0.4 + len_ratio * 0.2 + overlap * 0.4)

    def _find_matching_entity(self, entity_type: str, label: str, nodes: Dict[str, Any]) -> Optional[Any]:
        """Find a matching entity node using flexible matching"""
        entity_type = entity_type.lower()
        normalized_label = self._normalize_text(label)
        label_words = set(normalized_label.split())
        
        # Try exact match first with consistent key format
        key = f"{entity_type}:{label.lower()}"
        if key in nodes:
            return nodes[key]
        
        best_match = None
        best_score = 0.0
        
        # Try finding best match
        for node_key, node in nodes.items():
            try:
                # Ensure consistent key format for comparison
                node_type, node_label = node_key.lower().split(':', 1)
                
                if node_type != entity_type:
                    continue
                    
                normalized_node_label = self._normalize_text(node_label)
                node_words = set(normalized_node_label.split())
                
                # Calculate similarity score
                score = self._get_similarity_score(label_words, node_words)
                
                # For events, boost score if they share significant words
                if entity_type == "event":
                    # Get the most significant (longest) words from each label
                    sig_words1 = {w for w in label_words if len(w) > 4}
                    sig_words2 = {w for w in node_words if len(w) > 4}
                    if sig_words1 & sig_words2:
                        score *= 1.5
                
                # For persons, boost score if first words match
                elif entity_type == "person" and label_words and node_words:
                    if list(label_words)[0] == list(node_words)[0]:
                        score *= 1.5
                
                # Update best match if score is high enough
                threshold = 0.5 if entity_type == "event" else 0.7
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = node
                    
            except ValueError:
                continue  # Skip malformed keys
        
        return best_match

    def _update_node_visuals(self, node) -> None:
        """Update all visual components of a node"""
        try:
            # Update main label
            if hasattr(node, 'label'):
                node.label.setPlainText(node.node.label)
            
            # Update type label
            if hasattr(node, 'type_label'):
                node.type_label.setPlainText(node.node.type_label)
            
            # Update properties display
            if hasattr(node, 'properties_item'):
                props_text = []
                for key, value in node.node.properties.items():
                    if key not in ['notes', 'source', 'image'] and value:
                        props_text.append(f"{key}: {value}")
                if props_text:
                    node.properties_item.setPlainText('\n'.join(props_text))
            
            # Update geometry and visuals
            node.update()
            if hasattr(node, 'updateGeometry'):
                node.updateGeometry()
            if hasattr(node, '_update_layout'):
                node._update_layout()
                
        except Exception as e:
            logger.error(f"Error updating visual components: {str(e)}")

    def _refresh_scene(self, nodes: List[Any]) -> None:
        """Refresh the scene and update all node layouts"""
        if nodes and self.graph_manager and hasattr(self.graph_manager, 'view'):
            scene = self.graph_manager.view.scene
            if scene:
                scene.update()
                # Force layout update for all nodes
                for node in nodes:
                    try:
                        self._update_node_visuals(node)
                    except Exception as e:
                        logger.error(f"Error in final layout update: {str(e)}")

    def _update_entities(self, data: Dict[str, Any]) -> Dict[str, List]:
        """Update existing entities with new properties"""
        try:
            updated_entities = []
            updated_nodes = []
            
            if not self.graph_manager:
                return {'entities': [], 'nodes': [], 'edges': []}
            
            # Create lookup for existing entities with consistent key format
            existing_entities = {}
            for node in self.graph_manager.nodes.values():
                # Ensure consistent key format
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
                        
                        # Update visuals
                        self._update_node_visuals(existing_node)
                        
                        updated_entities.append(existing_node.node)
                        updated_nodes.append(existing_node)
                    else:
                        logger.warning(f"Could not find entity {entity_type}:{current_label} to update")
                    
                except Exception as e:
                    logger.error(f"Error updating entity: {str(e)}")
                    continue
            
            # Refresh scene
            self._refresh_scene(updated_nodes)
            
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
            
            # First pass: collect existing entities with consistent key format
            existing_entities = {}
            if self.graph_manager:
                for node in self.graph_manager.nodes.values():
                    # Ensure consistent key format
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
                    
                    # Update properties
                    temp_entity.properties.update({k: v for k, v in entity_data.get("properties", {}).items() if v and v != "Unknown"})
                    temp_entity.update_label()
                    
                    # Check if entity already exists using flexible matching
                    existing_node = self._find_matching_entity(entity_type, temp_entity.label, existing_entities)
                    
                    if existing_node:
                        # Use existing entity but update its properties
                        existing_node.node.properties.update(temp_entity.properties)
                        existing_node.node.update_label()
                        self._update_node_visuals(existing_node)
                        nodes.append(existing_node)
                        entities.append(existing_node.node)
                        # Update lookup with new label if it changed
                        key = f"{existing_node.node.type}:{existing_node.node.label}".lower()
                        existing_entities[key] = existing_node
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
                        self._update_node_visuals(node)
                        entities.append(entity)
                        nodes.append(node)
                        # Add to lookup
                        key = f"{entity.type}:{entity.label}".lower()
                        existing_entities[key] = node
                    
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
            
            # Refresh scene
            self._refresh_scene(nodes)
            
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
                
                all_entities = []
                all_edges = []
                
                # Process each operation in sequence
                for operation in data.get("operations", []):
                    action = operation.get("action")
                    if action == "create":
                        result = self._create_entities(operation)
                        all_entities.extend(result['entities'])
                        all_edges.extend(result['edges'])
                    elif action == "update":
                        result = self._update_entities(operation)
                        all_entities.extend(result['entities'])
                
                if all_entities:
                    self.entities_updated.emit()
                    
                    # Report all changes
                    self._add_message("Changes made:", False)
                    for entity in all_entities:
                        self._add_message(f"- {entity.type}: {entity.label}", False)
                    
                    if all_edges:
                        self._add_message("\nRelationships:", False)
                        for edge in all_edges:
                            source = edge.source.node.label
                            target = edge.target.node.label
                            rel = edge.relationship
                            self._add_message(f"- {source} {rel} {target}", False)
                else:
                    self._add_message("No changes were made. Please try rephrasing.", False)
            finally:
                self.processing_finished.emit()
                
        asyncio.create_task(process()) 