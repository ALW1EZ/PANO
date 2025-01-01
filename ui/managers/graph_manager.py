from typing import Dict, Any
import asyncio
import logging
from PyQt6.QtCore import QPointF, Qt

from entities import Entity
from ..components.node_visual import NodeVisual
from ..components.edge_visual import EdgeVisual

logger = logging.getLogger(__name__)

class GraphManager:
    def __init__(self, view):
        self.view = view
        self.nodes: Dict[str, NodeVisual] = {}
        self.edges: Dict[str, EdgeVisual] = {}
        
    def add_node(self, entity: Entity, pos: QPointF) -> NodeVisual:
        """Add a new node to the graph"""
        if entity.id in self.nodes:
            logger.warning(f"Node {entity.id} already exists")
            return self.nodes[entity.id]
            
        node = NodeVisual(entity)
        node.setPos(pos)
        self.view.scene.addItem(node)
        self.nodes[entity.id] = node
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
        
    def remove_node(self, node_id: str) -> None:
        """Remove a node and its connected edges from the graph"""
        if node_id not in self.nodes:
            logger.warning(f"Node {node_id} not found")
            return
            
        # Remove connected edges first
        edges_to_remove = []
        for edge_id, edge in self.edges.items():
            if (edge.source.node.id == node_id or 
                edge.target.node.id == node_id):
                edges_to_remove.append(edge_id)
                
        for edge_id in edges_to_remove:
            edge = self.edges.pop(edge_id)
            self.view.scene.removeItem(edge)
            
        # Remove the node
        node = self.nodes.pop(node_id)
        self.view.scene.removeItem(node)
        
    def clear(self) -> None:
        """Clear all nodes and edges from the graph"""
        # Clear edges first to avoid dangling references
        for edge in self.edges.values():
            self.view.scene.removeItem(edge)
        self.edges.clear()
        
        # Then clear nodes
        for node in self.nodes.values():
            self.view.scene.removeItem(node)
        self.nodes.clear()
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph state to a dictionary"""
        nodes_data = {}
        for node_id, node in self.nodes.items():
            nodes_data[node_id] = {
                'entity': node.node.to_dict(),
                'pos': {
                    'x': node.pos().x(),
                    'y': node.pos().y()
                }
            }
            
        edges_data = {}
        for edge_id, edge in self.edges.items():
            edges_data[edge_id] = {
                'source': edge.source.node.id,
                'target': edge.target.node.id,
                'relationship': edge.relationship,
                'style': edge.style.style.value
            }
            
        return {
            'nodes': nodes_data,
            'edges': edges_data
        }
        
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
            
        # Allow UI to update
        await asyncio.sleep(0) 