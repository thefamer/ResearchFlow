"""
ResearchFlow - Main Application
Portable desktop application for managing academic research workflows.
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Constants
QWIDGETSIZE_MAX = 16777215  # Qt's maximum widget size

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QVBoxLayout, QHBoxLayout, QWidget, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QMenu, QPushButton
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QMimeData, QByteArray, QBuffer, QVariantAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import (
    QAction, QKeySequence, QDragEnterEvent, QDropEvent,
    QMouseEvent, QWheelEvent, QClipboard, QImage, QColor, QPainter, QBrush, QIcon, QPen
)

from models import (
    ProjectData, NodeData, NodeMetadata, Position, EdgeData, Snippet,
    GroupData, generate_uuid
)
from utils import ProjectManager, extract_title_from_filename, get_app_root, get_resource_path, ModernTheme
from graphics_items import (
    BaseNodeItem, PipelineModuleItem, ReferenceNodeItem, EdgeItem,
    TempConnectionLine, Colors, SnippetItem, GroupItem, WaypointItem
)
from widgets import (
    WelcomeDialog, ProjectDockWidget, MarkdownViewerDialog, ModulePalette,
    PipelineRequiredDialog
)
from undo import (
    UndoManager, DescriptionChangeCommand,
    TodoAddCommand, TodoRemoveCommand, TodoEditCommand, TodoToggleCommand, TodoMoveCommand,
    TagAddCommand, TagRemoveCommand, TagRenameCommand, TagColorChangeCommand, TagMoveCommand,
    AddNodeCommand, RemoveNodeCommand, NodePositionCommand,
    AddEdgeCommand, RemoveEdgeCommand,
    AddGroupCommand, RemoveGroupCommand, GroupMoveCommand, NodeGroupChangeCommand,
    GlobalEdgeColorChangeCommand, ModulePaletteColorChangeCommand,
    SnippetAddCommand, SnippetRemoveCommand, SnippetEditCommand, SnippetMoveCommand,
    NodeMetadataEditCommand, GroupNameEditCommand, GroupSizeCommand, NodeTagToggleCommand
)


# ============================================================================
# Custom Graphics Scene
# ============================================================================
class ResearchScene(QGraphicsScene):
    """
    Custom scene handling node management and connections.
    """
    
    # Undo/Redo Signals
    node_added_requested = pyqtSignal(dict)
    node_removed_requested = pyqtSignal(dict, list)
    node_moved_requested = pyqtSignal(str, tuple, tuple)
    edge_added_requested = pyqtSignal(dict, str, list)  # edge_data, target_node_id, cloned_snippet_ids
    edge_removed_requested = pyqtSignal(dict)
    group_added_requested = pyqtSignal(dict)
    group_removed_requested = pyqtSignal(dict)
    group_moved_requested = pyqtSignal(str, tuple, tuple)
    node_group_changed = pyqtSignal(str, object, object)  # node_id, old_group_id, new_group_id
    
    # V3.9.0: Snippet undo signals
    snippet_add_requested = pyqtSignal(str, dict)  # node_id, snippet_data
    snippet_remove_requested = pyqtSignal(str, dict, int)  # node_id, snippet_data, index
    snippet_move_requested = pyqtSignal(str, str, int, int)  # node_id, snippet_id, from, to
    snippet_edit_requested = pyqtSignal(str, str, str, str, str)  # node_id, snippet_id, field, old, new
    
    # V3.9.0: Node metadata edit signal
    metadata_edit_requested = pyqtSignal(str, str, str, str)  # node_id, field, old_value, new_value
    
    # V3.9.0: Tag toggle and group name edit signals
    tag_toggle_requested = pyqtSignal(str, str, bool)  # node_id, tag_name, was_added
    group_name_edit_requested = pyqtSignal(str, str, str)  # group_id, old_name, new_name
    group_size_requested = pyqtSignal(str, tuple, tuple)  # group_id, old_rect, new_rect
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        
        # Grid settings
        self._grid_size = 25
        self._grid_color = QColor("#E0E0E0")
        self._bg_color = QColor("#FAFAFA")
        
        self._nodes: dict[str, BaseNodeItem] = {}
        self._edges: dict[str, EdgeItem] = {}
        self._groups: dict[str, GroupItem] = {}  # V3.5.0
        self._waypoints: dict[str, WaypointItem] = {}  # V3.9.0
        self._temp_connection: Optional[TempConnectionLine] = None
        self._connection_source: Optional[BaseNodeItem] = None
        self._suppress_context_menu: bool = False
        self._is_undo_operation: bool = False  # Flag to bypass signal emission
        
        # Edge color settings (V1.2.0)
        self._pipeline_edge_color = "#607D8B"
        self._reference_edge_color = "#4CAF50"
        
        self.project_manager: Optional[ProjectManager] = None
    
    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Draw a subtle grid background."""
        # Fill background
        painter.fillRect(rect, self._bg_color)
        
        # Draw grid
        pen = QPen(self._grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Calculate grid bounds
        left = int(rect.left()) - (int(rect.left()) % self._grid_size)
        top = int(rect.top()) - (int(rect.top()) % self._grid_size)
        
        # Draw vertical lines
        x = left
        while x < rect.right():
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += self._grid_size
        
        # Draw horizontal lines
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += self._grid_size
    
    def set_edge_colors(self, pipeline_color: str, reference_color: str) -> None:
        """Set edge colors and update all existing edges and waypoints."""
        self._pipeline_edge_color = pipeline_color
        self._reference_edge_color = reference_color
        
        # Update edges
        for edge in self._edges.values():
            edge.update_colors(pipeline_color, reference_color)
            
        # V3.9.0: Update waypoints
        for waypoint in self._waypoints.values():
            # Apply new color based on current mode
            color = reference_color if waypoint._is_reference_type else pipeline_color
            waypoint.set_color(color)
    
    def add_node(self, node: BaseNodeItem) -> None:
        """Add a node to the scene (Gatekeeper)."""
        if self._is_undo_operation:
            self._add_node_internal(node)
        else:
            # Emit request
            # We convert to dict for serialization consistency
            self.node_added_requested.emit(node.node_data.to_dict())

    def _add_node_internal(self, node: BaseNodeItem) -> None:
        """Internal add node logic."""
        self.addItem(node)
        self._nodes[node.node_data.id] = node
        
        # Connect signals
        node.signals.data_changed.connect(self._on_node_changed)
        node.signals.expand_requested.connect(self._on_expand_requested)
        # Handle drag finish for grouping AND undo (V3.9.0)
        node.signals.drag_finished.connect(self._on_node_interaction_finished)
        
        # V3.9.0: Connect snippet undo signals
        node.signals.snippet_add_requested.connect(self._on_snippet_add_requested)
        node.signals.snippet_remove_requested.connect(self._on_snippet_remove_requested)
        node.signals.snippet_move_requested.connect(self._on_snippet_move_requested)
        node.signals.snippet_edit_requested.connect(self._on_snippet_edit_requested)
        
        # V3.9.0: Connect metadata edit signal
        node.signals.metadata_edit_requested.connect(self._on_metadata_edit_requested)
        
        # V3.9.0: Connect tag toggle signal
        node.signals.tag_toggle_requested.connect(self._on_tag_toggle_requested)
    
    def _on_node_interaction_finished(self, node_id: str, modifiers) -> None:
        """Handle node drag/interaction end."""
        # 1. Grouping Logic
        self.check_node_grouping(node_id, modifiers)
        
        # 2. Undo/Redo Movement Logic
        node = self._nodes.get(node_id) or self._waypoints.get(node_id)
        if node and hasattr(node, '_drag_start_pos'):
            old_pos = (node._drag_start_pos.x(), node._drag_start_pos.y())
            new_pos = (node.pos().x(), node.pos().y())
            
            # Emit signal only if actually moved
            if (abs(old_pos[0] - new_pos[0]) > 0.1 or 
                abs(old_pos[1] - new_pos[1]) > 0.1):
                self.node_moved_requested.emit(node_id, old_pos, new_pos)


    def remove_node(self, node_id: str) -> None:
        """Remove a node (Gatekeeper)."""
        if self._is_undo_operation:
            self._remove_node_internal(node_id)
        else:
            # Need to gather connected edges for Command context
            node = self._nodes.get(node_id)
            if node:
                edges = []
                for edge in self._edges.values():
                    if edge.source_node == node or edge.target_node == node:
                        # Serialize edge data
                        edges.append(EdgeData(
                            id=edge.edge_id,
                            source_id=edge.source_node.node_data.id,
                            target_id=edge.target_node.node_data.id
                        ).to_dict())
                
                self.node_removed_requested.emit(node.node_data.to_dict(), edges)

    def _remove_node_internal(self, node_id: str) -> None:
        """Internal remove node logic."""
        if node_id in self._nodes:
            # Remove from any groups (V3.5.0)
            for group in self._groups.values():
                if node_id in group.group_data.node_ids:
                    group.remove_node(node_id)
            
            node = self._nodes.pop(node_id)
            
            # Remove connected edges
            edges_to_remove = []
            for edge_id, edge in self._edges.items():
                if edge.source_node == node or edge.target_node == node:
                    edges_to_remove.append(edge_id)
            
            for edge_id in edges_to_remove:
                # Direct remove (bypass gatekeeper for side-effects)
                self._remove_edge_internal(edge_id)
            
            self.removeItem(node)
    
    def add_edge(self, source_id: str, target_id: str, edge_id: str = None,
                 target_node_id: str = "", cloned_snippet_ids: list = None) -> Optional[EdgeItem]:
        """Create an edge (Gatekeeper).
        For Reference→Pipeline connections, target_node_id and cloned_snippet_ids
        are used to support undo of snippet cloning.
        """
        if self._is_undo_operation:
            return self._add_edge_internal(source_id, target_id, edge_id)
        else:
            edge_id = edge_id or generate_uuid()
            data = {"source_id": source_id, "target_id": target_id, "id": edge_id}
            self.edge_added_requested.emit(data, target_node_id or "", cloned_snippet_ids or [])
            # Return edge if created synchronously
            return self._edges.get(edge_id)

    def _add_edge_internal(self, source_id: str, target_id: str, edge_id: str = None) -> Optional[EdgeItem]:
        """Internal add edge logic."""
        # Get source (can be node or waypoint)
        source = self._nodes.get(source_id) or self._waypoints.get(source_id)
        target = self._nodes.get(target_id) or self._waypoints.get(target_id)
        
        if source and target:
            # Create edge
            # Determine edge type
            is_reference = False
            if isinstance(source, ReferenceNodeItem):
                is_reference = True
            elif isinstance(source, WaypointItem) and source._is_reference_type:
                is_reference = True
            
            edge = EdgeItem(source, target, edge_id,
                          self._pipeline_edge_color, self._reference_edge_color)
            
            # Manually set edge type/color if is_reference
            if is_reference:
                edge._is_reference_edge = True
                edge._base_color = QColor(self._reference_edge_color)
                edge.setPen(QPen(edge._base_color, 2))
                edge.update()
            
            self.addItem(edge)
            self._edges[edge.edge_id] = edge
            
            # V3.9.0: Update waypoint status if target is waypoint
            if isinstance(target, WaypointItem):
                target.set_has_incoming(True)
                changed = target.set_reference_type(is_reference, 
                                        self._pipeline_edge_color, 
                                        self._reference_edge_color)
                
                # Propagate to outgoing edge from this waypoint
                if changed:
                    self._update_outgoing_edges(target, is_reference)
            
            return edge
        return None
        
    def _update_outgoing_edges(self, source_node: BaseNodeItem, is_reference: bool) -> None:
        """Helper to propagate reference status to outgoing edges."""
        for edge in self._edges.values():
            if edge.source_node == source_node:
                # Update edge
                edge._is_reference_edge = is_reference
                color = self._reference_edge_color if is_reference else self._pipeline_edge_color
                edge._base_color = QColor(color)
                edge.setPen(QPen(edge._base_color, 2))
                edge.update()
                
                # If target is also a waypoint, continue propagation
                if isinstance(edge.target_node, WaypointItem):
                    changed = edge.target_node.set_reference_type(is_reference, 
                                                      self._pipeline_edge_color, 
                                                      self._reference_edge_color)
                    if changed:
                        self._update_outgoing_edges(edge.target_node, is_reference)
    
    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge (Gatekeeper)."""
        if self._is_undo_operation:
            self._remove_edge_internal(edge_id)
        else:
            edge = self._edges.get(edge_id)
            if edge:
                data = EdgeData(
                    id=edge_id,
                    source_id=edge.source_node.node_data.id,
                    target_id=edge.target_node.node_data.id
                ).to_dict()
                self.edge_removed_requested.emit(data)

    def _remove_edge_internal(self, edge_id: str) -> None:
        """Internal remove edge logic."""
        if edge_id in self._edges:
            edge = self._edges.pop(edge_id)
            
            # V3.9.0: Update waypoint status if target was a waypoint
            target_id = edge.target_node.node_data.id
            if target_id in self._waypoints:
                waypoint = self._waypoints[target_id]
                # Check if there are any remaining incoming edges
                has_incoming = any(
                    e.target_node.node_data.id == target_id 
                    for e in self._edges.values()
                )
                waypoint.set_has_incoming(has_incoming)
                
                # Reset color to default if no incoming edge
                if not has_incoming:
                    waypoint.set_reference_type(False, 
                                              self._pipeline_edge_color, 
                                              self._reference_edge_color)
                    # Propagate reset to outgoing edges
                    self._update_outgoing_edges(waypoint, False)
            
            self.removeItem(edge)
    
    def add_waypoint(self, waypoint: WaypointItem) -> None:
        """Add a waypoint (Gatekeeper)."""
        if self._is_undo_operation:
            self._add_waypoint_internal(waypoint)
        else:
            self.node_added_requested.emit(waypoint.node_data.to_dict())

    def _add_waypoint_internal(self, waypoint: WaypointItem) -> None:
        """Internal add waypoint logic."""
        self.addItem(waypoint)
        self._waypoints[waypoint.node_data.id] = waypoint
        
        # Connect signals for grouping
        # waypoint.signals.drag_finished.connect(self.check_node_grouping)
        waypoint.signals.drag_finished.connect(self._on_node_interaction_finished)
        waypoint.signals.data_changed.connect(self._on_node_changed)
    
    def remove_waypoint(self, waypoint_id: str) -> None:
        """Remove a waypoint (Gatekeeper)."""
        if self._is_undo_operation:
            self._remove_waypoint_internal(waypoint_id)
        else:
            waypoint = self._waypoints.get(waypoint_id)
            if waypoint:
                edges = []
                for edge in self._edges.values():
                    if edge.source_node == waypoint or edge.target_node == waypoint:
                        edges.append(EdgeData(
                            id=edge.edge_id,
                            source_id=edge.source_node.node_data.id,
                            target_id=edge.target_node.node_data.id
                        ).to_dict())
                self.node_removed_requested.emit(waypoint.node_data.to_dict(), edges)

    def _remove_waypoint_internal(self, waypoint_id: str) -> None:
        """Internal remove waypoint logic."""
        if waypoint_id in self._waypoints:
            # Remove from groups
            for group in self._groups.values():
                if waypoint_id in group.group_data.node_ids:
                    group.remove_node(waypoint_id)
            
            waypoint = self._waypoints.pop(waypoint_id)
            
            # Remove connected edges
            edges_to_remove = []
            for edge_id, edge in self._edges.items():
                if edge.source_node == waypoint or edge.target_node == waypoint:
                    edges_to_remove.append(edge_id)
            
            for edge_id in edges_to_remove:
                self._remove_edge_internal(edge_id)
            
            self.removeItem(waypoint)

    def restore_node(self, node_data) -> None:
        """Restore a node/waypoint from data (Undo/Redo helper)."""
        self._is_undo_operation = True
        try:
            if node_data.type == "waypoint":
                waypoint = WaypointItem(node_data, initial_color=self._pipeline_edge_color)
                self._add_waypoint_internal(waypoint)
            else:
                if node_data.type == "pipeline_module":
                    node = PipelineModuleItem(node_data)
                else:
                    node = ReferenceNodeItem(node_data)
                self._add_node_internal(node)
        finally:
            self._is_undo_operation = False

    def restore_edge(self, edge_data) -> None:
        """Restore an edge from data."""
        self._is_undo_operation = True
        try:
            self._add_edge_internal(edge_data.source_id, edge_data.target_id, edge_data.id)
        finally:
            self._is_undo_operation = False

    def restore_group(self, group_data) -> None:
        """Restore a group from data."""
        group = GroupItem(group_data)
        self.addItem(group)
        self._groups[group_data.id] = group
        group.signals.moved.connect(self.update_group_nodes_position)
        group.signals.color_changed.connect(self.update_group_color_visuals)
        group.signals.drag_finished.connect(self._on_group_drag_finished)
        group.signals.node_added.connect(self._on_group_node_added)
        group.signals.node_removed.connect(self._on_group_node_removed)
        # V3.9.0: Connect group name and size edit signals
        group.signals.name_edit_requested.connect(self._on_group_name_edit_requested)
        group.signals.size_resize_requested.connect(self._on_group_size_requested)
        group.setZValue(-1)

    def remove_group(self, group_id: str) -> None:
        """Remove a group by ID."""
        self._is_undo_operation = True
        try:
            if group_id in self._groups:
                group = self._groups.pop(group_id)
                self.removeItem(group)
        finally:
            self._is_undo_operation = False
    
    def get_node_at(self, pos: QPointF) -> Optional[BaseNodeItem]:
        """Get the node or waypoint at the given scene position."""
        items = self.items(pos)
        for item in items:
            # Check if it's a waypoint directly
            if isinstance(item, WaypointItem):
                return item
            # Walk up to find the node
            while item:
                if isinstance(item, BaseNodeItem):
                    return item
                item = item.parentItem()
        return None
    
    def update_all_edges(self) -> None:
        """Update all edge paths (after node movement)."""
        for edge in self._edges.values():
            edge.update_path()
    
    def start_connection(self, source, start_pos: QPointF) -> None:
        """Start drawing a temporary connection from node or waypoint."""
        self._connection_source = source
        source.set_connection_source(True)
        self._temp_connection = TempConnectionLine(start_pos)
        self.addItem(self._temp_connection)
    
    def update_temp_connection(self, pos: QPointF) -> None:
        """Update the temporary connection end point."""
        if self._temp_connection:
            self._temp_connection.update_end(pos)
    
    def complete_connection(self, target) -> bool:
        """Complete a connection to the target node/waypoint with deep copy."""
        if self._connection_source and target and self._connection_source != target:
            source = self._connection_source
            
            # V3.9.0: Block Pipeline → Reference connections
            if isinstance(source, PipelineModuleItem) and isinstance(target, ReferenceNodeItem):
                self.cancel_connection()
                return False
            
            # V3.9.0: Waypoint restrictions - single in, single out
            if isinstance(target, WaypointItem):
                # Check if waypoint already has an incoming edge
                for edge in self._edges.values():
                    if edge.target_node.node_data.id == target.node_data.id:
                        self.cancel_connection()
                        return False  # Already has incoming
            
            if isinstance(source, WaypointItem):
                # Check if waypoint already has an outgoing edge
                for edge in self._edges.values():
                    if edge.source_node.node_data.id == source.node_data.id:
                        self.cancel_connection()
                        return False  # Already has outgoing
            
            # Deep copy snippets only when connecting Reference → Pipeline
            cloned_snippet_ids = []
            target_node_id = ""
            if isinstance(source, ReferenceNodeItem) and isinstance(target, PipelineModuleItem):
                snippets = source.get_snippets_data()
                if snippets:
                    cloned_snippet_ids = target.add_cloned_snippets(snippets, source.get_title())
                    target_node_id = target.node_data.id
            
            # Create edge for any connection type (with cloned snippet info)
            edge_id = generate_uuid()
            self.add_edge(source.node_data.id, target.node_data.id, edge_id,
                         target_node_id, cloned_snippet_ids)
            
            self.cancel_connection()
            return True
        
        self.cancel_connection()
        return False
    
    def cancel_connection(self) -> None:
        """Cancel the current connection."""
        if self._connection_source:
            self._connection_source.set_connection_source(False)
            self._connection_source = None
        
        if self._temp_connection:
            self.removeItem(self._temp_connection)
            self._temp_connection = None
        
        # Suppress context menu briefly
        self._suppress_context_menu = True
    
    def _on_node_changed(self, node_id: str) -> None:
        """Handle node data changes."""
        # Auto-save will be triggered by main window
        pass
    
    def _on_expand_requested(self, node_id: str) -> None:
        """Handle expand button click on reference nodes."""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            if isinstance(node, ReferenceNodeItem):
                md_path = node.node_data.metadata.relative_path_to_md
                if md_path and self.project_manager:
                    abs_path = self.project_manager.get_absolute_asset_path(md_path)
                    if abs_path and abs_path.exists():
                        dialog = MarkdownViewerDialog(
                            node.node_data.metadata.title,
                            str(abs_path),
                            self.views()[0] if self.views() else None
                        )
                        dialog.show()
    
    # V3.9.0: Snippet signal handlers (forward to scene-level signals)
    def _on_snippet_add_requested(self, node_id: str, snippet_data: dict) -> None:
        self.snippet_add_requested.emit(node_id, snippet_data)
    
    def _on_snippet_remove_requested(self, node_id: str, snippet_data: dict, index: int) -> None:
        self.snippet_remove_requested.emit(node_id, snippet_data, index)
    
    def _on_snippet_move_requested(self, node_id: str, snippet_id: str, from_idx: int, to_idx: int) -> None:
        self.snippet_move_requested.emit(node_id, snippet_id, from_idx, to_idx)
    
    def _on_snippet_edit_requested(self, node_id: str, snippet_id: str, field: str, old: str, new: str) -> None:
        self.snippet_edit_requested.emit(node_id, snippet_id, field, old, new)
    
    def _on_metadata_edit_requested(self, node_id: str, field: str, old: str, new: str) -> None:
        self.metadata_edit_requested.emit(node_id, field, old, new)
    
    def _on_tag_toggle_requested(self, node_id: str, tag_name: str, was_added: bool) -> None:
        self.tag_toggle_requested.emit(node_id, tag_name, was_added)
    
    def _on_group_name_edit_requested(self, group_id: str, old_name: str, new_name: str) -> None:
        self.group_name_edit_requested.emit(group_id, old_name, new_name)
    
    def _on_group_size_requested(self, group_id: str, old_rect: tuple, new_rect: tuple) -> None:
        self.group_size_requested.emit(group_id, old_rect, new_rect)
    
    def clear_all(self) -> None:
        """Clear all items from the scene."""
        self._nodes.clear()
        self._edges.clear()
        self._groups.clear()
        self.clear()
    
    def get_project_data(self) -> ProjectData:
        """Export scene state to ProjectData."""
        data = ProjectData()
        
        # Export nodes
        for node in self._nodes.values():
            data.nodes.append(node.node_data)
            
        # V3.9.0: Export waypoints
        for waypoint in self._waypoints.values():
            data.nodes.append(waypoint.node_data)
        
        # Export edges
        for edge_id, edge in self._edges.items():
            edge_data = EdgeData(
                id=edge_id,
                source_id=edge.source_node.node_data.id,
                target_id=edge.target_node.node_data.id
            )
            data.edges.append(edge_data)
        
        # Export groups (V3.5.0)
        for group in self._groups.values():
            data.groups.append(group.group_data)
        
        # Check if pipeline is initialized
        data.pipeline_initialized = any(
            isinstance(n, PipelineModuleItem) for n in self._nodes.values()
        )
        
        return data
    
    def load_project_data(self, data: ProjectData) -> None:
        """Import scene state from ProjectData."""
        self.clear_all()
        
        # Create groups first (they're rendered below nodes)
        for group_data in data.groups:
            group = GroupItem(group_data)
            self.addItem(group)
            self._groups[group_data.id] = group
            group.signals.moved.connect(self.update_group_nodes_position)
            group.signals.color_changed.connect(self.update_group_color_visuals)
            group.signals.drag_finished.connect(self._on_group_drag_finished)
            group.signals.node_added.connect(self._on_group_node_added)
            group.signals.node_removed.connect(self._on_group_node_removed)
            # V3.9.0: Connect group name and size edit signals
            group.signals.name_edit_requested.connect(self._on_group_name_edit_requested)
            group.signals.size_resize_requested.connect(self._on_group_size_requested)
        
        # Create nodes and waypoints
        for node_data in data.nodes:
            if node_data.type == "pipeline_module":
                node = PipelineModuleItem(node_data)
                self.add_node(node)
            elif node_data.type == "reference_paper":
                node = ReferenceNodeItem(node_data)
                self.add_node(node)
            elif node_data.type == "waypoint":
                waypoint = WaypointItem(
                    node_data,
                    initial_color=self._pipeline_edge_color
                )
                self.add_waypoint(waypoint)
        
        # Create edges
        for edge_data in data.edges:
            self.add_edge(edge_data.source_id, edge_data.target_id, edge_data.id)
            
        # Initialize group visuals
        for group in self._groups.values():
            for node_id in group.group_data.node_ids:
                # Check both nodes and waypoints
                node = self._nodes.get(node_id) or self._waypoints.get(node_id)
                if node:
                    node.set_group_color(group.group_data.color)

    def check_node_grouping(self, node_id: str, modifiers) -> None:
        """Handle node grouping logic on drag finish (supports nodes and waypoints)."""
        # Look in both nodes and waypoints
        node = self._nodes.get(node_id) or self._waypoints.get(node_id)
        if not node:
            return
            
        node_rect = node.mapRectToScene(node.boundingRect())
        node_center = node.mapToScene(node.boundingRect().center())
        
        # Check if Ctrl is pressed (Qt.KeyboardModifier.ControlModifier)
        is_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        
        # Find if node is inside any group
        target_group = None
        for group in self._groups.values():
            if group.get_bounds().contains(node_center):
                target_group = group
                break
        
        # Current memberships
        current_groups = [g for g in self._groups.values() if g.contains_node(node_id)]
        
        if is_ctrl:
            # Ctrl pressed: Try to add to group or remove if dragged out
            if target_group:
                # Add to new group
                if not target_group.contains_node(node_id):
                    target_group.add_node(node_id)
                    target_group.expand_to_fit(node_rect)
                    node.set_group_color(target_group.group_data.color)
                
                # Remove from other groups
                for g in current_groups:
                    if g != target_group:
                        g.remove_node(node_id)
            else:
                # Dragged into empty space with Ctrl -> Remove from all groups
                for g in current_groups:
                    g.remove_node(node_id)
                node.set_group_color(None)

    def update_group_nodes_position(self, group_id: str, dx: float, dy: float) -> None:
        """Move all nodes in the group by delta (snap is handled by group)."""
        group = self._groups.get(group_id)
        if not group:
            return
            
        for node_id in group.group_data.node_ids:
            # Check both nodes and waypoints
            node = self._nodes.get(node_id) or self._waypoints.get(node_id)
            if node:
                # Set flag to prevent individual snap - group handles snap for all
                node._being_moved_by_group = True
                node.moveBy(dx, dy)
                node._being_moved_by_group = False

    def update_group_color_visuals(self, group_id: str, color: str) -> None:
        """Update visual color for all nodes in group."""
        group = self._groups.get(group_id)
        if not group: return
        for node_id in group.group_data.node_ids:
            # Check both nodes and waypoints
            node = self._nodes.get(node_id) or self._waypoints.get(node_id)
            if node:
                node.set_group_color(color)
    
    def _on_group_drag_finished(self, group_id: str, old_pos: tuple, new_pos: tuple) -> None:
        """Handle group drag end - emit signal for undo tracking."""
        self.group_moved_requested.emit(group_id, old_pos, new_pos)
    
    def _on_group_node_added(self, group_id: str, node_id: str) -> None:
        """Handle node added to group - find old group for undo."""
        # Find if node was in another group before
        old_group_id = None
        for gid, group in self._groups.items():
            if gid != group_id and node_id in group.group_data.node_ids:
                old_group_id = gid
                break
        # Emit signal for MainWindow to create command
        # We need a new signal for this
        if hasattr(self, 'node_group_changed'):
            self.node_group_changed.emit(node_id, old_group_id, group_id)
    
    def _on_group_node_removed(self, group_id: str, node_id: str) -> None:
        """Handle node removed from group."""
        # Emit signal for MainWindow
        if hasattr(self, 'node_group_changed'):
            self.node_group_changed.emit(node_id, group_id, None)


# ============================================================================
# Custom Graphics View
# ============================================================================
class ResearchView(QGraphicsView):
    """
    Custom view with pan/zoom, drag-drop, and clipboard support.
    """
    
    def __init__(self, scene: ResearchScene, parent=None):
        super().__init__(scene, parent)
        self._research_scene = scene
        
        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Enable drops
        self.setAcceptDrops(True)
        
        # Pan state
        self._is_panning = False
        self._pan_start = QPointF()
        
        # Connection state
        self._is_connecting = False
        self._right_click_start: Optional[QPointF] = None  # Track right-click start for drag detection
        self._right_click_node: Optional[BaseNodeItem] = None  # Node where right-click started
        self._connection_started = False  # True once drag threshold exceeded
        
        # Drag threshold in pixels
        self._drag_threshold = 10
        
        # Snap grid settings (activated by holding Shift)
        self._snap_grid_size = 20
        
        # Smooth zoom animation
        self._current_zoom = 1.0
        self._target_zoom = 1.0
        self._zoom_animation = None
    
    def keyPressEvent(self, event) -> None:
        """Handle keyboard input."""
        if event.key() == Qt.Key.Key_Delete:
            # Delete selected items
            self._delete_selected_items()
            event.accept()
        elif event.key() == Qt.Key.Key_Up:
            # Move selected snippet up
            self._move_selected_snippets("up")
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            # Move selected snippet down
            self._move_selected_snippets("down")
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def _delete_selected_items(self) -> None:
        """Delete all selected items (nodes, edges, snippets)."""
        selected = self._research_scene.selectedItems()
        
        # Process snippets first to avoid parent deletion issues
        snippets = [item for item in selected if isinstance(item, SnippetItem)]
        for snippet in snippets:
            snippet.parent_node.remove_snippet(snippet)
        
        # Then other items
        for item in selected:
            if isinstance(item, EdgeItem):
                self._research_scene.remove_edge(item.edge_id)
            elif isinstance(item, GroupItem):
                # V3.9.0: Unbind all nodes before deleting group
                for node_id in item.group_data.node_ids:
                    if node_id in self._research_scene._nodes:
                        self._research_scene._nodes[node_id].set_group_color(None)
                    if node_id in self._research_scene._waypoints:
                        self._research_scene._waypoints[node_id].set_group_color(None)
                if item.group_data.id in self._research_scene._groups:
                    del self._research_scene._groups[item.group_data.id]
                self._research_scene.removeItem(item)
            elif isinstance(item, WaypointItem):
                # V3.9.0: Delete waypoint
                self._research_scene.remove_waypoint(item.node_data.id)
            elif isinstance(item, BaseNodeItem) and not isinstance(item, SnippetItem):
                # Ensure we don't try to delete ReferenceNodeItem/PipelineModuleItem again if processed differently
                self._research_scene.remove_node(item.node_data.id)
    
    def _move_selected_snippets(self, direction: str) -> None:
        """Move selected snippets up or down."""
        selected = self._research_scene.selectedItems()
        snippets = [item for item in selected if isinstance(item, SnippetItem)]
        
        for snippet in snippets:
            if direction == "up":
                snippet.parent_node.move_snippet_up(snippet)
            elif direction == "down":
                snippet.parent_node.move_snippet_down(snippet)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom with mouse wheel - animated."""
        # Calculate new target zoom
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        new_target = self._target_zoom * factor
        
        # Clamp zoom level
        new_target = max(0.1, min(5.0, new_target))
        
        if new_target == self._target_zoom:
            return
            
        self._target_zoom = new_target
        
        # Stop any running animation
        if self._zoom_animation:
            self._zoom_animation.stop()
        
        # Create smooth zoom animation
        self._zoom_animation = QVariantAnimation(self)
        self._zoom_animation.setStartValue(self._current_zoom)
        self._zoom_animation.setEndValue(self._target_zoom)
        self._zoom_animation.setDuration(150)  # 150ms for snappy feel
        self._zoom_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._zoom_animation.valueChanged.connect(self._apply_zoom)
        self._zoom_animation.start()
    
    def _apply_zoom(self, value: float) -> None:
        """Apply zoom value during animation."""
        if self._current_zoom != 0:
            factor = value / self._current_zoom
            self.scale(factor, factor)
        self._current_zoom = value
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for panning and connections."""
        if event.button() == Qt.MouseButton.MiddleButton:
            # Pan
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            # Record position for possible connection drag
            scene_pos = self.mapToScene(event.pos())
            node = self._research_scene.get_node_at(scene_pos)
            if node:
                self._right_click_start = event.position()
                self._right_click_node = node
                self._is_connecting = True
                self._connection_started = False  # Don't start until drag threshold hit
                return  # Don't pass to parent yet
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move for panning and temp connection."""
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
        elif self._is_connecting and self._right_click_start:
            # Check if we've exceeded drag threshold
            delta = event.position() - self._right_click_start
            distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            
            if distance >= self._drag_threshold and not self._connection_started:
                # Start the actual connection now
                self._connection_started = True
                scene_pos = self.mapToScene(self._right_click_start.toPoint())
                self._research_scene.start_connection(self._right_click_node, scene_pos)
            
            if self._connection_started:
                scene_pos = self.mapToScene(event.pos())
                self._research_scene.update_temp_connection(scene_pos)
        else:
            super().mouseMoveEvent(event)
            # Update edges when nodes move
            self._research_scene.update_all_edges()
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.RightButton and self._is_connecting:
            self._is_connecting = False
            was_connection = self._connection_started  # Save before reset
            
            if was_connection:
                # Complete the connection
                scene_pos = self.mapToScene(event.pos())
                target = self._research_scene.get_node_at(scene_pos)
                if target:
                    self._research_scene.complete_connection(target)
                else:
                    self._research_scene.cancel_connection()
            
            # Reset state
            self._right_click_start = None
            self._right_click_node = None
            self._connection_started = False
            
            if was_connection:
                # Don't propagate - prevents context menu
                event.accept()
                return
            # else: No drag occurred - let context menu show normally
        else:
            super().mouseReleaseEvent(event)
            self._research_scene.update_all_edges()
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drops."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
    
    def dragMoveEvent(self, event) -> None:
        """Accept drag move."""
        event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drops (files, modules, tags)."""
        mime = event.mimeData()
        pos = self.mapToScene(event.position().toPoint())
        
        if mime.hasText():
            text = mime.text()
            
            if text.startswith("module:"):
                # Drop module from palette
                module_type = text.split(":", 1)[1]
                if module_type == "group":
                    self._create_group(pos)
                elif module_type == "waypoint":
                    self._create_waypoint(pos)
                else:
                    self._create_module(module_type, pos)
                event.acceptProposedAction()
                return
            
            elif text.startswith("tag:"):
                # Drop tag onto node
                tag_name = text.split(":", 1)[1]
                node = self._research_scene.get_node_at(pos)
                if node:
                    node.add_tag(tag_name)
                event.acceptProposedAction()
                return
        
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path.lower().endswith('.md'):
                        self._import_markdown(path, pos)
                    elif path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        self._import_image_to_selected(path)
            event.acceptProposedAction()
            return
        
        super().dropEvent(event)
    
    def _create_group(self, pos: QPointF) -> None:
        """Create a new group at position."""
        # Get current group color from palette
        group_color = "#78909C"  # Default fallback
        main_window = self.parent()
        if main_window and hasattr(main_window, 'module_palette'):
            # The group item is stored in group_item attribute
            if hasattr(main_window.module_palette, 'group_item'):
                group_color = main_window.module_palette.group_item._color.name()
        
        group_data = GroupData(
            position=Position(pos.x(), pos.y()),
            width=300,
            height=200,
            name="New Group",
            color=group_color
        )
        
        group = GroupItem(group_data)
        self._research_scene.addItem(group)
        self._research_scene._groups[group_data.id] = group
        group.signals.moved.connect(self._research_scene.update_group_nodes_position)
        group.signals.color_changed.connect(self._research_scene.update_group_color_visuals)
    
    def _create_module(self, module_type: str, pos: QPointF) -> None:
        """Create a new pipeline module at position."""
        node_data = NodeData(
            type="pipeline_module",
            position=Position(pos.x(), pos.y()),
            metadata=NodeMetadata(
                module_name=f"New {module_type.capitalize()}",
                module_type=module_type
            )
        )
        
        node = PipelineModuleItem(node_data)
        self._research_scene.add_node(node)
        
        # V3.9.0: Apply current palette color to new node
        main_window = self.parent()
        if main_window and hasattr(main_window, 'module_palette'):
            current_color = main_window.module_palette.get_color(module_type)
            node.set_color(current_color)
    
    def _create_waypoint(self, pos: QPointF) -> None:
        """Create a new waypoint at position."""
        node_data = NodeData(
            type="waypoint",
            position=Position(pos.x(), pos.y())
        )
        
        # V3.9.0: Initialize with current pipeline color
        waypoint = WaypointItem(
            node_data, 
            initial_color=self._research_scene._pipeline_edge_color
        )
        self._research_scene.add_waypoint(waypoint)
    
    def _import_markdown(self, path: str, pos: QPointF) -> None:
        """Import a markdown file as a reference node."""
        pm = self._research_scene.project_manager
        if not pm:
            return
        
        # Check if pipeline exists
        if not self._research_scene.get_project_data().pipeline_initialized:
            if not any(isinstance(n, PipelineModuleItem) for n in self._research_scene._nodes.values()):
                dialog = PipelineRequiredDialog(self)
                dialog.exec()
                return
        
        # Copy file to assets
        relative_path = pm.copy_markdown_to_assets(path)
        if not relative_path:
            QMessageBox.warning(self, "Import Failed", f"Could not import file: {path}")
            return
        
        # Create reference node
        title = extract_title_from_filename(path)
        node_data = NodeData(
            type="reference_paper",
            position=Position(pos.x(), pos.y()),
            metadata=NodeMetadata(
                title=title,
                relative_path_to_md=relative_path
            )
        )
        
        node = ReferenceNodeItem(node_data)
        self._research_scene.add_node(node)
    
    def _import_image_to_selected(self, path: str) -> None:
        """Import an image as a snippet to the selected node."""
        pm = self._research_scene.project_manager
        if not pm:
            return
        
        # Get selected node
        selected = self._research_scene.selectedItems()
        node = None
        for item in selected:
            if isinstance(item, BaseNodeItem):
                node = item
                break
        
        if not node:
            QMessageBox.information(
                self, "No Selection",
                "Please select a node to add the image to."
            )
            return
        
        # Copy image to assets
        relative_path = pm.copy_image_to_assets(path)
        if relative_path:
            node.add_image_snippet(relative_path)
    
    def paste_clipboard_image(self) -> None:
        """Paste image from clipboard to selected node."""
        pm = self._research_scene.project_manager
        if not pm:
            return
        
        # Get selected node
        selected = self._research_scene.selectedItems()
        node = None
        for item in selected:
            if isinstance(item, BaseNodeItem):
                node = item
                break
        
        if not node:
            QMessageBox.information(
                self, "No Selection",
                "Please select a node to paste the image to."
            )
            return
        
        # Get clipboard image
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        
        if image.isNull():
            QMessageBox.information(
                self, "No Image",
                "No image found in clipboard."
            )
            return
        
        # Save image to assets
        buffer = QByteArray()
        buf = QBuffer(buffer)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buf, "PNG")
        buf.close()
        
        relative_path = pm.save_clipboard_image(buffer.data(), ".png")
        if relative_path:
            node.add_image_snippet(relative_path)


# ============================================================================
# Main Window
# ============================================================================
class MainWindow(QMainWindow):
    """
    Main application window.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ResearchFlow")
        self.setMinimumSize(1000, 700)
        self.resize(1280, 800)
        
        self.project_manager = ProjectManager()
        
        # V3.9.0: Initialize undo manager
        self.undo_manager = UndoManager(context=self)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_shortcuts()  # V3.9.0
        self._create_undo_actions() # V3.9.0
        
        # Show welcome dialog
        self._show_welcome()
    
    def _setup_ui(self) -> None:
        """Setup the main UI components."""
        # Central widget with scene and view
        self.scene = ResearchScene(self)
        self.view = ResearchView(self.scene, self)
        self.setCentralWidget(self.view)
        
        # Connect Scene Signals for Undo/Redo (V3.9.0)
        self.scene.node_added_requested.connect(self._on_node_added)
        self.scene.node_removed_requested.connect(self._on_node_removed)
        self.scene.node_moved_requested.connect(self._on_node_moved)
        self.scene.edge_added_requested.connect(self._on_edge_added)
        self.scene.edge_removed_requested.connect(self._on_edge_removed)
        self.scene.group_added_requested.connect(self._on_group_added)
        self.scene.group_removed_requested.connect(self._on_group_removed)
        self.scene.group_moved_requested.connect(self._on_group_moved)
        self.scene.node_group_changed.connect(self._on_node_group_changed)
        
        # V3.9.0: Connect Snippet signals for Undo/Redo
        self.scene.snippet_add_requested.connect(self._on_snippet_add)
        self.scene.snippet_remove_requested.connect(self._on_snippet_remove)
        self.scene.snippet_move_requested.connect(self._on_snippet_move)
        self.scene.snippet_edit_requested.connect(self._on_snippet_edit)
        
        # V3.9.0: Connect Node metadata edit signal
        self.scene.metadata_edit_requested.connect(self._on_metadata_edit)
        
        # V3.9.0: Connect tag toggle and group name/size edit signals
        self.scene.tag_toggle_requested.connect(self._on_tag_toggle)
        self.scene.group_name_edit_requested.connect(self._on_group_name_edit)
        self.scene.group_size_requested.connect(self._on_group_size_edit)
        
        # Project dock (Replaces Tag dock)
        self.project_dock = ProjectDockWidget(self)
        # Tag signals (Undo/Redo)
        self.project_dock.tag_added_requested.connect(self._on_tag_added)
        self.project_dock.tag_removed_requested.connect(self._on_tag_removed)
        self.project_dock.tag_renamed_requested.connect(self._on_tag_renamed_cmd)
        self.project_dock.tag_color_changed_requested.connect(self._on_tag_color_changed_undo)
        self.project_dock.move_tag_requested.connect(self._on_move_tag)
        
        # Todo signals (Undo/Redo)
        self.project_dock.todo_added_requested.connect(self._on_todo_added)
        self.project_dock.todo_removed_requested.connect(self._on_todo_removed)
        self.project_dock.todo_edited_requested.connect(self._on_todo_edited)
        self.project_dock.todo_toggled_requested.connect(self._on_todo_toggled)
        self.project_dock.move_todo_requested.connect(self._on_todo_moved)
        
        # Project signals
        self.project_dock.description_changed.connect(self._on_description_changed_undo)
        # self.project_dock.todo_changed.connect(self._on_todo_changed) # Handled by specific signals now
        self.project_dock.edge_color_changed.connect(self._on_edge_color_changed_undo)
        self.project_dock.close_requested.connect(self._animate_dock_hide)
        
        # V3.9.0: Connect tag sync signals (after undo commands modify dock)
        self.project_dock.tag_renamed.connect(self._on_tag_renamed_sync)
        self.project_dock.tag_removed.connect(self._on_tag_removed_sync)
        self.project_dock.tag_color_changed.connect(self._on_tag_color_changed_sync)
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)
        
        # Sidebar Toggle Button
        self.sidebar_toggle = QPushButton("❯", self)
        self.sidebar_toggle.setObjectName("SidebarToggle")
        self.sidebar_toggle.setFixedSize(36, 48)
        self.sidebar_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sidebar_toggle.hide()
        self.sidebar_toggle.clicked.connect(self._animate_dock_show)
        
        # Dock animation
        self._dock_animation = None
        self._dock_target_width = 280
        self._dock_is_animating = False
        
        # Handle visibility
        self.project_dock.visibilityChanged.connect(self._on_dock_visibility_changed)
    
    def _animate_dock_show(self) -> None:
        """Animate dock widget sliding in."""
        if self._dock_is_animating:
            return
        self._dock_is_animating = True
        
        self.project_dock.setMinimumWidth(0)
        self.project_dock.setMaximumWidth(0)
        self.project_dock.show()
        
        self._dock_animation = QVariantAnimation(self)
        self._dock_animation.setStartValue(0)
        self._dock_animation.setEndValue(self._dock_target_width)
        self._dock_animation.setDuration(180)
        self._dock_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._dock_animation.valueChanged.connect(self._set_dock_width)
        self._dock_animation.finished.connect(self._finish_dock_show)
        self._dock_animation.start()
    
    def _animate_dock_hide(self) -> None:
        """Animate dock widget sliding out."""
        if self._dock_is_animating:
            return
        self._dock_is_animating = True
        
        self._dock_target_width = self.project_dock.width()
        
        self._dock_animation = QVariantAnimation(self)
        self._dock_animation.setStartValue(self.project_dock.width())
        self._dock_animation.setEndValue(0)
        self._dock_animation.setDuration(150)
        self._dock_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        self._dock_animation.valueChanged.connect(self._set_dock_width)
        self._dock_animation.finished.connect(self._finish_dock_hide)
        self._dock_animation.start()
    
    def _set_dock_width(self, width: int) -> None:
        """Set dock width during animation."""
        self.project_dock.setMinimumWidth(width)
        self.project_dock.setMaximumWidth(width)
    
    def _finish_dock_show(self) -> None:
        """Finish show animation - restore normal sizing."""
        self.project_dock.setMinimumWidth(250)
        self.project_dock.setMaximumWidth(QWIDGETSIZE_MAX)
        self._dock_is_animating = False
    
    def _finish_dock_hide(self) -> None:
        """Finish hide animation."""
        self.project_dock.hide()
        self.project_dock.setMinimumWidth(250)
        self.project_dock.setMaximumWidth(QWIDGETSIZE_MAX)
        self._dock_is_animating = False
    
    def _on_dock_visibility_changed(self, visible: bool) -> None:
        self.sidebar_toggle.setVisible(not visible)
        if not visible:
            self.sidebar_toggle.raise_()
            
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Position toggle button at center left
        if hasattr(self, 'sidebar_toggle'):
            y = (self.height() - self.sidebar_toggle.height()) // 2
            self.sidebar_toggle.move(0, y)
            self.sidebar_toggle.raise_()
            
    def closeEvent(self, event) -> None:
        """Handle application close event - save and clean."""
        if self.project_manager.is_project_open:
            # Gather state including layout
            project_data = self.scene.get_project_data()
            project_data.global_tags = self.project_dock.get_tags()
            project_data.description = self.project_dock.get_description()
            project_data.todos = self.project_dock.get_todos()
            
            current = self.project_manager.project_data
            project_data.pipeline_edge_color = current.pipeline_edge_color
            project_data.reference_edge_color = current.reference_edge_color
            project_data.dock_layout = self.project_dock.get_layout_state()
            
            self.project_manager.project_data = project_data
            
            # Clean orphaned data
            cleaned = self.project_manager.validate_and_clean_data()
            if any(cleaned.values()):
                print(f"Cleaned orphaned data on exit: {cleaned}")
            
            # Save
            self.project_manager.save_project()
        
        event.accept()
    
    def _setup_menu(self) -> None:
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Project...", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("&Import Markdown...", self)
        import_action.triggered.connect(self._import_markdown_dialog)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        paste_action = QAction("&Paste Image", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._paste_image)
        edit_menu.addAction(paste_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(lambda: self.view.scale(1.2, 1.2))
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(lambda: self.view.scale(1/1.2, 1/1.2))
        view_menu.addAction(zoom_out_action)
        
        fit_action = QAction("&Fit to View", self)
        fit_action.triggered.connect(self._fit_to_view)
        view_menu.addAction(fit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self) -> None:
        """Setup the toolbar with module palette."""
        toolbar = QToolBar("Modules")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        self.module_palette = ModulePalette()
        self.module_palette.color_changed.connect(self._on_module_color_changed)
        toolbar.addWidget(self.module_palette)
    
    def _setup_statusbar(self) -> None:
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Welcome to ResearchFlow")
    
    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts (undo/redo handled via menu actions)."""
        # Undo/Redo shortcuts are set via _create_undo_actions menu items
        # No additional QShortcut registration needed to avoid conflict
        pass
    
    def _undo(self) -> None:
        """Perform undo operation."""
        if not self.undo_manager.can_undo():
            self.statusbar.showMessage("Nothing to undo", 2000)
            return
        if self.undo_manager.undo():
            remaining = len(self.undo_manager._undo_stack)
            self.statusbar.showMessage(f"Undo performed ({remaining} remaining)", 2000)
    
    def _redo(self) -> None:
        """Perform redo operation."""
        if not self.undo_manager.can_redo():
            self.statusbar.showMessage("Nothing to redo", 2000)
            return
        if self.undo_manager.redo():
            remaining = len(self.undo_manager._redo_stack)
            self.statusbar.showMessage(f"Redo performed ({remaining} remaining)", 2000)

    
    def _show_welcome(self) -> None:
        """Show the welcome dialog."""
        projects = self.project_manager.list_existing_projects()
        dialog = WelcomeDialog(projects, self)
        dialog.project_selected.connect(self._on_project_selected)
        
        if dialog.exec() != WelcomeDialog.DialogCode.Accepted:
            # No project selected, maybe show empty state
            pass
    
    def _on_project_selected(self, name: str, is_new: bool) -> None:
        """Handle project selection from welcome dialog."""
        if is_new:
            if self.project_manager.create_project(name):
                self._load_current_project()
                self.statusbar.showMessage(f"Created project: {name}")
            else:
                QMessageBox.warning(
                    self, "Project Exists",
                    f"A project named '{name}' already exists."
                )
        else:
            if self.project_manager.open_project(name):
                self._load_current_project()
                self.statusbar.showMessage(f"Opened project: {name}")
            else:
                QMessageBox.warning(
                    self, "Open Failed",
                    f"Could not open project: {name}"
                )
    
    def _load_current_project(self) -> None:
        """Load the current project into the scene."""
        if not self.project_manager.is_project_open:
            return
        
        data = self.project_manager.project_data
        
        # V3.9.0: Clear undo history and set flag to prevent recording load operations
        self.undo_manager.clear()
        self.scene._is_undo_operation = True
        
        try:
            # Load scene data
            self.scene.project_manager = self.project_manager
            self.scene.set_edge_colors(data.pipeline_edge_color, data.reference_edge_color)
            self.scene.load_project_data(data)
            
            # Load project dock data
            self.project_dock.set_project_data(
                data.description,
                data.todos,
                data.global_tags,
                data.pipeline_edge_color,
                data.reference_edge_color
            )
            
            # Load layout state
            if data.dock_layout:
                self.project_dock.set_layout_state(data.dock_layout)
            
            # Load module palette colors and apply to existing nodes
            if data.module_colors:
                self.module_palette.set_colors(data.module_colors)
                # Apply colors to already loaded nodes
                for node in self.scene._nodes.values():
                    if isinstance(node, PipelineModuleItem):
                        mtype = node.module_type
                        if mtype in data.module_colors:
                            node.set_color(data.module_colors[mtype])
            
            # V3.9.0: Always sync waypoint palette color with pipeline edge color
            self.module_palette.waypoint_item.set_color(data.pipeline_edge_color)
        finally:
            # Restore normal operation
            self.scene._is_undo_operation = False
        
        # V3.9.0: Sync tag colors to nodes after load
        self._sync_all_tag_colors()
        
        # V3.9.0: Load undo history AFTER project is fully loaded
        self.undo_manager.load_from_file(self.project_manager.current_project_path)
        
        self.setWindowTitle(f"ResearchFlow - {self.project_manager.current_project_name}")
    
    # --- New V1.2.0 Handlers ---
    
    def _on_description_changed(self, text: str) -> None:
        if self.project_manager.is_project_open:
            self.project_manager.project_data.description = text
            self._auto_save()
    
    def _create_undo_actions(self):
        """Create Undo/Redo actions in Edit menu."""
        # Find Edit menu
        menubar = self.menuBar()
        edit_menu = None
        for action in menubar.actions():
            if action.text() == "&Edit":
                edit_menu = action.menu()
                break
        
        if edit_menu:
            edit_menu.addSeparator()
            
            undo_action = QAction("Undo", self)
            undo_action.setShortcut(QKeySequence.StandardKey.Undo)
            undo_action.triggered.connect(self._undo)
            edit_menu.addAction(undo_action)
            
            redo_action = QAction("Redo", self)
            redo_action.setShortcut(QKeySequence.StandardKey.Redo)
            redo_action.triggered.connect(self._redo)
            edit_menu.addAction(redo_action)

    # --- Undo/Redo Handlers ---

    def _on_description_changed_undo(self, new_desc: str) -> None:
        """Handle description change with Undo."""
        if self.project_manager.is_project_open:
            cmd = DescriptionChangeCommand(self, self.project_manager.project_data.description, new_desc)
            self.undo_manager.execute(cmd)
            self._auto_save()

    def _on_todo_added(self, text: str):
        index = self.project_dock.todo_list.count()
        cmd = TodoAddCommand(self, text, index)
        self.undo_manager.execute(cmd)

    def _on_todo_removed(self, index: int, text: str, is_done: bool):
        cmd = TodoRemoveCommand(self, index, text, is_done)
        self.undo_manager.execute(cmd)

    def _on_todo_edited(self, index: int, old_text: str, new_text: str):
         cmd = TodoEditCommand(self, index, old_text, new_text)
         self.undo_manager.execute(cmd)

    def _on_todo_toggled(self, index: int, new_state: bool):
         cmd = TodoToggleCommand(self, index, new_state)
         self.undo_manager.execute(cmd)
   
    def _on_todo_moved(self, from_index: int, to_index: int):
         cmd = TodoMoveCommand(self, from_index, to_index)
         self.undo_manager.execute(cmd)

    def _on_tag_added(self, name: str):
        cmd = TagAddCommand(self, name)
        self.undo_manager.execute(cmd)

    def _on_tag_removed(self, name: str, color: str, index: int):
        cmd = TagRemoveCommand(self, name, color, index)
        self.undo_manager.execute(cmd)

    def _on_tag_renamed_cmd(self, old_name: str, new_name: str):
        cmd = TagRenameCommand(self, old_name, new_name)
        self.undo_manager.execute(cmd)

    def _on_tag_color_changed_undo(self, name: str, old_color: str, new_color: str):
        cmd = TagColorChangeCommand(self, name, old_color, new_color)
        self.undo_manager.execute(cmd)

    def _on_move_tag(self, from_index: int, to_index: int):
        cmd = TagMoveCommand(self, from_index, to_index)
        self.undo_manager.execute(cmd)

    def _on_edge_color_changed_undo(self, pipeline_color: str, reference_color: str) -> None:
        if self.project_manager.is_project_open:
            old_p = self.project_manager.project_data.pipeline_edge_color
            old_r = self.project_manager.project_data.reference_edge_color
            
            if old_p != pipeline_color or old_r != reference_color:
                cmd = GlobalEdgeColorChangeCommand(self, old_p, old_r, pipeline_color, reference_color)
                self.undo_manager.execute(cmd)
    
    def _on_module_color_changed(self, module_type: str, color: str) -> None:
        """Handle module palette color change - update existing nodes."""
        if self.project_manager.is_project_open:
            # Check for actual change to prevent loop with UndoCommand
            existing = self.project_manager.project_data.module_colors.get(module_type, "#607D8B")
            if existing == color:
                return
            
            cmd = ModulePaletteColorChangeCommand(self, module_type, existing, color)
            self.undo_manager.execute(cmd)
            self._auto_save()
            
    # --- Scene Signal Handlers (V3.9.0) ---
    
    def _on_node_added(self, node_data_dict: dict):
        cmd = AddNodeCommand(self, node_data_dict)
        self.undo_manager.execute(cmd)
        
    def _on_node_removed(self, node_data_dict: dict, connected_edges: list):
        cmd = RemoveNodeCommand(self, node_data_dict, connected_edges)
        self.undo_manager.execute(cmd)
        
    def _on_node_moved(self, node_id: str, old_pos: tuple, new_pos: tuple):
        # Only create command if actually moved significantly
        if old_pos != new_pos:
            cmd = NodePositionCommand(self, node_id, old_pos[0], old_pos[1], new_pos[0], new_pos[1])
            self.undo_manager.execute(cmd)
            
    def _on_edge_added(self, edge_data_dict: dict, target_node_id: str = "", cloned_snippet_ids: list = None):
        """Handle edge added with optional cloned snippet info."""
        cmd = AddEdgeCommand(self, edge_data_dict, target_node_id, cloned_snippet_ids or [])
        self.undo_manager.execute(cmd)
        
    def _on_edge_removed(self, edge_data_dict: dict):
        cmd = RemoveEdgeCommand(self, edge_data_dict)
        self.undo_manager.execute(cmd)
        
    def _on_group_added(self, group_data_dict: dict):
        cmd = AddGroupCommand(self, group_data_dict)
        self.undo_manager.execute(cmd)
        
    def _on_group_removed(self, group_data_dict: dict):
        cmd = RemoveGroupCommand(self, group_data_dict)
        self.undo_manager.execute(cmd)
        
    def _on_group_moved(self, group_id: str, old_pos: tuple, new_pos: tuple):
        if old_pos != new_pos:
            cmd = GroupMoveCommand(self, group_id, old_pos, new_pos)
            self.undo_manager.execute(cmd)
    
    def _on_node_group_changed(self, node_id: str, old_group_id, new_group_id):
        """Handle node added/removed from group for undo."""
        cmd = NodeGroupChangeCommand(self, node_id, old_group_id, new_group_id)
        self.undo_manager.execute(cmd)
    
    # --- V3.9.0: Snippet Undo/Redo Handlers ---
    
    def _on_snippet_add(self, node_id: str, snippet_data: dict):
        """Handle snippet add request."""
        cmd = SnippetAddCommand(self, node_id, snippet_data)
        self.undo_manager.execute(cmd)
    
    def _on_snippet_remove(self, node_id: str, snippet_data: dict, index: int):
        """Handle snippet remove request."""
        cmd = SnippetRemoveCommand(self, node_id, snippet_data, index)
        self.undo_manager.execute(cmd)
    
    def _on_snippet_move(self, node_id: str, snippet_id: str, from_idx: int, to_idx: int):
        """Handle snippet move request."""
        cmd = SnippetMoveCommand(self, node_id, snippet_id, from_idx, to_idx)
        self.undo_manager.execute(cmd)
    
    def _on_snippet_edit(self, node_id: str, snippet_id: str, field: str, old_val: str, new_val: str):
        """Handle snippet edit request."""
        cmd = SnippetEditCommand(self, node_id, snippet_id, field, old_val, new_val)
        self.undo_manager.execute(cmd)
    
    def _on_metadata_edit(self, node_id: str, field: str, old_val: str, new_val: str):
        """Handle node metadata edit request."""
        cmd = NodeMetadataEditCommand(self, node_id, field, old_val, new_val)
        self.undo_manager.execute(cmd)
    
    def _on_tag_toggle(self, node_id: str, tag_name: str, was_added: bool):
        """Handle node tag toggle request (add/remove tag from node)."""
        cmd = NodeTagToggleCommand(self, node_id, tag_name, was_added)
        self.undo_manager.execute(cmd)
    
    def _on_group_name_edit(self, group_id: str, old_name: str, new_name: str):
        """Handle group name edit request."""
        cmd = GroupNameEditCommand(self, group_id, old_name, new_name)
        self.undo_manager.execute(cmd)
    
    def _on_group_size_edit(self, group_id: str, old_rect: tuple, new_rect: tuple):
        """Handle group size edit request."""
        cmd = GroupSizeCommand(self, group_id, old_rect, new_rect)
        self.undo_manager.execute(cmd)
    
    def _new_project(self) -> None:
        """Create a new project via dialog."""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "New Project",
            "Project Name:"
        )
        if ok and name:
            if self.project_manager.create_project(name):
                self._load_current_project()
                self.statusbar.showMessage(f"Created project: {name}")
            else:
                QMessageBox.warning(
                    self, "Project Exists",
                    f"A project named '{name}' already exists."
                )
    
    def _open_project(self) -> None:
        """Open a project via dialog."""
        projects = self.project_manager.list_existing_projects()
        if not projects:
            QMessageBox.information(
                self, "No Projects",
                "No existing projects found. Create a new one!"
            )
            return
        
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self, "Open Project",
            "Select Project:",
            projects, 0, False
        )
        if ok and name:
            if self.project_manager.open_project(name):
                self._load_current_project()
                self.statusbar.showMessage(f"Opened project: {name}")
    
    def _save_project(self) -> None:
        """Save the current project."""
        if not self.project_manager.is_project_open:
            QMessageBox.warning(
                self, "No Project",
                "No project is currently open."
            )
            return
            
        # Update project data from scene
        project_data = self.scene.get_project_data()
        
        # Populate dock fields
        project_data.global_tags = self.project_dock.get_tags()
        project_data.description = self.project_dock.get_description()
        project_data.todos = self.project_dock.get_todos()
        
        # Preserve colors
        current = self.project_manager.project_data
        project_data.pipeline_edge_color = current.pipeline_edge_color
        project_data.reference_edge_color = current.reference_edge_color
        
        # Save layout state
        project_data.dock_layout = self.project_dock.get_layout_state()
        
        # Save module colors
        project_data.module_colors = self.module_palette.get_colors()
        
        self.project_manager.project_data = project_data
        
        # Validate and clean
        cleaned = self.project_manager.validate_and_clean_data()
        if any(cleaned.values()):
            print(f"Cleaned orphaned data: {cleaned}")
        
        if self.project_manager.save_project():
            self.statusbar.showMessage("Project saved", 3000)
        else:
            QMessageBox.warning(
                self, "Save Failed",
                "Could not save project."
            )
    
    def _import_markdown_dialog(self) -> None:
        """Show file dialog to import markdown."""
        if not self.project_manager.is_project_open:
            QMessageBox.warning(
                self, "No Project",
                "Please open or create a project first."
            )
            return
        
        # Check if pipeline exists
        if not self.scene.get_project_data().pipeline_initialized:
            if not any(isinstance(n, PipelineModuleItem) for n in self.scene._nodes.values()):
                dialog = PipelineRequiredDialog(self)
                dialog.exec()
                return
        
        files, _ = QFileDialog.getOpenFileNames(
            self, "Import Markdown Files",
            "", "Markdown Files (*.md);;All Files (*)"
        )
        
        for path in files:
            pos = QPointF(100 + len(self.scene._nodes) * 50, 100)
            self.view._import_markdown(path, pos)
    
    def _paste_image(self) -> None:
        """Paste image from clipboard."""
        self.view.paste_clipboard_image()
    
    def _fit_to_view(self) -> None:
        """Fit all items in view."""
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self, "About ResearchFlow",
            "<h2>ResearchFlow</h2>"
            "<p>Version 3.9.0</p>"
            "<p>A portable research management tool for academics.</p>"
            "<p>Built with Python and PyQt6.</p>"
            "<hr>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Pipeline workflow design</li>"
            "<li>Reference paper management</li>"
            "<li>Snippet extraction and copying</li>"
            "<li>Tag-based organization</li>"
            "<li>Node grouping (subgraphs)</li>"
            "</ul>"
        )
    
    def _on_tag_added(self, tag: str) -> None:
        """Handle new tag creation."""
        self._auto_save()
    
    def _on_tag_removed(self, tag: str) -> None:
        """Handle tag removal."""
        # Remove from all nodes
        for node in self.scene._nodes.values():
            node.remove_tag(tag)
        self._auto_save()
    
    def _on_tag_renamed_sync(self, old_name: str, new_name: str) -> None:
        """Handle tag rename - sync to all nodes."""
        for node in self.scene._nodes.values():
            if old_name in node.node_data.tags:
                # Replace old tag with new
                idx = node.node_data.tags.index(old_name)
                node.node_data.tags[idx] = new_name
                # Rebuild tag badges to reflect new name
                node._rebuild_tags()
                node.update_layout()
        self._auto_save()
    
    def _on_tag_removed_sync(self, tag_name: str) -> None:
        """Handle tag removal - remove from all nodes."""
        for node in self.scene._nodes.values():
            if tag_name in node.node_data.tags:
                node.node_data.tags.remove(tag_name)
                node._rebuild_tags()
                node.update_layout()
        self._auto_save()
    
    def _on_tag_color_changed_sync(self, tag_name: str, color: str) -> None:
        """Handle tag color change - sync to all nodes."""
        for node in self.scene._nodes.values():
            if tag_name in node.node_data.tags:
                # Update the tag badge color
                for badge in node._tag_badges:
                    if badge.tag_name == tag_name:
                        badge.set_color(color)
        self._auto_save()
    
    def _sync_all_tag_colors(self) -> None:
        """Sync all tag colors from dock to nodes (called after project load)."""
        # Build tag color map from dock
        tag_colors = {}
        for tag_data in self.project_dock.get_tags():
            color = tag_data.get("color")
            if color:
                tag_colors[tag_data["name"]] = color
        
        # Apply colors to all node badges
        for node in self.scene._nodes.values():
            for badge in node._tag_badges:
                if badge.tag_name in tag_colors:
                    badge.set_color(tag_colors[badge.tag_name])
    
    def _auto_save(self) -> None:
        """Auto-save the project with data validation."""
        if self.project_manager.is_project_open:
            project_data = self.scene.get_project_data()
            
            # Populate V1.2.0 fields
            project_data.global_tags = self.project_dock.get_tags()
            project_data.description = self.project_dock.get_description()
            project_data.todos = self.project_dock.get_todos()
            
            current = self.project_manager.project_data
            project_data.pipeline_edge_color = current.pipeline_edge_color
            project_data.reference_edge_color = current.reference_edge_color
            
            self.project_manager.project_data = project_data
            # Validate and clean orphaned data
            self.project_manager.validate_and_clean_data()
            self.project_manager.save_project()
    
    def closeEvent(self, event) -> None:
        """Handle window close - ensure clean shutdown."""
        # Stop any running animations to prevent process hanging
        if self._dock_animation:
            self._dock_animation.stop()
            self._dock_animation = None
        
        # Stop view zoom animation
        if hasattr(self, 'view') and self.view._zoom_animation:
            self.view._zoom_animation.stop()
            self.view._zoom_animation = None
        
        # Save project if open
        if self.project_manager.is_project_open:
            self._save_project()
        
        # Accept close and quit application
        event.accept()
        QApplication.instance().quit()


# ============================================================================
# Application Entry Point
# ============================================================================
def main():
    # Ensure projects directory exists
    projects_dir = get_app_root() / "projects"
    projects_dir.mkdir(exist_ok=True)
    
    app = QApplication(sys.argv)
    
    # Set Global Icon (use resource path for PyInstaller compatibility)
    icon_path = get_resource_path("icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Apply Modern Theme Stylesheet
    app.setStyleSheet(ModernTheme.get_stylesheet())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
