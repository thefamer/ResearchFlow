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
from PyQt6.QtCore import Qt, QPointF, QRectF, QMimeData, QByteArray, QBuffer, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import (
    QAction, QKeySequence, QDragEnterEvent, QDropEvent,
    QMouseEvent, QWheelEvent, QClipboard, QImage, QColor, QPainter, QBrush, QIcon, QPen
)

from models import (
    ProjectData, NodeData, NodeMetadata, Position, EdgeData, Snippet,
    generate_uuid
)
from utils import ProjectManager, extract_title_from_filename, get_app_root, ModernTheme
from graphics_items import (
    BaseNodeItem, PipelineModuleItem, ReferenceNodeItem, EdgeItem,
    TempConnectionLine, Colors, SnippetItem
)
from widgets import (
    WelcomeDialog, ProjectDockWidget, MarkdownViewerDialog, ModulePalette,
    PipelineRequiredDialog
)


# ============================================================================
# Custom Graphics Scene
# ============================================================================
class ResearchScene(QGraphicsScene):
    """
    Custom scene handling node management and connections.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        
        # Grid settings
        self._grid_size = 25
        self._grid_color = QColor("#E0E0E0")
        self._bg_color = QColor("#FAFAFA")
        
        self._nodes: dict[str, BaseNodeItem] = {}
        self._edges: dict[str, EdgeItem] = {}
        self._temp_connection: Optional[TempConnectionLine] = None
        self._connection_source: Optional[BaseNodeItem] = None
        self._suppress_context_menu: bool = False  # Flag to prevent context menu after connection
        
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
        """Set edge colors and update all existing edges."""
        self._pipeline_edge_color = pipeline_color
        self._reference_edge_color = reference_color
        for edge in self._edges.values():
            edge.update_colors(pipeline_color, reference_color)
    
    def add_node(self, node: BaseNodeItem) -> None:
        """Add a node to the scene."""
        self.addItem(node)
        self._nodes[node.node_data.id] = node
        
        # Connect signals
        node.signals.data_changed.connect(self._on_node_changed)
        node.signals.expand_requested.connect(self._on_expand_requested)
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and its edges from the scene."""
        if node_id in self._nodes:
            node = self._nodes.pop(node_id)
            
            # Remove connected edges
            edges_to_remove = []
            for edge_id, edge in self._edges.items():
                if edge.source_node == node or edge.target_node == node:
                    edges_to_remove.append(edge_id)
            
            for edge_id in edges_to_remove:
                edge = self._edges.pop(edge_id)
                self.removeItem(edge)
            
            self.removeItem(node)
    
    def add_edge(self, source_id: str, target_id: str, edge_id: str = None) -> Optional[EdgeItem]:
        """Create an edge between two nodes."""
        if source_id in self._nodes and target_id in self._nodes:
            source = self._nodes[source_id]
            target = self._nodes[target_id]
            
            edge = EdgeItem(source, target, edge_id,
                          self._pipeline_edge_color, self._reference_edge_color)
            self.addItem(edge)
            self._edges[edge.edge_id] = edge
            
            return edge
        return None
    
    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge by its ID."""
        if edge_id in self._edges:
            edge = self._edges.pop(edge_id)
            self.removeItem(edge)
    
    def get_node_at(self, pos: QPointF) -> Optional[BaseNodeItem]:
        """Get the node at the given scene position."""
        items = self.items(pos)
        for item in items:
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
    
    def start_connection(self, source: BaseNodeItem, start_pos: QPointF) -> None:
        """Start drawing a temporary connection."""
        self._connection_source = source
        source.set_connection_source(True)
        self._temp_connection = TempConnectionLine(start_pos)
        self.addItem(self._temp_connection)
    
    def update_temp_connection(self, pos: QPointF) -> None:
        """Update the temporary connection end point."""
        if self._temp_connection:
            self._temp_connection.update_end(pos)
    
    def complete_connection(self, target: BaseNodeItem) -> bool:
        """Complete a connection to the target node with deep copy."""
        if self._connection_source and target and self._connection_source != target:
            source = self._connection_source
            
            # Deep copy snippets only when connecting Reference → Pipeline
            if isinstance(source, ReferenceNodeItem) and isinstance(target, PipelineModuleItem):
                snippets = source.get_snippets_data()
                if snippets:
                    target.add_cloned_snippets(snippets, source.get_title())
            
            # Create edge for any connection type
            edge_id = generate_uuid()
            self.add_edge(source.node_data.id, target.node_data.id, edge_id)
            
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
    
    def clear_all(self) -> None:
        """Clear all items from the scene."""
        self._nodes.clear()
        self._edges.clear()
        self.clear()
    
    def get_project_data(self) -> ProjectData:
        """Export scene state to ProjectData."""
        data = ProjectData()
        
        # Export nodes
        for node in self._nodes.values():
            data.nodes.append(node.node_data)
        
        # Export edges
        for edge_id, edge in self._edges.items():
            edge_data = EdgeData(
                id=edge_id,
                source_id=edge.source_node.node_data.id,
                target_id=edge.target_node.node_data.id
            )
            data.edges.append(edge_data)
        
        # Check if pipeline is initialized
        data.pipeline_initialized = any(
            isinstance(n, PipelineModuleItem) for n in self._nodes.values()
        )
        
        return data
    
    def load_project_data(self, data: ProjectData) -> None:
        """Import scene state from ProjectData."""
        self.clear_all()
        
        # Create nodes
        for node_data in data.nodes:
            if node_data.type == "pipeline_module":
                node = PipelineModuleItem(node_data)
            else:
                node = ReferenceNodeItem(node_data)
            
            self.add_node(node)
        
        # Create edges
        for edge_data in data.edges:
            self.add_edge(edge_data.source_id, edge_data.target_id, edge_data.id)


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
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        
        # Show welcome dialog
        self._show_welcome()
    
    def _setup_ui(self) -> None:
        """Setup the main UI components."""
        # Central widget with scene and view
        self.scene = ResearchScene(self)
        self.view = ResearchView(self.scene, self)
        self.setCentralWidget(self.view)
        
        # Project dock (Replaces Tag dock)
        self.project_dock = ProjectDockWidget(self)
        # Tag signals
        self.project_dock.tag_added.connect(self._on_tag_added)
        self.project_dock.tag_removed.connect(self._on_tag_removed)
        self.project_dock.tag_renamed.connect(self._on_tag_renamed)
        # Project signals
        self.project_dock.description_changed.connect(self._on_description_changed)
        self.project_dock.todo_changed.connect(self._on_todo_changed)
        self.project_dock.edge_color_changed.connect(self._on_edge_color_changed)
        self.project_dock.close_requested.connect(self._animate_dock_hide)
        
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
        
        palette = ModulePalette()
        toolbar.addWidget(palette)
    
    def _setup_statusbar(self) -> None:
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Welcome to ResearchFlow")
    
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
        
        self.setWindowTitle(f"ResearchFlow - {self.project_manager.current_project_name}")
    
    # --- New V1.2.0 Handlers ---
    
    def _on_description_changed(self, text: str) -> None:
        if self.project_manager.is_project_open:
            self.project_manager.project_data.description = text
            self._auto_save()
    
    def _on_todo_changed(self) -> None:
        if self.project_manager.is_project_open:
            self.project_manager.project_data.todos = self.project_dock.get_todos()
            self._auto_save()
    
    def _on_edge_color_changed(self, pipeline_color: str, reference_color: str) -> None:
        if self.project_manager.is_project_open:
            self.project_manager.project_data.pipeline_edge_color = pipeline_color
            self.project_manager.project_data.reference_edge_color = reference_color
            self.scene.set_edge_colors(pipeline_color, reference_color)
            self._auto_save()
    
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
            "<p>Version 3.0.0</p>"
            "<p>A portable research management tool for academics.</p>"
            "<p>Built with Python and PyQt6.</p>"
            "<hr>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Pipeline workflow design</li>"
            "<li>Reference paper management</li>"
            "<li>Snippet extraction and copying</li>"
            "<li>Tag-based organization</li>"
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
    
    def _on_tag_renamed(self, old_name: str, new_name: str) -> None:
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
        """Handle window close."""
        if self.project_manager.is_project_open:
            self._save_project()
        event.accept()


# ============================================================================
# Application Entry Point
# ============================================================================
def main():
    # Ensure projects directory exists
    projects_dir = get_app_root() / "projects"
    projects_dir.mkdir(exist_ok=True)
    
    app = QApplication(sys.argv)
    
    # Set Global Icon
    icon_path = str(get_app_root() / "icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    # Apply Modern Theme Stylesheet
    app.setStyleSheet(ModernTheme.get_stylesheet())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
