import networkx as nx
from PyQt6.QtCore import QPointF
from ..components.node_visual import NodeVisual
from ..components.edge_visual import EdgeVisual
import math

class LayoutManager:
    """Manages different layout algorithms for graph visualization"""
    
    def __init__(self, graph_view):
        self.graph_view = graph_view
        
    def _get_graph_elements(self):
        """Get nodes and edges from the scene"""
        nodes = [item for item in self.graph_view.scene.items() if isinstance(item, NodeVisual)]
        edges = [item for item in self.graph_view.scene.items() if isinstance(item, EdgeVisual)]
        return nodes, edges
        
    def _create_networkx_graph(self, directed=False):
        """Create a networkx graph from the scene elements"""
        nodes, edges = self._get_graph_elements()
        if not nodes:
            return None, None
            
        # Create graph
        G = nx.DiGraph() if directed else nx.Graph()
        node_map = {node.node.id: node for node in nodes}
        G.add_nodes_from(node_map.keys())
        
        # Add edges
        for edge in edges:
            G.add_edge(edge.source.node.id, edge.target.node.id)
            
        return G, node_map
        
    def _get_center_point(self):
        """Get the center point of the viewport in scene coordinates"""
        return self.graph_view.mapToScene(self.graph_view.viewport().rect().center())

    def _apply_positions(self, layout, node_map, scale=1.0, center=None):
        """Apply positions to nodes with optional scaling and centering"""
        if not center:
            center = self._get_center_point()

        # Calculate bounding box of layout
        min_x = min(pos[0] for pos in layout.values())
        max_x = max(pos[0] for pos in layout.values())
        min_y = min(pos[1] for pos in layout.values())
        max_y = max(pos[1] for pos in layout.values())
        
        # Calculate center of layout
        layout_center_x = (min_x + max_x) / 2
        layout_center_y = (min_y + max_y) / 2
        
        # Apply positions with centering and scaling
        for node_id, pos in layout.items():
            node = node_map[node_id]
            x = (pos[0] - layout_center_x) * scale + center.x()
            y = (pos[1] - layout_center_y) * scale + center.y()
            node.setPos(x, y)
            
    def apply_circular_layout(self):
        """Arrange nodes in a circular layout with optional grouping"""
        G, node_map = self._create_networkx_graph()
        if not G:
            return
            
        # Get circular layout with larger scale for better spacing
        layout = nx.circular_layout(G, scale=400)
        self._apply_positions(layout, node_map)
            
    def apply_hierarchical_layout(self):
        """Arrange nodes in an improved hierarchical tree layout"""
        G, node_map = self._create_networkx_graph(directed=True)
        if not G:
            return
            
        # Find root nodes (nodes with no incoming edges)
        root_nodes = [n for n in G.nodes() if G.in_degree(n) == 0]
        if not root_nodes:
            root_nodes = [list(G.nodes())[0]]  # If no root nodes found, use first node
            
        # Calculate node levels using BFS
        levels = {}
        for root in root_nodes:
            bfs_levels = nx.single_source_shortest_path_length(G, root)
            for node, level in bfs_levels.items():
                levels[node] = min(level, levels.get(node, float('inf')))
                
        # Group nodes by level
        nodes_by_level = {}
        for node, level in levels.items():
            nodes_by_level.setdefault(level, []).append(node)
            
        # Calculate layout
        max_level = max(levels.values())
        level_height = 200  # Increased vertical spacing
        
        # Center the layout
        center = self._get_center_point()
        total_height = max_level * level_height
        start_y = center.y() - total_height / 2
        
        # Position nodes level by level with dynamic spacing
        layout = {}
        for level, level_nodes in sorted(nodes_by_level.items()):
            # Calculate horizontal spacing based on number of nodes
            spacing = max(150, 800 / len(level_nodes))  # Dynamic spacing with minimum
            level_width = (len(level_nodes) - 1) * spacing
            start_x = center.x() - level_width / 2
            
            # Position nodes in this level
            for i, node_id in enumerate(level_nodes):
                x = start_x + i * spacing
                y = start_y + level * level_height
                layout[node_id] = (x, y)
                
        # Apply positions
        self._apply_positions(layout, node_map, scale=1.0)
                
    def apply_grid_layout(self):
        """Arrange nodes in an optimized grid layout"""
        G, node_map = self._create_networkx_graph()
        if not G:
            return
            
        # Use spring layout with optimized parameters
        layout = nx.spring_layout(
            G,
            k=2.0,  # Optimal distance between nodes
            iterations=100,  # More iterations for better convergence
            scale=400,  # Larger scale
            seed=42  # For consistent layouts
        )
        
        self._apply_positions(layout, node_map)
        
    def apply_radial_tree_layout(self):
        """Arrange nodes in a radial tree layout"""
        G, node_map = self._create_networkx_graph(directed=True)
        if not G:
            return
            
        # Find root node (node with highest out degree)
        root = max(G.nodes(), key=lambda n: G.out_degree(n))
        
        # Create a tree layout
        layout = nx.kamada_kawai_layout(G, scale=400)
        
        # Convert to radial coordinates
        radial_layout = {}
        for node, pos in layout.items():
            # Convert cartesian to polar coordinates
            x, y = pos
            r = math.sqrt(x*x + y*y)
            theta = math.atan2(y, x)
            
            # Adjust radius based on distance from root
            try:
                distance = nx.shortest_path_length(G, root, node)
                r = distance * 150  # Scale factor for radius
            except nx.NetworkXNoPath:
                pass
                
            # Convert back to cartesian coordinates
            radial_layout[node] = (
                r * math.cos(theta),
                r * math.sin(theta)
            )
            
        self._apply_positions(radial_layout, node_map)
        
    def apply_force_directed_layout(self):
        """Apply force-directed layout with advanced parameters"""
        G, node_map = self._create_networkx_graph()
        if not G:
            return
            
        # Use Fruchterman-Reingold force-directed algorithm
        layout = nx.fruchterman_reingold_layout(
            G,
            k=2.0,  # Optimal distance between nodes
            iterations=100,  # More iterations for better convergence
            scale=400,  # Larger scale
            seed=42  # For consistent layouts
        )
        
        self._apply_positions(layout, node_map) 