from __future__ import annotations

from typing import List, Dict, Any

from PySide6.QtGui import QUndoCommand
from PySide6.QtCore import QPointF

from entities import Entity


class AddNodeCommand(QUndoCommand):
    """Undoable command to add a node to the graph."""

    def __init__(self, graph_manager, entity: Entity, pos: QPointF, text: str | None = None):
        super().__init__(text or f"Add {entity.__class__.__name__}")
        self.graph_manager = graph_manager
        self.entity = entity
        self.pos = QPointF(pos)
        self._done = False

    def redo(self):
        # Add node if not present
        self.graph_manager.add_node(self.entity, self.pos)
        self._done = True

    def undo(self):
        # Remove node by id
        self.graph_manager.remove_node(self.entity.id)


class RemoveNodeCommand(QUndoCommand):
    """Undoable command to remove a node (and its connected edges) from the graph.

    On undo, it restores the node with its original position and the removed edges.
    """

    def __init__(self, graph_manager, node_id: str, text: str | None = None):
        super().__init__(text or f"Remove node {node_id}")
        self.graph_manager = graph_manager
        self.node_id = node_id
        # State to restore on undo
        self._entity: Entity | None = None
        self._pos: QPointF | None = None
        self._edges: List[Dict[str, Any]] = []  # list of {source, target, relationship, style, label, properties}

    def _capture_state(self):
        node_visual = self.graph_manager.nodes.get(self.node_id)
        if not node_visual:
            return
        self._entity = node_visual.node
        self._pos = QPointF(node_visual.pos())

        # Capture connected edges
        for edge_id, edge in list(self.graph_manager.edges.items()):
            if edge.source.node.id == self.node_id or edge.target.node.id == self.node_id:
                self._edges.append({
                    "source": edge.source.node.id,
                    "target": edge.target.node.id,
                    "relationship": getattr(edge, "relationship", ""),
                    "style": getattr(edge, "style", None) and {
                        # store plain int to avoid enum->int casting issues
                        "pen_style": getattr(edge.style.style, 'value', edge.style.style),
                        "color": edge.style.color.name(),
                        "width": edge.style.width,
                    },
                    "label": getattr(edge, "label", None),
                    "properties": getattr(edge, "properties", None)
                })

    def redo(self):
        # Capture on first execution
        if self._entity is None:
            self._capture_state()
        self.graph_manager.remove_node(self.node_id)

    def undo(self):
        if not self._entity or self._pos is None:
            return
        node = self.graph_manager.add_node(self._entity, self._pos)
        # Restore edges
        for e in self._edges:
            edge = self.graph_manager.add_edge(e["source"], e["target"], e.get("relationship", ""))
            if edge and e.get("style"):
                style = e["style"]
                from PySide6.QtCore import Qt as _Qt
                edge.style.style = _Qt.PenStyle(style["pen_style"])
                from PySide6.QtGui import QColor as _QColor
                edge.style.color = _QColor(style["color"])
                edge.style.width = style["width"]
                edge.update()
            if edge and e.get("label") is not None:
                edge.label = e["label"]
                edge.update()
            if edge and e.get("properties") is not None:
                edge.properties = e["properties"]


class AddEdgeCommand(QUndoCommand):
    """Undoable command to add an edge between two nodes."""

    def __init__(self, graph_manager, source_id: str, target_id: str, *,
                 relationship: str = "",
                 style: dict | None = None,
                 label: str | None = None,
                 properties: dict | None = None,
                 text: str | None = None):
        super().__init__(text or f"Add edge {source_id}->{target_id}")
        self.graph_manager = graph_manager
        self.source_id = source_id
        self.target_id = target_id
        self.relationship = relationship or ""
        # Persist optional visuals/metadata to apply on redo
        self.style = style
        self.label = label
        self.properties = properties

    def redo(self):
        edge = self.graph_manager.add_edge(self.source_id, self.target_id, self.relationship)
        if edge is None:
            return
        # Restore optional style/label/properties
        if self.style:
            from PySide6.QtCore import Qt as _Qt
            from PySide6.QtGui import QColor as _QColor
            try:
                # handle either enum or int for pen_style
                pen_style_val = self.style.get("pen_style")
                edge.style.style = (_Qt.PenStyle(pen_style_val)
                                    if isinstance(pen_style_val, int) else pen_style_val)
                edge.style.color = _QColor(self.style.get("color", edge.style.color.name()))
                edge.style.width = self.style.get("width", edge.style.width)
                edge.update()
            except Exception:
                pass
        if self.label is not None:
            setattr(edge, "label", self.label)
            edge.update()
        if self.properties is not None:
            setattr(edge, "properties", self.properties)

    def undo(self):
        self.graph_manager.remove_edge(self.source_id, self.target_id)


