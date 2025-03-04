from typing import Dict, Any
import asyncio
import logging
from PySide6.QtCore import QPointF, Qt, QObject, Signal, QTimer
from PySide6.QtGui import QColor

from entities import Entity
from entities.event import Event
from entities.location import Location
from ..components.node_visual import NodeVisual
from ..components.edge_visual import EdgeVisual
from ..components.group_visual import GroupVisual
from ..dialogs.timeline_editor import TimelineEvent
from .map_manager import MapManager
from .group_manager import GroupManager
from ..components.node_visual import NodeVisualState

logger = logging.getLogger(__name__)

class GraphManager(QObject):
    """Manages the graph's nodes and edges"""
    nodes_changed = Signal()  # Signal emitted when nodes are added, removed, or cleared
    
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.nodes: Dict[str, NodeVisual] = {}
        self.edges: Dict[str, EdgeVisual] = {}
        self.groups: Dict[str, GroupVisual] = {}
        self.map_manager: MapManager | None = None
        self.group_manager = GroupManager(self)
        
        # Connect to group manager signals
        self.group_manager.groups_changed.connect(self._update_group_visuals)
        
    def set_map_manager(self, map_manager: MapManager) -> None:
        """Set the map manager instance"""
        self.map_manager = map_manager
        
    def add_node(self, entity: Entity, pos: QPointF) -> NodeVisual:
        """Add a new node to the graph"""
        if entity.id in self.nodes:
            logger.warning(f"Node {entity.id} already exists")
            return self.nodes[entity.id]
            
        node = NodeVisual(entity)
        node.setPos(pos)
        self.view.scene.addItem(node)
        self.nodes[entity.id] = node
        
        # Handle location entities
        if isinstance(entity, Location) and self.map_manager:
            self.map_manager.update_location(entity)
        
        # If it's an event with dates, add it to the timeline
        if isinstance(entity, Event):
            window = self.view.window()
            if hasattr(window, 'timeline_manager'):
                if entity.start_date and entity.end_date and entity.properties.get("add_to_timeline", True):
                    timeline_event = TimelineEvent(
                        name=entity.name,
                        description=entity.description or "",
                        start_time=entity.start_date,
                        end_time=entity.end_date,
                        color=QColor(entity.color)
                    )
                    timeline_event.source_entity_id = entity.id
                    window.timeline_manager.add_event(timeline_event)
        
        self.nodes_changed.emit()
        return node
        
    def add_edge(self, source_id: str, target_id: str, relationship: str = "") -> EdgeVisual | None:
        """Add a new edge between nodes"""
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.error(f"Cannot create edge: node not found")
            return None
            
        edge_id = f"{source_id}->{target_id}"
        if edge_id in self.edges:
            logger.warning(f"Edge {edge_id} already exists")
            return self.edges[edge_id]
            
        source = self.nodes[source_id]
        target = self.nodes[target_id]
        edge = EdgeVisual(source, target, relationship)
        self.view.scene.addItem(edge)
        self.edges[edge_id] = edge
        return edge
        
    def update_node(self, node_id: str, entity: Entity) -> None:
        """Update an existing node's entity"""
        if node_id not in self.nodes:
            logger.warning(f"Node {node_id} not found")
            return
            
        node = self.nodes[node_id]
        old_entity = node.node
        node.node = entity
        node.update()
        
        # Handle location entities
        if isinstance(entity, Location) and self.map_manager:
            self.map_manager.update_location(entity)
            
        # Update any groups containing this node
        self._update_group_visuals()
        
    def remove_node(self, node_id: str) -> None:
        """Remove a node and its connected edges from the graph"""
        if node_id not in self.nodes:
            logger.warning(f"Node {node_id} not found")
            return
            
        node = self.nodes[node_id]
        
        # Handle location entities
        if isinstance(node.node, Location) and self.map_manager:
            self.map_manager.remove_location(node_id)
            
        # Remove connected edges first
        edges_to_remove = []
        for edge_id, edge in self.edges.items():
            if (edge.source.node.id == node_id or 
                edge.target.node.id == node_id):
                edges_to_remove.append(edge_id)
                
        for edge_id in edges_to_remove:
            edge = self.edges.pop(edge_id)
            self.view.scene.removeItem(edge)
            
        # Remove from any groups
        for group in self.group_manager.groups.values():
            group.remove_node(node_id)
            
        # Remove the node
        self.nodes.pop(node_id)
        
        # If it's an event node, remove its timeline event
        if isinstance(node.node, Event):
            window = self.view.window()
            if hasattr(window, 'timeline_manager'):
                timeline_manager = window.timeline_manager
                existing_events = [e for e in timeline_manager.get_events() 
                                 if getattr(e, 'source_entity_id', None) == node_id]
                for event in existing_events:
                    timeline_manager.timeline_widget.delete_event(event)
        
        self.view.scene.removeItem(node)
        self.nodes_changed.emit()
        
    def clear(self) -> None:
        """Clear all nodes and edges from the graph"""
        # Clear edges first
        for edge in self.edges.values():
            self.view.scene.removeItem(edge)
        self.edges.clear()
        
        # Clear nodes
        for node in self.nodes.values():
            self.view.scene.removeItem(node)
        self.nodes.clear()
        
        # Clear groups
        self.group_manager.groups.clear()
        for group in self.groups.values():
            self.view.scene.removeItem(group)
        self.groups.clear()
        
        self.nodes_changed.emit()
        
    def _update_group_visuals(self) -> None:
        """Update visual representations of all groups"""
        # Remove old group visuals
        for group in self.groups.values():
            self.view.scene.removeItem(group)
        self.groups.clear()
        
        # Create new group visuals
        for group in self.group_manager.groups.values():
            visual = GroupVisual(group, self)
            self.view.scene.addItem(visual)
            self.groups[group.id] = visual
            
    async def from_dict(self, data: Dict[str, Any]) -> None:
        """Restore graph state from a dictionary"""
        self.clear()
        
        # First restore all nodes
        for node_id, node_data in data['nodes'].items():
            entity = Entity.from_dict(node_data['entity'])
            pos = QPointF(
                node_data['pos']['x'],
                node_data['pos']['y']
            )
            self.add_node(entity, pos)
            
        # Then restore edges
        for edge_id, edge_data in data['edges'].items():
            edge = self.add_edge(
                edge_data['source'],
                edge_data['target'],
                edge_data['relationship']
            )
            # Restore edge style if present
            if 'style' in edge_data and edge:
                edge.style.style = Qt.PenStyle(edge_data['style'])
                
        # Finally restore groups if present
        if 'groups' in data:
            self.group_manager.from_dict(data['groups'])
            
        # Allow UI to update
        await asyncio.sleep(0)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph state to a dictionary"""
        return {
            'nodes': {
                node_id: {
                    'entity': node.node.to_dict(),
                    'pos': {'x': node.pos().x(), 'y': node.pos().y()}
                }
                for node_id, node in self.nodes.items()
            },
            'edges': {
                edge_id: {
                    'source': edge.source.node.id,
                    'target': edge.target.node.id,
                    'relationship': edge.relationship,
                    'style': edge.style.style.value if hasattr(edge.style, 'style') else None
                }
                for edge_id, edge in self.edges.items()
            },
            'groups': self.group_manager.to_dict()
        }
        
    def center_on_node(self, node: NodeVisual) -> None:
        """Center the view on a specific node"""
        if not node:
            return
            
        # Get the node's scene position
        node_pos = node.scenePos()
        
        # Center the view on the node
        self.view.centerOn(node_pos)
        
        # Set zoom level to 2x
        current_transform = self.view.transform()
        current_scale = current_transform.m11() # Get current horizontal scale
        scale_factor = 2.0 / current_scale # Calculate factor needed to reach 2x
        self.view.scale(scale_factor, scale_factor)
