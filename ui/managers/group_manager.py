from PySide6.QtCore import QObject, Signal, QPointF
from PySide6.QtGui import QColor
from typing import Dict, List, Set, Optional
import logging

logger = logging.getLogger(__name__)

class NodeGroup:
    """Represents a group of nodes"""
    def __init__(self, group_id: str, name: str, color: QColor = QColor("#3d3d3d")):
        self.id = group_id
        self.name = name
        self.color = color
        self.nodes: Set[str] = set()  # Set of node IDs
        self.expanded: bool = True  # Changed to True by default
        self.center: QPointF = QPointF(0, 0)
        
    def add_node(self, node_id: str) -> None:
        """Add a node to the group"""
        self.nodes.add(node_id)
        
    def remove_node(self, node_id: str) -> None:
        """Remove a node from the group"""
        self.nodes.discard(node_id)
        
    def contains_node(self, node_id: str) -> bool:
        """Check if the group contains a node"""
        return node_id in self.nodes
        
    def to_dict(self) -> dict:
        """Convert group to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color.name(),
            "nodes": list(self.nodes),
            "expanded": self.expanded,
            "center": {"x": self.center.x(), "y": self.center.y()}
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'NodeGroup':
        """Create group from dictionary"""
        group = cls(data["id"], data["name"], QColor(data["color"]))
        group.nodes = set(data["nodes"])
        group.expanded = data["expanded"]
        group.center = QPointF(data["center"]["x"], data["center"]["y"])
        return group

class GroupManager(QObject):
    """Manages node groups and clustering"""
    
    groups_changed = Signal()  # Emitted when groups are modified
    
    def __init__(self, graph_manager):
        super().__init__()
        self.graph_manager = graph_manager
        self.groups: Dict[str, NodeGroup] = {}
        
    def create_group(self, name: str, node_ids: List[str], color: QColor = None) -> NodeGroup:
        """Create a new group containing the specified nodes"""
        # Generate unique group ID
        group_id = f"group_{len(self.groups)}"
        while group_id in self.groups:
            group_id = f"group_{len(self.groups) + 1}"
            
        # Create group with specified or default color
        if color is None:
            color = QColor("#3d3d3d")
        group = NodeGroup(group_id, name, color)
        
        # Add nodes to group
        for node_id in node_ids:
            if node_id in self.graph_manager.nodes:
                group.add_node(node_id)
                
        # Calculate group center based on node positions
        if group.nodes:
            total_x = 0
            total_y = 0
            for node_id in group.nodes:
                node = self.graph_manager.nodes[node_id]
                pos = node.pos()
                total_x += pos.x()
                total_y += pos.y()
            avg_x = total_x / len(group.nodes)
            avg_y = total_y / len(group.nodes)
            group.center = QPointF(avg_x, avg_y)
            
        self.groups[group_id] = group
        self.groups_changed.emit()
        return group
        
    def delete_group(self, group_id: str) -> None:
        """Delete a group"""
        if group_id in self.groups:
            del self.groups[group_id]
            self.groups_changed.emit()
            
    def add_node_to_group(self, group_id: str, node_id: str) -> None:
        """Add a node to an existing group"""
        if group_id in self.groups and node_id in self.graph_manager.nodes:
            self.groups[group_id].add_node(node_id)
            self.groups_changed.emit()
            
    def remove_node_from_group(self, group_id: str, node_id: str) -> None:
        """Remove a node from a group"""
        if group_id in self.groups:
            self.groups[group_id].remove_node(node_id)
            self.groups_changed.emit()
            
    def get_node_groups(self, node_id: str) -> List[NodeGroup]:
        """Get all groups that contain a node"""
        return [group for group in self.groups.values() if group.contains_node(node_id)]
        
    def toggle_group_expansion(self, group_id: str) -> None:
        """Toggle group expansion state"""
        if group_id in self.groups:
            group = self.groups[group_id]
            group.expanded = not group.expanded
            self.groups_changed.emit()
            
    def auto_group_by_type(self) -> None:
        """Automatically create groups based on entity types"""
        # Clear existing groups
        self.groups.clear()
        
        # Group nodes by type
        nodes_by_type = {}
        for node_id, node in self.graph_manager.nodes.items():
            entity_type = node.node.__class__.__name__
            if entity_type not in nodes_by_type:
                nodes_by_type[entity_type] = []
            nodes_by_type[entity_type].append(node_id)
            
        # Create a group for each type
        for entity_type, node_ids in nodes_by_type.items():
            if len(node_ids) > 1:  # Only create groups with multiple nodes
                self.create_group(f"{entity_type} Group", node_ids)
                
        self.groups_changed.emit()
        
    def auto_group_by_connectivity(self, min_group_size: int = 3) -> None:
        """Automatically create groups based on node connectivity"""
        import networkx as nx
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes and edges
        for node_id in self.graph_manager.nodes:
            G.add_node(node_id)
            
        for edge_id, edge in self.graph_manager.edges.items():
            G.add_edge(edge.source.node.id, edge.target.node.id)
            
        # Find connected components
        components = list(nx.connected_components(G))
        
        # Create groups for components with sufficient size
        for i, component in enumerate(components):
            if len(component) >= min_group_size:
                self.create_group(f"Cluster {i+1}", list(component))
                
        self.groups_changed.emit()
        
    def to_dict(self) -> dict:
        """Convert all groups to dictionary for serialization"""
        return {
            group_id: group.to_dict()
            for group_id, group in self.groups.items()
        }
        
    def from_dict(self, data: dict) -> None:
        """Restore groups from dictionary"""
        self.groups.clear()
        for group_id, group_data in data.items():
            self.groups[group_id] = NodeGroup.from_dict(group_data)
        self.groups_changed.emit()

    def clear_all_groups(self) -> None:
        """Delete all groups"""
        self.groups.clear()
        self.groups_changed.emit() 