class RemoveEdgeCommand(QUndoCommand):
    """Undoable command to remove an existing edge; restores on undo."""

    def __init__(self, graph_manager, source_id: str, target_id: str, text: str | None = None):
        super().__init__(text or f"Remove edge {source_id}->{target_id}")
        self.graph_manager = graph_manager
        self.source_id = source_id
        self.target_id = target_id
        # Captured state
        self.relationship: str = ""
        self.style: dict | None = None
        self.label: str | None = None
        self.properties: dict | None = None

    def _capture(self):
        edge_id = f"{self.source_id}->{self.target_id}"
        edge = self.graph_manager.edges.get(edge_id)
        if not edge:
            return
        self.relationship = getattr(edge, "relationship", "")
        if getattr(edge, "style", None):
            self.style = {
                # store plain int to avoid enum->int casting issues
                "pen_style": getattr(edge.style.style, 'value', edge.style.style),
                "color": edge.style.color.name(),
                "width": edge.style.width,
            }
        self.label = getattr(edge, "label", None)
        self.properties = getattr(edge, "properties", None)

    def redo(self):
        # Capture on first execution
        if self.style is None and self.label is None and self.properties is None and self.relationship == "":
            self._capture()
        self.graph_manager.remove_edge(self.source_id, self.target_id)

    def undo(self):
        # Recreate with captured state
        cmd = AddEdgeCommand(self.graph_manager, self.source_id, self.target_id,
                             relationship=self.relationship, style=self.style,
                             label=self.label, properties=self.properties)
        cmd.redo()


class UpdateEdgeCommand(QUndoCommand):
    """Undoable command to update an existing edge's attributes (relationship, style, etc.).

    Currently supports updating:
      - relationship (text)
      - pen style (Qt.PenStyle or int)
    """

    def __init__(self, graph_manager, source_id: str, target_id: str, *,
                 relationship: str | None = None,
                 pen_style: int | None = None,
                 text: str | None = None):
        super().__init__(text or f"Update edge {source_id}->{target_id}")
        self.graph_manager = graph_manager
        self.source_id = source_id
        self.target_id = target_id
        # new values to apply
        self.new_relationship = relationship
        self.new_pen_style = pen_style
        # old values captured on first redo
        self._old_relationship: str | None = None
        self._old_pen_style: int | None = None

    def _get_edge(self):
        return self.graph_manager.edges.get(f"{self.source_id}->{self.target_id}")

    def _capture_if_needed(self):
        edge = self._get_edge()
        if edge is None:
            return None
        if self._old_relationship is None and self._old_pen_style is None:
            # capture old
            self._old_relationship = getattr(edge, 'relationship', '')
            ps = getattr(getattr(edge, 'style', None), 'style', None)
            if ps is not None:
                self._old_pen_style = getattr(ps, 'value', ps)
        return edge

    def _apply(self, relationship: str | None, pen_style_val: int | None):
        from PySide6.QtCore import Qt as _Qt
        edge = self._get_edge()
        if edge is None:
            return
        if relationship is not None:
            edge.relationship = relationship
            if hasattr(edge, 'text_item'):
                edge.text_item.setPlainText(relationship)
        if pen_style_val is not None and getattr(edge, 'style', None):
            try:
                edge.style.style = _Qt.PenStyle(pen_style_val)
            except Exception:
                # fallback if already an enum/int
                edge.style.style = pen_style_val
        if hasattr(edge, 'updatePosition'):
            edge.updatePosition()
        edge.update()

    def redo(self):
        edge = self._capture_if_needed()
        if edge is None:
            return
        self._apply(self.new_relationship, self.new_pen_style)

    def undo(self):
        # restore captured old values
        self._apply(self._old_relationship, self._old_pen_style)
