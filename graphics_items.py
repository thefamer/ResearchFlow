"""
ResearchFlow - Custom Graphics Items
QGraphicsItem subclasses for canvas rendering.
All snippets are pure QGraphicsItems (no QWidgets) for seamless canvas integration.
"""

from typing import Optional, TYPE_CHECKING
import math

from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsPolygonItem, QGraphicsPathItem, QGraphicsPixmapItem,
    QGraphicsEllipseItem,
    QGraphicsSceneMouseEvent, QGraphicsSceneHoverEvent,
    QStyleOptionGraphicsItem, QWidget, QMenu, QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QRectF, QRect, QPointF, QSizeF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPolygonF,
    QPainterPath, QPixmap, QFontMetrics, QCursor
)

from models import Snippet, NodeData, NodeMetadata, Position, generate_uuid
from utils import ModernTheme

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QGraphicsScene


# ============================================================================
# Color Palette
# ============================================================================
class Colors:
    """Application color palette."""
    # Node backgrounds
    PIPELINE_INPUT = QColor("#4CAF50")      # Green
    PIPELINE_OUTPUT = QColor("#2196F3")     # Blue
    PIPELINE_PROCESS = QColor("#9C27B0")    # Purple
    PIPELINE_DECISION = QColor("#FF9800")   # Orange
    REFERENCE = QColor("#607D8B")           # Blue Grey
    
    # UI elements
    HEADER_BG = QColor("#37474F")           # Dark Blue Grey
    SNIPPET_BG = QColor("#ECEFF1")          # Light Grey
    SNIPPET_IMAGE_BG = QColor("#CFD8DC")    # Slightly darker grey
    TEXT = QColor("#212121")                # Near black
    TEXT_LIGHT = QColor("#FFFFFF")          # White
    BORDER = QColor("#455A64")              # Medium Blue Grey
    SELECTION = QColor("#00BCD4")           # Cyan
    HOVER = QColor("#B2EBF5")               # Light Cyan
    TAG_BG = QColor("#E91E63")              # Pink
    CONNECTION_LINE = QColor("#FF5722")     # Deep Orange


# ============================================================================
# Signal Emitter for Graphics Items
# ============================================================================
class NodeSignals(QObject):
    """Signals emitted by node items."""
    position_changed = pyqtSignal(str, float, float)  # node_id, x, y
    snippet_added = pyqtSignal(str)  # node_id (legacy, for auto-save)
    snippet_removed = pyqtSignal(str, str)  # node_id, snippet_id (legacy)
    expand_requested = pyqtSignal(str)  # node_id
    connection_started = pyqtSignal(str)  # source_node_id
    connection_completed = pyqtSignal(str, str)  # source_node_id, target_node_id
    data_changed = pyqtSignal(str)  # node_id
    drag_finished = pyqtSignal(str, object)  # node_id, modifiers (for group logic V3.5.0)
    
    # V3.9.0: Snippet undo/redo request signals
    snippet_add_requested = pyqtSignal(str, dict)  # node_id, snippet_data
    snippet_remove_requested = pyqtSignal(str, dict, int)  # node_id, snippet_data, index
    snippet_edit_requested = pyqtSignal(str, str, str, str, str)  # node_id, snippet_id, field, old, new
    snippet_move_requested = pyqtSignal(str, str, int, int)  # node_id, snippet_id, from, to
    
    # V3.9.0: Node metadata edit signal
    metadata_edit_requested = pyqtSignal(str, str, str, str)  # node_id, field, old_value, new_value
    
    # V3.9.0: Node tag toggle signal
    tag_toggle_requested = pyqtSignal(str, str, bool)  # node_id, tag_name, was_added


# ============================================================================
# Snippet Item (Pure QGraphicsItem)
# ============================================================================
class SnippetItem(QGraphicsRectItem):
    """
    A snippet displaying text or an image.
    Pure QGraphicsItem - no QWidgets used.
    Supports drag reordering and double-click editing of source_label.
    """
    
    SNIPPET_WIDTH = 180
    TEXT_PADDING = 8
    MIN_HEIGHT = 30
    IMAGE_MAX_HEIGHT = 300
    SOURCE_LABEL_HEIGHT = 18
    
    def __init__(self, snippet_data: Snippet, parent_node: "BaseNodeItem"):
        super().__init__(parent_node)
        self.snippet_data = snippet_data
        self.parent_node = parent_node
        self.width = self.SNIPPET_WIDTH
        self._pixmap: Optional[QPixmap] = None
        self._is_hover = False
        self._is_editing_label = False
        self._drag_start_y: Optional[float] = None
        
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        
        # Load image if this is an image snippet
        if snippet_data.type == "image" and snippet_data.content:
            self._load_image()
        
        self._update_geometry()
        
    def set_width(self, width: int) -> None:
        if self.width != width:
            self.width = width
            self._update_geometry()
            self.update()
        
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged:
            # Try loading image again when scene is available
            if self.scene() and self.snippet_data.type == "image" and not self._pixmap:
                self._load_image()
                if self._pixmap:
                    self._update_geometry()
                    # CRITICAL: Notify parent to resize
                    if self.parentItem() and hasattr(self.parentItem(), "update_layout"):
                        self.parentItem().update_layout()
                    
        return super().itemChange(change, value)
    
    def _load_image(self) -> None:
        """Load the image from the content path via ProjectManager."""
        scene = self.scene()
        if not scene or not hasattr(scene, "project_manager"):
            # Can't resolve path without project manager
            return
            
        pm = scene.project_manager
        path = pm.get_absolute_asset_path(self.snippet_data.content)
        
        if path and path.exists():
            self._pixmap = QPixmap(str(path))
        else:
            self._pixmap = None
    
    def _update_geometry(self) -> None:
        """Calculate and update the item geometry."""
        height = self.MIN_HEIGHT
        
        if self.snippet_data.type == "image" and self._pixmap and not self._pixmap.isNull():
            # Scale image to fit width while maintaining aspect ratio
            scaled = self._pixmap.scaledToWidth(
                int(self.width - 2 * self.TEXT_PADDING),
                Qt.TransformationMode.SmoothTransformation
            )
            height = min(scaled.height(), self.IMAGE_MAX_HEIGHT) + 2 * self.TEXT_PADDING
        else:
            # Text snippet - calculate height based on text
            font = ModernTheme.get_ui_font(9)
            metrics = QFontMetrics(font)
            text_width = int(self.width - 2 * self.TEXT_PADDING)
            text = self.snippet_data.content or "(Empty)"
            
            # Use boundingRect for accurate multi-line height calculation
            rect = metrics.boundingRect(
                QRect(0, 0, text_width, 0),
                Qt.TextFlag.TextWordWrap,
                text
            )
            height = max(self.MIN_HEIGHT, rect.height() + 2 * self.TEXT_PADDING)
        
        # Add source label height if present
        if self.snippet_data.source_label:
            height += self.SOURCE_LABEL_HEIGHT
        
        self.setRect(0, 0, self.width, height)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        """Paint the snippet."""
        rect = self.rect()
        
        # Background
        bg_color = Colors.SNIPPET_IMAGE_BG if self.snippet_data.type == "image" else Colors.SNIPPET_BG
        if self._is_hover:
            bg_color = QColor(ModernTheme.BG_TERTIARY)
        else:
            bg_color = QColor("white")
            
        painter.setBrush(bg_color)
        
        if self.isSelected():
            painter.setPen(QPen(QColor(ModernTheme.ACCENT_COLOR), 2))
        else:
            painter.setPen(QPen(QColor(ModernTheme.BORDER_LIGHT), 1))
            
        painter.drawRoundedRect(rect, 8, 8)
        
        y_offset = self.TEXT_PADDING
        
        # Draw source label if present (editable)
        if self.snippet_data.source_label:
            label_font = ModernTheme.get_ui_font(8, bold=True)
            painter.setFont(label_font)
            painter.setPen(QPen(QColor("#1565C0")))  # Blue color
            label_rect = QRectF(
                self.TEXT_PADDING, y_offset,
                self.width - 2 * self.TEXT_PADDING,
                self.SOURCE_LABEL_HEIGHT
            )
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft, self.snippet_data.source_label)
            y_offset += self.SOURCE_LABEL_HEIGHT
        
        # Draw content
        content_rect = QRectF(
            self.TEXT_PADDING, y_offset,
            self.width - 2 * self.TEXT_PADDING,
            rect.height() - y_offset - self.TEXT_PADDING
        )
        
        if self.snippet_data.type == "image" and self._pixmap and not self._pixmap.isNull():
            # Draw image
            scaled = self._pixmap.scaledToWidth(
                int(content_rect.width()),
                Qt.TransformationMode.SmoothTransformation
            )
            if scaled.height() > self.IMAGE_MAX_HEIGHT:
                scaled = scaled.scaledToHeight(
                    self.IMAGE_MAX_HEIGHT,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            # Center the image horizontally
            x_pos = int(content_rect.x() + (content_rect.width() - scaled.width()) / 2)
            painter.drawPixmap(x_pos, int(content_rect.y()), scaled)
        else:
            # Draw text
            text_font = ModernTheme.get_ui_font(9)
            painter.setFont(text_font)
            painter.setPen(QColor(ModernTheme.TEXT_PRIMARY))
            text = self.snippet_data.content or "(Empty - double-click to edit)"
            painter.drawText(
                content_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                text
            )
        
        # Selection highlight
        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(Colors.SELECTION, 2))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle double-click for editing."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on source label area
            if self.snippet_data.source_label:
                label_rect = QRectF(
                    self.TEXT_PADDING, self.TEXT_PADDING,
                    self.width - 2 * self.TEXT_PADDING,
                    self.SOURCE_LABEL_HEIGHT
                )
                if label_rect.contains(event.pos()):
                    self._edit_source_label()
                    return
            
            # Edit text content
            if self.snippet_data.type == "text":
                self._edit_text_content()
            elif self.snippet_data.type == "image" and self._pixmap:
                 from widgets import ImageViewerDialog
                 views = self.scene().views()
                 if views:
                     dlg = ImageViewerDialog(self._pixmap, views[0])
                     dlg.exec()
        
        super().mouseDoubleClickEvent(event)
    
    def _edit_source_label(self) -> None:
        """Show dialog to edit source label (emit request for undo)."""
        current = self.snippet_data.source_label or ""
        text, ok = QInputDialog.getText(
            None, "Edit Source Label",
            "Source Label:",
            QLineEdit.EchoMode.Normal,
            current
        )
        if ok and text != current:
            # Emit edit request signal
            self.parent_node.signals.snippet_edit_requested.emit(
                self.parent_node.node_data.id,
                self.snippet_data.id,
                "source_label",
                current,
                text
            )
    
    def _edit_text_content(self) -> None:
        """Show dialog to edit text content with word wrap (emit request for undo)."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
        
        old_content = self.snippet_data.content
        
        dialog = QDialog()
        dialog.setWindowTitle("Edit Snippet")
        dialog.setMinimumSize(400, 300)
        dialog.resize(500, 350)
        
        layout = QVBoxLayout(dialog)
        
        # Text edit with word wrap
        text_edit = QTextEdit()
        text_edit.setPlainText(old_content)
        text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        text_edit.setStyleSheet("""
            QTextEdit {
                font-family: 'Segoe UI', sans-serif;
                font-size: 11pt;
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        """)
        layout.addWidget(text_edit)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_content = text_edit.toPlainText()
            if new_content != old_content:
                # Emit edit request signal
                self.parent_node.signals.snippet_edit_requested.emit(
                    self.parent_node.node_data.id,
                    self.snippet_data.id,
                    "content",
                    old_content,
                    new_content
                )
    
    def get_height(self) -> float:
        """Get the current height of this snippet."""
        return self.rect().height()
    
    def refresh_image(self) -> None:
        """Reload the image if this is an image snippet."""
        if self.snippet_data.type == "image":
            self._load_image()
            self._update_geometry()
            self.update()
    
    def contextMenuEvent(self, event) -> None:
        """Show context menu for snippet operations."""
        menu = QMenu()
        
        # Move up action
        move_up_action = menu.addAction("↑ Move Up")
        move_up_action.triggered.connect(self._move_up)
        
        # Move down action
        move_down_action = menu.addAction("↓ Move Down")
        move_down_action.triggered.connect(self._move_down)
        
        menu.addSeparator()
        
        # Delete action
        delete_action = menu.addAction("🗑 Delete Snippet")
        delete_action.triggered.connect(self._delete_snippet)
        
        menu.exec(event.screenPos())
    
    def _move_up(self) -> None:
        """Move this snippet up in the list."""
        self.parent_node.move_snippet_up(self)
    
    def _move_down(self) -> None:
        """Move this snippet down in the list."""
        self.parent_node.move_snippet_down(self)
    
    def _delete_snippet(self) -> None:
        """Delete this snippet."""
        self.parent_node.remove_snippet(self)


# ============================================================================
# Tag Badge
# ============================================================================
class TagBadge(QGraphicsRectItem):
    """Small colored badge showing an assigned tag. Click to remove from node."""
    
    BADGE_HEIGHT = 16
    PADDING = 6
    DEFAULT_COLOR = "#607D8B"  # Same as DraggableTagItem
    
    def __init__(self, tag_name: str, parent: "BaseNodeItem", color: str = None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.parent_node = parent
        # Use provided color or default gray
        self._color = QColor(color) if color else QColor(self.DEFAULT_COLOR)
        self._is_hover = False
        
        # Make interactive
        self.setAcceptHoverEvents(True)
        
        # Calculate width based on text
        font = ModernTheme.get_ui_font(7, bold=True)
        metrics = QFontMetrics(font)
        width = metrics.horizontalAdvance(tag_name) + 2 * self.PADDING
        
        self.setRect(0, 0, width, self.BADGE_HEIGHT)
    
    def set_color(self, color: str) -> None:
        """Set a custom color for this badge."""
        self._color = QColor(color) if color else QColor(self.DEFAULT_COLOR)
        self.update()
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        rect = self.rect()
        
        # Draw rounded background
        color = self._color.lighter(110) if self._is_hover else self._color
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        
        # Draw text
        font = ModernTheme.get_ui_font(7, bold=True)
        painter.setFont(font)
        painter.setPen(QPen(Colors.TEXT_LIGHT))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.tag_name)
        
        # Draw X hint on hover
        if self._is_hover:
            painter.setPen(QPen(Colors.TEXT_LIGHT, 1))
            x_rect = QRectF(rect.right() - 12, rect.top() + 2, 10, 12)
            painter.drawText(x_rect, Qt.AlignmentFlag.AlignCenter, "×")
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Click to remove tag from this node."""
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self.parent_node, 'remove_tag'):
                self.parent_node.remove_tag(self.tag_name)
            event.accept()
            return
        super().mousePressEvent(event)



# ============================================================================
# Resize Handle Item
# ============================================================================
class ResizeHandleItem(QGraphicsItem):
    """Handle for resizing nodes."""
    
    def __init__(self, parent: "BaseNodeItem"):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._parent = parent
        self._start_pos = None
        self._start_width = 0
        
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, 12, 12)
        
    def paint(self, painter, option, widget=None):
        painter.setPen(Qt.PenStyle.NoPen)
        # Draw a little grip triangle
        color = QColor(ModernTheme.TEXT_SECONDARY)
        color.setAlpha(60)
        painter.setBrush(color)
        
        path = QPainterPath()
        # Bottom-right corner triangle
        path.moveTo(10, 10)
        path.lineTo(10, 2)
        path.lineTo(2, 10)
        path.closeSubpath()
        painter.drawPath(path)
        
    def mousePressEvent(self, event):
        self._start_pos = event.screenPos()
        self._start_width = self._parent.node_width
        event.accept()
        
    def mouseMoveEvent(self, event):
        delta = event.screenPos().x() - self._start_pos.x()
        new_width = max(200, self._start_width + delta)
        self._parent.resize_node(new_width)
        event.accept()


# ============================================================================
# Base Node Item
# ============================================================================
class BaseNodeItem(QGraphicsRectItem):
    """
    Abstract base class for all nodes (pipeline modules and references).
    Handles common functionality: selection, movement, tags, snippets.
    """
    
    NODE_WIDTH = 200
    HEADER_HEIGHT = 50
    SNIPPET_SPACING = 5
    TAG_SPACING = 4
    
    def __init__(self, node_data: NodeData):
        super().__init__()
        self.node_data = node_data
        self.node_width = self.NODE_WIDTH
        self.signals = NodeSignals()
        
        self._snippet_items: list[SnippetItem] = []
        self._tag_badges: list[TagBadge] = []
        
        # Add resize handle
        self._resize_handle = ResizeHandleItem(self)
        self._resize_handle.setZValue(100)
        
        self._is_hover = False
        self._drag_start_pos: Optional[QPointF] = None
        self._is_connection_source = False
        self._group_color = None
        self._being_moved_by_group = False  # V3.9.0: Skip snap when moved by group
        
        # Setup flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setAcceptDrops(True)
        
        # Set initial position
        self.setPos(node_data.position.x, node_data.position.y)
        
        # Create snippet items
        self._rebuild_snippets()
        self._rebuild_tags()
        self._update_rect()
    
    def set_group_color(self, color: Optional[str]) -> None:
        """Set the visual group color indicator."""
        self._group_color = QColor(color) if color else None
        self.update()

    def _get_header_color(self) -> QColor:
        """Override in subclasses to provide header color."""
        return Colors.HEADER_BG
    
    def _get_header_text(self) -> str:
        """Override in subclasses to provide header text."""
        return "Node"
    
    def _get_body_color(self) -> QColor:
        """Override in subclasses to provide body background color."""
        return QColor("#FAFAFA")
    
    def _rebuild_snippets(self) -> None:
        """Recreate snippet items from node data."""
        # Remove existing
        for item in self._snippet_items:
            if item.scene():
                item.scene().removeItem(item)
        self._snippet_items.clear()
        
        # Create new
        for snippet in self.node_data.snippets:
            item = SnippetItem(snippet, self)
            self._snippet_items.append(item)
        
        self.update_layout()
    
    def _rebuild_tags(self) -> None:
        """Recreate tag badges from node data."""
        for badge in self._tag_badges:
            if badge.scene():
                badge.scene().removeItem(badge)
        self._tag_badges.clear()
        
        for tag in self.node_data.tags:
            color = self._get_tag_color(tag)
            badge = TagBadge(tag, self, color)
            self._tag_badges.append(badge)
        
        self._layout_tags()
    
    def _get_tag_color(self, tag_name: str) -> Optional[str]:
        """Get tag color from the main window's global tags."""
        scene = self.scene()
        if scene:
            # Try to get main window from scene's views
            views = scene.views()
            if views:
                main_window = views[0].parent()
                if main_window and hasattr(main_window, 'project_dock'):
                    tags = main_window.project_dock.get_tags()
                    for t in tags:
                        if t.get('name') == tag_name:
                            return t.get('color')
        return None
    
    def _layout_tags(self) -> None:
        """Position tag badges horizontally below header."""
        x = 5
        y = self.HEADER_HEIGHT + 3
        for badge in self._tag_badges:
            badge.setPos(x, y)
            x += badge.rect().width() + self.TAG_SPACING
    
    def resize_node(self, width: float) -> None:
        self.node_width = width
        self.update_layout()
        
    def update_layout(self) -> None:
        """Update positions of all child items and recalculate size."""
        # Resize snippets to match node width (20px padding)
        snippet_width = int(self.node_width - 20)
        
        # Position snippets vertically
        y = self.HEADER_HEIGHT + 25  # Space for tags
        if self._tag_badges:
            y += 20  # Extra space if tags exist
        
        x = 10
        
        for snippet_item in self._snippet_items:
            snippet_item.set_width(snippet_width)
            snippet_item.setPos(x, y)
            y += snippet_item.get_height() + self.SNIPPET_SPACING
        
        self._update_rect()
    
    def _update_rect(self) -> None:
        """Update the bounding rectangle to encompass all content."""
        height = self.HEADER_HEIGHT + 25  # Base + tag space
        
        if self._tag_badges:
            height += 20
        
        for snippet_item in self._snippet_items:
            height += snippet_item.get_height() + self.SNIPPET_SPACING
        
        height = max(height, self.HEADER_HEIGHT + 30)  # Minimum height
        height += 10  # Bottom padding
        
        self.setRect(0, 0, self.node_width, height)
        # Update transform origin for scaling
        self.setTransformOriginPoint(self.node_width / 2, height / 2)
        
        # Position Handle
        if hasattr(self, '_resize_handle'):
            self._resize_handle.setPos(self.node_width - 12, height - 12)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        rect = self.rect()
        
        # Anti-aliasing
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        # Shadow (Simple subtle drop shadow)
        if not self.isSelected():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 10)) # Very subtle shadow
            painter.drawRoundedRect(rect.translated(0, 2), 12, 12)
            painter.setBrush(QColor(0, 0, 0, 5))  # Softer outer shadow
            painter.drawRoundedRect(rect.translated(0, 4), 12, 12)
        
        # Main Card Background
        bg_color = QColor(ModernTheme.BG_PRIMARY)
        painter.setBrush(bg_color)
        
        # Border
        if self.isSelected():
            # Glow effect for selection
            pen = QPen(QColor(ModernTheme.ACCENT_COLOR), 2)
        elif self._group_color:
            pen = QPen(self._group_color, 2)
        else:
            pen = QPen(QColor(ModernTheme.BORDER_LIGHT), 1)
            
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 12, 12)
        
        # Header Accent Strip (Top)
        # We use a path to ensure the top corners are clipped correctly
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.setClipPath(path)
        
        # Get color based on node type logic
        accent_color = QColor(self._get_header_color())
        # Make accent purely a strip
        painter.fillRect(QRectF(rect.x(), rect.y(), rect.width(), 6), accent_color)
        
        painter.setClipping(False)
        
        # Header Text
        # Use primary font, bold
        font = ModernTheme.get_ui_font(10, bold=True)
             
        painter.setFont(font)
        painter.setPen(QColor(ModernTheme.TEXT_PRIMARY))
        
        # Position text below the accent strip
        text_rect = QRectF(16, 16, rect.width() - 32, 24)
        
        # Draw Title
        title_text = self._get_header_text()
        metrics = QFontMetrics(font)
        elided_text = metrics.elidedText(title_text, Qt.TextElideMode.ElideRight, int(text_rect.width()))
        
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text
        )
        
        # Draw connection highlighting
        if self._is_connection_source:
            painter.setPen(QPen(QColor(ModernTheme.ACCENT_COLOR), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-4, -4, 4, 4), 14, 14)
    
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # V3.9.0: Block movement if node is locked
            if self.node_data.is_locked:
                return self.pos()  # Keep current position
            
            # V3.9.0: Block movement if node is in a locked group
            scene = self.scene()
            if scene and hasattr(scene, '_groups'):
                for group in scene._groups.values():
                    if self.node_data.id in group.group_data.node_ids:
                        if group.group_data.is_locked:
                            return self.pos()  # Keep current position
            
            # Snap to grid when Shift is held, but NOT when being moved by group
            if not self._being_moved_by_group:
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtCore import Qt
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    grid_size = 20
                    new_pos = value
                    snapped_x = round(new_pos.x() / grid_size) * grid_size
                    snapped_y = round(new_pos.y() / grid_size) * grid_size
                    return QPointF(snapped_x, snapped_y)
        
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update node data
            pos = self.pos()
            self.node_data.position.x = pos.x()
            self.node_data.position.y = pos.y()
            self.signals.position_changed.emit(self.node_data.id, pos.x(), pos.y())
        return super().itemChange(change, value)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.setZValue(10)
        self.setScale(1.02)
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.setZValue(0)
        self.setScale(1.0)
        self.update()
        super().hoverLeaveEvent(event)
    
    _drag_start_pos = QPointF(0, 0)
    
    # Enable usage of mousePressEvent
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Capture drag start position."""
        self._drag_start_pos = self.pos()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        
        # If we were dragging to connect, connection is handled by view
        if hasattr(self, '_is_dragging_to_connect') and self._is_dragging_to_connect:
            return
            
        # Emit drag finished for grouping logic
        self.signals.drag_finished.emit(self.node_data.id, event.modifiers())
    
    def contextMenuEvent(self, event):
        """Show context menu on right-click."""
        # Check if the scene wants to suppress context menu (after connection)
        scene = self.scene()
        if scene and hasattr(scene, '_suppress_context_menu') and scene._suppress_context_menu:
            scene._suppress_context_menu = False  # Reset the flag
            event.accept()  # Consume the event
            return
        
        menu = QMenu()
        
        add_text_action = menu.addAction("Add Text Snippet")
        add_text_action.triggered.connect(self._add_text_snippet)
        
        menu.addSeparator()
        
        # V3.9.0: Lock/Unlock action
        lock_text = "🔓 Unlock Node" if self.node_data.is_locked else "🔒 Lock Node"
        lock_action = menu.addAction(lock_text)
        lock_action.triggered.connect(self._toggle_lock)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete Node")
        delete_action.triggered.connect(self._request_delete)
        
        menu.exec(event.screenPos())
    
    _is_undo_operation = False  # V3.9.0: Flag for undo/redo bypass
    
    def _add_text_snippet(self) -> None:
        """Add a new empty text snippet (emit request for undo)."""
        from models import Snippet
        snippet = Snippet(type="text", content="")
        # Emit request signal with serialized data
        self.signals.snippet_add_requested.emit(self.node_data.id, snippet.to_dict())
    
    def add_snippet_internal(self, snippet_data: dict) -> None:
        """Internal: Actually add snippet (called by command)."""
        from models import Snippet
        snippet = Snippet.from_dict(snippet_data)
        self.node_data.snippets.append(snippet)
        
        item = SnippetItem(snippet, self)
        self._snippet_items.append(item)
        
        self.update_layout()
        self.signals.data_changed.emit(self.node_data.id)
    
    def remove_snippet_internal(self, snippet_id: str) -> None:
        """Internal: Remove snippet by ID (for undo support)."""
        # Find and remove from data
        for i, snippet in enumerate(self.node_data.snippets):
            if snippet.id == snippet_id:
                self.node_data.snippets.pop(i)
                break
        
        # Find and remove from items
        for item in self._snippet_items:
            if item.snippet_data.id == snippet_id:
                if item.scene():
                    item.scene().removeItem(item)
                self._snippet_items.remove(item)
                break
        
        self.update_layout()
        self.signals.data_changed.emit(self.node_data.id)
    
    def _toggle_lock(self) -> None:
        """Toggle the lock state of this node."""
        self.node_data.is_locked = not self.node_data.is_locked
        self.update()
        self.signals.data_changed.emit(self.node_data.id)
    
    def add_image_snippet(self, relative_path: str) -> None:
        """Add an image snippet with the given path (emit request for undo)."""
        from models import Snippet
        snippet = Snippet(type="image", content=relative_path)
        # Emit request signal
        self.signals.snippet_add_requested.emit(self.node_data.id, snippet.to_dict())
    
    def add_cloned_snippets(self, source_snippets: list[Snippet], source_title: str) -> list[str]:
        """Add deep-copied snippets from another node.
        Returns list of cloned snippet IDs (for undo support).
        """
        cloned_ids = []
        for snippet in source_snippets:
            cloned = snippet.deep_copy(source_title)
            cloned_ids.append(cloned.id)
            self.node_data.snippets.append(cloned)
            
            item = SnippetItem(cloned, self)
            self._snippet_items.append(item)
        
        self.update_layout()
        self.signals.data_changed.emit(self.node_data.id)
        return cloned_ids
    
    def add_tag(self, tag_name: str) -> None:
        """Assign a tag to this node (emit request for undo)."""
        if tag_name not in self.node_data.tags:
            # Emit toggle request for undo
            self.signals.tag_toggle_requested.emit(self.node_data.id, tag_name, True)
    
    def add_tag_internal(self, tag_name: str) -> None:
        """Internal: Actually add tag (called by command)."""
        if tag_name not in self.node_data.tags:
            self.node_data.tags.append(tag_name)
            color = self._get_tag_color(tag_name)
            badge = TagBadge(tag_name, self, color)
            self._tag_badges.append(badge)
            self._layout_tags()
            self.update_layout()
            self.signals.data_changed.emit(self.node_data.id)
    
    def remove_tag(self, tag_name: str) -> None:
        """Remove a tag from this node (emit request for undo)."""
        if tag_name in self.node_data.tags:
            # Emit toggle request for undo
            self.signals.tag_toggle_requested.emit(self.node_data.id, tag_name, False)
    
    def remove_tag_internal(self, tag_name: str) -> None:
        """Internal: Actually remove tag (called by command)."""
        if tag_name in self.node_data.tags:
            self.node_data.tags.remove(tag_name)
            self._rebuild_tags()
            self.update_layout()
            self.signals.data_changed.emit(self.node_data.id)
    
    def _request_delete(self) -> None:
        """Request deletion of this node and its connected edges."""
        scene = self.scene()
        if scene and hasattr(scene, 'remove_node'):
            scene.remove_node(self.node_data.id)
    
    def get_connection_point(self) -> QPointF:
        """Get the center point for connections."""
        return self.sceneBoundingRect().center()
    
    def get_snippets_data(self) -> list[Snippet]:
        """Get the snippet data for deep copy operations."""
        return self.node_data.snippets.copy()
    
    def get_title(self) -> str:
        """Get the node title for attribution."""
        return self._get_header_text()
    
    def set_connection_source(self, is_source: bool) -> None:
        """Visual indicator that this node is being dragged for connection."""
        self._is_connection_source = is_source
        self.update()
    
    def remove_snippet(self, snippet_item: "SnippetItem") -> None:
        """Remove a snippet from this node (emit request for undo)."""
        if snippet_item in self._snippet_items:
            idx = self._snippet_items.index(snippet_item)
            snippet_data = snippet_item.snippet_data.to_dict()
            self.signals.snippet_remove_requested.emit(self.node_data.id, snippet_data, idx)
    
    def remove_snippet_internal(self, snippet_id: str) -> None:
        """Internal: Actually remove snippet by ID (called by command)."""
        for i, snip in enumerate(self.node_data.snippets):
            if snip.id == snippet_id:
                self.node_data.snippets.pop(i)
                break
        
        for i, item in enumerate(self._snippet_items):
            if item.snippet_data.id == snippet_id:
                if item.scene():
                    item.scene().removeItem(item)
                self._snippet_items.pop(i)
                break
        
        self.update_layout()
        self.signals.data_changed.emit(self.node_data.id)
    
    def move_snippet_up(self, snippet_item: "SnippetItem") -> None:
        """Move a snippet up in the list (emit request for undo)."""
        if snippet_item in self._snippet_items:
            idx = self._snippet_items.index(snippet_item)
            if idx > 0:
                self.signals.snippet_move_requested.emit(
                    self.node_data.id, snippet_item.snippet_data.id, idx, idx - 1)
    
    def move_snippet_down(self, snippet_item: "SnippetItem") -> None:
        """Move a snippet down in the list (emit request for undo)."""
        if snippet_item in self._snippet_items:
            idx = self._snippet_items.index(snippet_item)
            if idx < len(self._snippet_items) - 1:
                self.signals.snippet_move_requested.emit(
                    self.node_data.id, snippet_item.snippet_data.id, idx, idx + 1)
    
    def move_snippet_internal(self, from_idx: int, to_idx: int) -> None:
        """Internal: Actually move snippet (called by command)."""
        if 0 <= from_idx < len(self.node_data.snippets):
            # Move in data list
            snippet = self.node_data.snippets.pop(from_idx)
            self.node_data.snippets.insert(to_idx, snippet)
            
            # Move in item list
            if 0 <= from_idx < len(self._snippet_items):
                item = self._snippet_items.pop(from_idx)
                self._snippet_items.insert(to_idx, item)
            
            self.update_layout()
            self.signals.data_changed.emit(self.node_data.id)


# ============================================================================
# Flag Button (V3.9.0)
# ============================================================================
class FlagButton(QGraphicsRectItem):
    """Small clickable flag icon for marking important nodes."""
    
    SIZE = 20
    
    def __init__(self, parent: "PipelineModuleItem"):
        super().__init__(parent)
        self.parent_node = parent
        self.setRect(0, 0, self.SIZE, self.SIZE)
        self.setAcceptHoverEvents(True)
        self._is_hover = False
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        rect = self.rect()
        is_flagged = self.parent_node.node_data.is_flagged
        
        # Background on hover
        if self._is_hover:
            painter.setBrush(QBrush(QColor(0, 0, 0, 20)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 4, 4)
        
        # Draw flag icon
        flag_color = QColor("#E53935") if is_flagged else QColor("#9E9E9E")
        painter.setPen(QPen(flag_color, 1.5))
        painter.setBrush(QBrush(flag_color) if is_flagged else Qt.BrushStyle.NoBrush)
        
        # Flag pole
        cx = rect.center().x()
        top = rect.top() + 4
        bottom = rect.bottom() - 4
        painter.drawLine(QPointF(cx - 4, top), QPointF(cx - 4, bottom))
        
        # Flag triangle
        flag_path = QPainterPath()
        flag_path.moveTo(cx - 4, top)
        flag_path.lineTo(cx + 6, top + 5)
        flag_path.lineTo(cx - 4, top + 10)
        flag_path.closeSubpath()
        painter.drawPath(flag_path)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update()
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Toggle flag state
            self.parent_node.node_data.is_flagged = not self.parent_node.node_data.is_flagged
            self.parent_node.update()  # Trigger repaint for gradient
            self.update()
            self.parent_node.signals.data_changed.emit(self.parent_node.node_data.id)
            event.accept()
            return
        super().mousePressEvent(event)


# ============================================================================
# Pipeline Module Item
# ============================================================================
class PipelineModuleItem(BaseNodeItem):
    """
    A pipeline module node (flowchart shape).
    Types: input, output, process, decision
    """
    
    DEFAULT_COLORS = {
        "input": Colors.PIPELINE_INPUT,
        "output": Colors.PIPELINE_OUTPUT,
        "process": Colors.PIPELINE_PROCESS,
        "decision": Colors.PIPELINE_DECISION,
    }
    
    def __init__(self, node_data: NodeData):
        super().__init__(node_data)
        module_type = node_data.metadata.module_type or "process"
        self._header_color = self.DEFAULT_COLORS.get(module_type, Colors.PIPELINE_PROCESS)
        
        # V3.9.0: Add flag button
        self._flag_button = FlagButton(self)
        self._position_flag_button()
    
    @property
    def module_type(self) -> str:
        """Get the module type."""
        return self.node_data.metadata.module_type or "process"
    
    def set_color(self, color: str) -> None:
        """Set the header color for this module."""
        self._header_color = QColor(color)
        self.update()
    
    def _get_header_color(self) -> QColor:
        return self._header_color
    
    def _get_header_text(self) -> str:
        name = self.node_data.metadata.module_name or "Module"
        type_label = self.node_data.metadata.module_type.capitalize() if self.node_data.metadata.module_type else ""
        if type_label:
            return f"{name} [{type_label}]"
        return name
    
    def _position_flag_button(self) -> None:
        """Position the flag button in the header area."""
        self._flag_button.setPos(self.node_width - FlagButton.SIZE - 8, 10)
    
    def _update_rect(self) -> None:
        """Override to reposition flag button when rect changes."""
        super()._update_rect()
        if hasattr(self, '_flag_button'):
            self._position_flag_button()
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        # Call parent paint first
        super().paint(painter, option, widget)
        
        # V3.9.0: Draw red gradient at bottom when flagged
        if self.node_data.is_flagged:
            rect = self.rect()
            gradient_height = 30
            gradient_rect = QRectF(
                rect.x(), rect.bottom() - gradient_height,
                rect.width(), gradient_height
            )
            
            # Create gradient from transparent to semi-transparent red
            from PyQt6.QtGui import QLinearGradient
            gradient = QLinearGradient(
                gradient_rect.topLeft(),
                gradient_rect.bottomLeft()
            )
            gradient.setColorAt(0.0, QColor(229, 57, 53, 0))    # Transparent
            gradient.setColorAt(1.0, QColor(229, 57, 53, 60))   # Semi-transparent red
            
            # Clip to rounded rect
            path = QPainterPath()
            path.addRoundedRect(rect, 12, 12)
            painter.setClipPath(path)
            painter.fillRect(gradient_rect, gradient)
            painter.setClipping(False)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Edit module name on double-click header (emit request for undo)."""
        if event.pos().y() < self.HEADER_HEIGHT:
            old_name = self.node_data.metadata.module_name
            text, ok = QInputDialog.getText(
                None, "Edit Module Name",
                "Module Name:",
                QLineEdit.EchoMode.Normal,
                old_name
            )
            if ok and text and text != old_name:
                # Emit edit request signal for undo
                self.signals.metadata_edit_requested.emit(
                    self.node_data.id, "module_name", old_name, text)
        else:
            super().mouseDoubleClickEvent(event)


# ============================================================================
# Waypoint Item (V3.9.0) - Connection Bending Point
# ============================================================================
class WaypointItem(QGraphicsEllipseItem):
    """
    A small waypoint node for creating connection bends.
    Features:
    - Circular shape, smaller when connected
    - Inherits color from incoming edge
    - Supports snap to grid and group binding
    - Single in, single out connections
    """
    
    SIZE_UNCONNECTED = 16
    SIZE_CONNECTED = 10
    DEFAULT_COLOR = "#607D8B"
    
    def __init__(self, node_data: NodeData = None, parent=None, initial_color: str = None):
        super().__init__(parent)
        from models import NodeData, Position, generate_uuid
        
        if node_data is None:
            node_data = NodeData(
                id=generate_uuid(),
                type="waypoint",
                position=Position(0, 0)
            )
        
        self.node_data = node_data
        self.signals = NodeSignals()
        
        self._color = QColor(initial_color if initial_color else self.DEFAULT_COLOR)
        self._is_hover = False
        self._has_incoming = False
        self._group_color = None
        self._being_moved_by_group = False
        self._is_connection_source = False
        self._is_reference_type = False  # Track if waypoint is carrying reference signal
        
        # Set initial size
        size = self.SIZE_UNCONNECTED
        self.setRect(-size/2, -size/2, size, size)
        self.setPos(node_data.position.x, node_data.position.y)
        
        # Setup flags
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(5)  # Above edges but below nodes
    
    def set_color(self, color: str) -> None:
        """Set the waypoint color directly."""
        self._color = QColor(color)
        self.update()
        
    def set_reference_type(self, is_reference: bool, pipeline_color: str, reference_color: str) -> bool:
        """Set whether waypoint carries reference signal. Returns True if changed."""
        if self._is_reference_type == is_reference:
            return False
            
        self._is_reference_type = is_reference
        self.set_color(reference_color if is_reference else pipeline_color)
        return True
    
    def set_has_incoming(self, has_incoming: bool) -> None:
        """Update size based on whether there's an incoming connection."""
        self._has_incoming = has_incoming
        size = self.SIZE_CONNECTED if has_incoming else self.SIZE_UNCONNECTED
        self.prepareGeometryChange()
        self.setRect(-size/2, -size/2, size, size)
        self.update()
    
    def set_group_color(self, color: Optional[str]) -> None:
        """Set group color indicator."""
        self._group_color = QColor(color) if color else None
        self.update()
    
    def set_connection_source(self, is_source: bool) -> None:
        """Set whether this waypoint is the source of a connection being drawn."""
        self._is_connection_source = is_source
        self.update()
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        # Fill color
        painter.setBrush(QBrush(self._color))
        
        # Border
        if self._is_connection_source:
            painter.setPen(QPen(QColor(ModernTheme.ACCENT_COLOR), 2, Qt.PenStyle.DashLine))
        elif self.isSelected():
            painter.setPen(QPen(QColor(ModernTheme.ACCENT_COLOR), 2))
        elif self._group_color:
            painter.setPen(QPen(self._group_color, 2))
        elif self._is_hover:
            painter.setPen(QPen(self._color.darker(120), 2))
        else:
            painter.setPen(QPen(self._color.darker(110), 1))
        
        painter.drawEllipse(rect)
    
    def boundingRect(self) -> QRectF:
        return self.rect().adjusted(-3, -3, 3, 3)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def itemChange(self, change: QGraphicsEllipseItem.GraphicsItemChange, value):
        if change == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionChange:
            # V3.9.0: Block movement if locked
            if self.node_data.is_locked:
                return self.pos()
            
            # Check group lock
            scene = self.scene()
            if scene and hasattr(scene, '_groups'):
                for group in scene._groups.values():
                    if self.node_data.id in group.group_data.node_ids:
                        if group.group_data.is_locked:
                            return self.pos()
            
            # Snap to grid when Shift is held
            if not self._being_moved_by_group:
                from PyQt6.QtWidgets import QApplication
                from PyQt6.QtCore import Qt
                modifiers = QApplication.keyboardModifiers()
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    grid_size = 20
                    new_pos = value
                    snapped_x = round(new_pos.x() / grid_size) * grid_size
                    snapped_y = round(new_pos.y() / grid_size) * grid_size
                    return QPointF(snapped_x, snapped_y)
        
        if change == QGraphicsEllipseItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            self.node_data.position.x = pos.x()
            self.node_data.position.y = pos.y()
            self.signals.position_changed.emit(self.node_data.id, pos.x(), pos.y())
        
        return super().itemChange(change, value)
    
    _drag_start_pos = None  # For undo/redo movement tracking
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Capture drag start position."""
        from PyQt6.QtCore import QPointF
        self._drag_start_pos = QPointF(self.pos())
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            self.signals.drag_finished.emit(self.node_data.id, modifiers)
    
    def contextMenuEvent(self, event) -> None:
        """Show context menu."""
        # Check if context menu should be suppressed (after connection)
        scene = self.scene()
        if scene and hasattr(scene, '_suppress_context_menu') and scene._suppress_context_menu:
            scene._suppress_context_menu = False
            event.accept()
            return
        
        menu = QMenu()
        
        # Lock/Unlock
        lock_text = "🔓 Unlock" if self.node_data.is_locked else "🔒 Lock"
        lock_action = menu.addAction(lock_text)
        lock_action.triggered.connect(self._toggle_lock)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete Waypoint")
        delete_action.triggered.connect(self._request_delete)
        
        menu.exec(event.screenPos())
    
    def _toggle_lock(self) -> None:
        self.node_data.is_locked = not self.node_data.is_locked
        self.update()
        self.signals.data_changed.emit(self.node_data.id)
    
    def _request_delete(self) -> None:
        scene = self.scene()
        if scene and hasattr(scene, 'remove_waypoint'):
            scene.remove_waypoint(self.node_data.id)


# ============================================================================
# Expand Button
# ============================================================================
class ExpandButton(QGraphicsRectItem):
    """Small button to expand reference node content."""
    
    SIZE = 24
    
    def __init__(self, parent: "ReferenceNodeItem"):
        super().__init__(parent)
        self.parent_ref = parent
        self.setRect(0, 0, self.SIZE, self.SIZE)
        self.setAcceptHoverEvents(True)
        self._is_hover = False
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        rect = self.rect()
        
        # Background
        bg_color = Colors.SELECTION if self._is_hover else Colors.HEADER_BG.lighter(130)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 4, 4)
        
        # Draw expand icon (arrow)
        painter.setPen(QPen(Colors.TEXT_LIGHT, 2))
        center = rect.center()
        size = 6
        painter.drawLine(
            QPointF(center.x() - size, center.y()),
            QPointF(center.x() + size, center.y())
        )
        painter.drawLine(
            QPointF(center.x() + size - 3, center.y() - 3),
            QPointF(center.x() + size, center.y())
        )
        painter.drawLine(
            QPointF(center.x() + size - 3, center.y() + 3),
            QPointF(center.x() + size, center.y())
        )
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update()
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_ref.signals.expand_requested.emit(self.parent_ref.node_data.id)
        super().mousePressEvent(event)


# ============================================================================
# Reference Node Item
# ============================================================================
class ReferenceNodeItem(BaseNodeItem):
    """
    A reference paper node.
    Shows: Title, Year, Conference, Expand button, Snippets
    """
    
    HEADER_HEIGHT = 70  # Taller to fit more info
    
    def __init__(self, node_data: NodeData):
        super().__init__(node_data)
        
        # Add expand button
        self._expand_button = ExpandButton(self)
        self._position_expand_button()
    
    def _position_expand_button(self) -> None:
        """Position the expand button in the header."""
        x = self.NODE_WIDTH - ExpandButton.SIZE - 8
        y = (self.HEADER_HEIGHT - ExpandButton.SIZE) / 2
        self._expand_button.setPos(x, y)
    
    def _get_header_color(self) -> QColor:
        return Colors.REFERENCE
    
    def _get_header_text(self) -> str:
        return self.node_data.metadata.title or "Untitled Paper"
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        rect = self.rect()
        
        # Draw body background
        body_rect = QRectF(0, self.HEADER_HEIGHT, rect.width(), rect.height() - self.HEADER_HEIGHT)
        painter.setBrush(QBrush(self._get_body_color()))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(body_rect, 0, 0)
        painter.drawRect(QRectF(0, self.HEADER_HEIGHT, rect.width(), 10))
        
        # Draw header
        header_rect = QRectF(0, 0, rect.width(), self.HEADER_HEIGHT)
        painter.setBrush(QBrush(self._get_header_color()))
        painter.drawRoundedRect(header_rect, 8, 8)
        painter.drawRect(QRectF(0, self.HEADER_HEIGHT - 10, rect.width(), 10))
        
        # Draw title
        title_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(title_font)
        painter.setPen(QPen(Colors.TEXT_LIGHT))
        title_rect = QRectF(10, 5, rect.width() - 50, 25)
        title = self.node_data.metadata.title or "Untitled Paper"
        # Elide long titles
        metrics = QFontMetrics(title_font)
        elided = metrics.elidedText(title, Qt.TextElideMode.ElideRight, int(title_rect.width()))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
        
        # Draw year and conference
        info_font = QFont("Segoe UI", 8)
        painter.setFont(info_font)
        painter.setPen(QPen(Colors.TEXT_LIGHT.darker(110)))
        
        info_parts = []
        if self.node_data.metadata.year:
            info_parts.append(self.node_data.metadata.year)
        if self.node_data.metadata.conference:
            info_parts.append(self.node_data.metadata.conference)
        info_text = " | ".join(info_parts) if info_parts else "(No metadata)"
        
        info_rect = QRectF(10, 30, rect.width() - 50, 20)
        painter.drawText(info_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, info_text)
        
        # Draw hint for snippets area
        if not self._snippet_items:
            hint_font = QFont("Segoe UI", 8, QFont.Weight.Normal)
            painter.setFont(hint_font)
            painter.setPen(QPen(QColor("#9E9E9E")))
            hint_rect = QRectF(10, self.HEADER_HEIGHT + 30, rect.width() - 20, 20)
            painter.drawText(
                hint_rect,
                Qt.AlignmentFlag.AlignCenter,
                "Paste text or Ctrl+V to add snippets"
            )
        
        # Draw border
        if self.isSelected():
            border_pen = QPen(Colors.SELECTION, 2)
        elif self._group_color:
            border_pen = QPen(self._group_color, 2)
        else:
            border_pen = QPen(Colors.BORDER, 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        
        # Draw connection indicator
        if self._is_connection_source:
            painter.setPen(QPen(Colors.CONNECTION_LINE, 3))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 10, 10)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Edit metadata on double-click header."""
        if event.pos().y() < self.HEADER_HEIGHT:
            # Determine which field to edit based on y position
            if event.pos().y() < 30:
                # Edit title
                old_title = self.node_data.metadata.title or ""
                text, ok = QInputDialog.getText(
                    None, "Edit Title",
                    "Paper Title:",
                    QLineEdit.EchoMode.Normal,
                    old_title
                )
                if ok and text and text != old_title:
                    self.signals.metadata_edit_requested.emit(
                        self.node_data.id, "title", old_title, text)
            else:
                # Edit year
                old_year = self.node_data.metadata.year or ""
                year, ok = QInputDialog.getText(
                    None, "Edit Year",
                    "Year:",
                    QLineEdit.EchoMode.Normal,
                    old_year
                )
                if ok and year != old_year:
                    self.signals.metadata_edit_requested.emit(
                        self.node_data.id, "year", old_year, year)
                
                # Edit conference
                old_conf = self.node_data.metadata.conference or ""
                conf, ok = QInputDialog.getText(
                    None, "Edit Conference",
                    "Conference/Journal:",
                    QLineEdit.EchoMode.Normal,
                    old_conf
                )
                if ok and conf != old_conf:
                    self.signals.metadata_edit_requested.emit(
                        self.node_data.id, "conference", old_conf, conf)
        else:
            super().mouseDoubleClickEvent(event)
    
    def get_title(self) -> str:
        """Get paper title for attribution."""
        return self.node_data.metadata.title or "Unknown Paper"


# ============================================================================
# Edge Item (Connection Arrow)
# ============================================================================
class EdgeItem(QGraphicsPathItem):
    """
    A connection arrow between two nodes or waypoints.
    Drawn as a curved bezier path with an arrowhead.
    Supports selection and deletion via context menu.
    Different colors for reference vs pipeline connections.
    """
    
    ARROW_SIZE = 10
    
    def __init__(self, source_node, target_node, edge_id: str = None,
                 pipeline_color: str = "#607D8B", reference_color: str = "#4CAF50"):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.edge_id = edge_id or generate_uuid()
        self._is_hover = False
        
        # Determine edge type and color
        # Reference edge if source is ReferenceNodeItem
        self._is_reference_edge = isinstance(source_node, ReferenceNodeItem)
        self._pipeline_color = QColor(pipeline_color)
        self._reference_color = QColor(reference_color)
        self._base_color = self._reference_color if self._is_reference_edge else self._pipeline_color
        
        # Make selectable and hoverable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        self.setPen(QPen(self._base_color, 2))
        self.setZValue(-1)  # Draw behind nodes
        
        self.update_path()
    
    def update_colors(self, pipeline_color: str, reference_color: str) -> None:
        """Update edge colors from settings."""
        self._pipeline_color = QColor(pipeline_color)
        self._reference_color = QColor(reference_color)
        self._base_color = self._reference_color if self._is_reference_edge else self._pipeline_color
        self.update()
    
    def _get_edge_point(self, rect: QRectF, center: QPointF, target: QPointF) -> QPointF:
        """Calculate the intersection point between a line from center to target and the rectangle edge."""
        dx = target.x() - center.x()
        dy = target.y() - center.y()
        
        if dx == 0 and dy == 0:
            return center
        
        # Calculate intersection with each edge
        # We need to find where the line from center to target crosses the rectangle
        
        # Try left/right edges
        if dx != 0:
            if dx > 0:  # Going right
                t = (rect.right() - center.x()) / dx
            else:  # Going left
                t = (rect.left() - center.x()) / dx
            
            y_at_t = center.y() + t * dy
            if rect.top() <= y_at_t <= rect.bottom() and t > 0:
                return QPointF(rect.right() if dx > 0 else rect.left(), y_at_t)
        
        # Try top/bottom edges
        if dy != 0:
            if dy > 0:  # Going down
                t = (rect.bottom() - center.y()) / dy
            else:  # Going up
                t = (rect.top() - center.y()) / dy
            
            x_at_t = center.x() + t * dx
            if rect.left() <= x_at_t <= rect.right() and t > 0:
                return QPointF(x_at_t, rect.bottom() if dy > 0 else rect.top())
        
        return center
    
    def update_path(self) -> None:
        """Recalculate the path based on node positions."""
        if not self.source_node or not self.target_node:
            return
        
        source_rect = self.source_node.sceneBoundingRect()
        target_rect = self.target_node.sceneBoundingRect()
        source_center = source_rect.center()
        target_center = target_rect.center()
        
        # For WaypointItem, connect directly to center
        if isinstance(self.source_node, WaypointItem):
            source_edge = source_center
        else:
            source_edge = self._get_edge_point(source_rect, source_center, target_center)
        
        if isinstance(self.target_node, WaypointItem):
            target_edge = target_center
        else:
            target_edge = self._get_edge_point(target_rect, target_center, source_center)
        
        # Calculate control points for bezier curve
        dx = target_edge.x() - source_edge.x()
        dy = target_edge.y() - source_edge.y()
        
        # Calculate Euclidean distance
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Calculate angle in degrees (0 = Right, 90 = Down)
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
            
        # Determine direction vector based on 45-degree quadrants
        if (angle >= 315) or (angle < 45):
            # Right
            dir_vec = QPointF(1, 0)
        elif 45 <= angle < 135:
            # Down
            dir_vec = QPointF(0, 1)
        elif 135 <= angle < 225:
            # Left
            dir_vec = QPointF(-1, 0)
        else: # 225 <= angle < 315
            # Up
            dir_vec = QPointF(0, -1)
            
        # Adjust control points based on direction
        # Use dynamic offset based on distance, capped at 100
        ctrl_offset = min(distance * 0.5, 100)
        
        ctrl1 = source_edge + dir_vec * ctrl_offset
        ctrl2 = target_edge - dir_vec * ctrl_offset
        
        # Create path
        path = QPainterPath()
        path.moveTo(source_edge)
        path.cubicTo(ctrl1, ctrl2, target_edge)
        
        self.setPath(path)
        
        # Store edge points for arrowhead
        self._source_edge = source_edge
        self._target_edge = target_edge
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        # Determine color based on state
        if self.isSelected():
            color = Colors.SELECTION
            width = 4
        elif self._is_hover:
            color = self._base_color.lighter(120)
            width = 3
        else:
            color = self._base_color
            width = 2
        
        # Draw the path
        painter.setPen(QPen(color, width))
        painter.drawPath(self.path())
        
        # Draw arrowhead at target edge
        if hasattr(self, '_target_edge') and hasattr(self, '_source_edge'):
            target_edge = self._target_edge
            source_edge = self._source_edge
            
            # Calculate angle from the path tangent at the end
            # Using pointAtPercent accounts for the actual curve direction
            path = self.path()
            if path.length() > 0:
                p_end = path.pointAtPercent(1.0)
                p_pre = path.pointAtPercent(0.95) # 5% back to get tangent
                angle = math.atan2(p_end.y() - p_pre.y(), p_end.x() - p_pre.x())
            else:
                # Fallback
                dx = target_edge.x() - source_edge.x()
                dy = target_edge.y() - source_edge.y()
                angle = math.atan2(dy, dx)
            
            # Arrowhead points
            arrow_p1 = QPointF(
                target_edge.x() - self.ARROW_SIZE * math.cos(angle - math.pi / 6),
                target_edge.y() - self.ARROW_SIZE * math.sin(angle - math.pi / 6)
            )
            arrow_p2 = QPointF(
                target_edge.x() - self.ARROW_SIZE * math.cos(angle + math.pi / 6),
                target_edge.y() - self.ARROW_SIZE * math.sin(angle + math.pi / 6)
            )
            
            # Draw arrowhead
            arrow = QPolygonF([target_edge, arrow_p1, arrow_p2])
            painter.setBrush(QBrush(color))
            painter.drawPolygon(arrow)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.update()
        super().hoverLeaveEvent(event)
    
    def contextMenuEvent(self, event) -> None:
        """Show context menu for edge deletion."""
        menu = QMenu()
        
        delete_action = menu.addAction("🗑 Delete Connection")
        delete_action.triggered.connect(self._delete_edge)
        
        menu.exec(event.screenPos())
    
    def _delete_edge(self) -> None:
        """Request deletion of this edge."""
        scene = self.scene()
        if scene and hasattr(scene, 'remove_edge'):
            scene.remove_edge(self.edge_id)


# ============================================================================
# Temporary Connection Line (for drag-connecting)
# ============================================================================
class TempConnectionLine(QGraphicsPathItem):
    """Temporary line shown while dragging to create a connection."""
    
    def __init__(self, start_pos: QPointF):
        super().__init__()
        self.start_pos = start_pos
        self.end_pos = start_pos
        
        pen = QPen(Colors.CONNECTION_LINE, 2, Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setZValue(100)  # Draw on top
        
        self.update_path()
    
    def update_end(self, end_pos: QPointF) -> None:
        """Update the end position."""
        self.end_pos = end_pos
        self.update_path()
    
    def update_path(self) -> None:
        """Recalculate the path."""
        path = QPainterPath()
        path.moveTo(self.start_pos)
        
        # Simple bezier curve
        dx = self.end_pos.x() - self.start_pos.x()
        ctrl1 = QPointF(self.start_pos.x() + dx * 0.5, self.start_pos.y())
        ctrl2 = QPointF(self.end_pos.x() - dx * 0.5, self.end_pos.y())
        
        path.cubicTo(ctrl1, ctrl2, self.end_pos)
        self.setPath(path)


# ============================================================================
# Group Item (V3.5.0)
# ============================================================================
class GroupSignals(QObject):
    """Signals emitted by group items."""
    position_changed = pyqtSignal(str, float, float)  # group_id, x, y
    moved = pyqtSignal(str, float, float)  # group_id, dx, dy (for relative movement)
    drag_finished = pyqtSignal(str, tuple, tuple)  # group_id, old_pos, new_pos (V3.9.0)
    color_changed = pyqtSignal(str, str)  # group_id, color
    size_changed = pyqtSignal(str, float, float)  # group_id, width, height
    name_changed = pyqtSignal(str, str)  # group_id, new_name
    node_added = pyqtSignal(str, str)  # group_id, node_id
    node_removed = pyqtSignal(str, str)  # group_id, node_id
    
    # V3.9.0: Group name edit request for undo
    name_edit_requested = pyqtSignal(str, str, str)  # group_id, old_name, new_name
    
    # V3.9.0: Group size change request for undo
    size_resize_requested = pyqtSignal(str, tuple, tuple)  # group_id, old_rect, new_rect


class GroupItem(QGraphicsRectItem):
    """
    A resizable group container that can hold multiple nodes.
    Features:
    - Dashed border with semi-transparent background
    - Resizable via corner handles
    - Contains node IDs and moves them together
    - Always rendered below nodes and edges
    """
    
    HANDLE_SIZE = 10
    MIN_SIZE = 100
    TITLE_HEIGHT = 24
    
    def __init__(self, group_data: "GroupData"):
        super().__init__()
        from models import GroupData  # Import here to avoid circular
        
        self.group_data = group_data
        self.signals = GroupSignals()
        self._color = QColor(group_data.color)
        self._is_resizing = False
        self._is_dragging = False  # Track interactive drag
        self._resize_handle = None  # 'tl', 'tr', 'bl', 'br'
        self._drag_start_pos = None
        self._drag_start_rect = None
        
        # Setup item properties
        self.setRect(0, 0, group_data.width, group_data.height)
        self.setPos(group_data.position.x, group_data.position.y)
        self.setZValue(-100)  # Always below nodes and edges
        
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        rect = self.rect()
        
        # Semi-transparent background
        bg_color = QColor(self._color)
        bg_color.setAlpha(30)
        painter.setBrush(QBrush(bg_color))
        
        # Dashed border
        border_color = QColor(self._color)
        border_color.setAlpha(180)
        pen = QPen(border_color, 2, Qt.PenStyle.DashLine)
        if self.isSelected():
            pen.setColor(Colors.SELECTION)
            pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        painter.drawRect(rect)
        
        # Draw title background
        title_rect = QRectF(rect.x(), rect.y(), rect.width(), self.TITLE_HEIGHT)
        title_bg = QColor(self._color)
        title_bg.setAlpha(60)
        painter.fillRect(title_rect, title_bg)
        
        # Draw title text
        painter.setPen(QPen(Colors.TEXT))
        font = ModernTheme.get_ui_font(9, bold=True)
        painter.setFont(font)
        text_rect = title_rect.adjusted(8, 0, -8, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, 
                        self.group_data.name)
        
        # Draw resize handles when selected
        if self.isSelected():
            painter.setBrush(QBrush(Colors.SELECTION))
            painter.setPen(Qt.PenStyle.NoPen)
            for handle_rect in self._get_handle_rects().values():
                painter.drawRect(handle_rect)
    
    def _get_handle_rects(self) -> dict:
        """Get resize handle rectangles."""
        rect = self.rect()
        hs = self.HANDLE_SIZE
        return {
            'tl': QRectF(rect.left() - hs/2, rect.top() - hs/2, hs, hs),
            'tr': QRectF(rect.right() - hs/2, rect.top() - hs/2, hs, hs),
            'bl': QRectF(rect.left() - hs/2, rect.bottom() - hs/2, hs, hs),
            'br': QRectF(rect.right() - hs/2, rect.bottom() - hs/2, hs, hs),
        }
    
    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        """Check if position is over a resize handle."""
        for name, rect in self._get_handle_rects().items():
            if rect.contains(pos):
                return name
        return None
    
    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        handle = self._get_handle_at(event.pos())
        if handle and self.isSelected():
            if handle in ('tl', 'br'):
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverMoveEvent(event)
    
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._get_handle_at(event.pos())
            if handle and self.isSelected():
                self._is_resizing = True
                self._resize_handle = handle
                self._drag_start_pos = event.scenePos()
                self._drag_start_rect = self.rect()
                # V3.9.0: Capture initial state for undo
                self._resize_start_state = (
                    self.pos().x() + self.rect().x(),
                    self.pos().y() + self.rect().y(),
                    self.rect().width(),
                    self.rect().height()
                )
                event.accept()
                return
            else:
                self._is_dragging = True
                # V3.9.0: Capture group position at drag start for undo
                self._group_drag_start = (self.pos().x(), self.pos().y())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self._is_resizing and self._resize_handle:
            delta = event.scenePos() - self._drag_start_pos
            new_rect = QRectF(self._drag_start_rect)
            
            if 'l' in self._resize_handle:
                new_left = new_rect.left() + delta.x()
                if new_rect.right() - new_left >= self.MIN_SIZE:
                    new_rect.setLeft(new_left)
            if 'r' in self._resize_handle:
                new_right = new_rect.right() + delta.x()
                if new_right - new_rect.left() >= self.MIN_SIZE:
                    new_rect.setRight(new_right)
            if 't' in self._resize_handle:
                new_top = new_rect.top() + delta.y()
                if new_rect.bottom() - new_top >= self.MIN_SIZE:
                    new_rect.setTop(new_top)
            if 'b' in self._resize_handle:
                new_bottom = new_rect.bottom() + delta.y()
                if new_bottom - new_rect.top() >= self.MIN_SIZE:
                    new_rect.setBottom(new_bottom)
            
            # Apply the new rect
            self.prepareGeometryChange()
            self.setRect(new_rect.normalized())
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        was_dragging = self._is_dragging
        self._is_dragging = False
        if self._is_resizing:
            self._is_resizing = False
            self._resize_handle = None
            # Update data
            rect = self.rect()
            new_x = self.pos().x() + rect.x()
            new_y = self.pos().y() + rect.y()
            new_rect = (new_x, new_y, rect.width(), rect.height())
            
            # V3.9.0: Emit resize signal for undo if size changed
            if hasattr(self, '_resize_start_state') and self._resize_start_state != new_rect:
                self.signals.size_resize_requested.emit(
                    self.group_data.id,
                    self._resize_start_state,
                    new_rect
                )
            
            # Apply to data
            self.group_data.width = rect.width()
            self.group_data.height = rect.height()
            self.group_data.position.x = new_x
            self.group_data.position.y = new_y
            self.signals.size_changed.emit(self.group_data.id, rect.width(), rect.height())
            event.accept()
            return
        
        # V3.9.0: Emit drag_finished if group was being dragged
        if was_dragging and hasattr(self, '_group_drag_start'):
            old_pos = self._group_drag_start
            new_pos = (self.pos().x(), self.pos().y())
            if old_pos != new_pos:
                self.signals.drag_finished.emit(self.group_data.id, old_pos, new_pos)
        
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Double-click to edit group name (emit request for undo)."""
        if event.pos().y() < self.TITLE_HEIGHT:
            old_name = self.group_data.name
            text, ok = QInputDialog.getText(
                None, "Edit Group Name",
                "Group Name:",
                QLineEdit.EchoMode.Normal,
                old_name
            )
            if ok and text and text != old_name:
                # Emit edit request signal for undo
                self.signals.name_edit_requested.emit(self.group_data.id, old_name, text)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event) -> None:
        """Show context menu on right-click."""
        from PyQt6.QtWidgets import QMenu, QColorDialog
        menu = QMenu()
        
        change_color_action = menu.addAction("Change Color...")
        
        menu.addSeparator()
        
        # V3.9.0: Lock/Unlock action
        lock_text = "🔓 Unlock Group" if self.group_data.is_locked else "🔒 Lock Group"
        lock_action = menu.addAction(lock_text)
        
        action = menu.exec(event.screenPos())
        
        if action == change_color_action:
            color = QColorDialog.getColor(self._color, None, "Choose Group Color")
            if color.isValid():
                self.set_color(color.name())
        elif action == lock_action:
            self.group_data.is_locked = not self.group_data.is_locked
            self.update()
        
    def itemChange(self, change: QGraphicsRectItem.GraphicsItemChange, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange and self._is_dragging:
            # V3.9.0: Block movement if group is locked
            if self.group_data.is_locked:
                return self.pos()
            
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import Qt
            
            modifiers = QApplication.keyboardModifiers()
            new_pos = value
            old_pos = self.pos()
            
            # Apply snap to group position when Shift is held
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                grid_size = 20
                snapped_x = round(new_pos.x() / grid_size) * grid_size
                snapped_y = round(new_pos.y() / grid_size) * grid_size
                new_pos = QPointF(snapped_x, snapped_y)
                value = new_pos
            
            # Calculate delta from (potentially snapped) positions
            dx = new_pos.x() - old_pos.x()
            dy = new_pos.y() - old_pos.y()
            if dx != 0 or dy != 0:
                # Emit moved signal with the actual delta (child nodes will use this)
                self.signals.moved.emit(self.group_data.id, dx, dy)
                
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = value
            self.group_data.position.x = pos.x()
            self.group_data.position.y = pos.y()
            self.signals.position_changed.emit(self.group_data.id, pos.x(), pos.y())
        return super().itemChange(change, value)
    
    def set_color(self, color: str) -> None:
        """Set the group color."""
        self._color = QColor(color)
        self.group_data.color = color
        self.update()
        self.signals.color_changed.emit(self.group_data.id, color)
    
    def get_bounds(self) -> QRectF:
        """Get the bounding rectangle in scene coordinates."""
        return self.mapRectToScene(self.rect())
    
    def contains_node(self, node_id: str) -> bool:
        """Check if a node is in this group."""
        return node_id in self.group_data.node_ids
    
    def add_node(self, node_id: str) -> None:
        """Add a node to this group."""
        if node_id not in self.group_data.node_ids:
            self.group_data.node_ids.append(node_id)
            self.signals.node_added.emit(self.group_data.id, node_id)
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node from this group."""
        if node_id in self.group_data.node_ids:
            self.group_data.node_ids.remove(node_id)
            self.signals.node_removed.emit(self.group_data.id, node_id)
    
    def expand_to_fit(self, node_rect: QRectF, padding: float = 20) -> None:
        """Expand the group to fit a node rectangle (in scene coords)."""
        group_rect = self.get_bounds()
        
        # Calculate needed expansion
        new_left = min(group_rect.left(), node_rect.left() - padding)
        new_top = min(group_rect.top(), node_rect.top() - padding - self.TITLE_HEIGHT)
        new_right = max(group_rect.right(), node_rect.right() + padding)
        new_bottom = max(group_rect.bottom(), node_rect.bottom() + padding)
        
        # Apply new bounds
        self.setPos(new_left, new_top)
        self.setRect(0, 0, new_right - new_left, new_bottom - new_top)
        
        # Update data
        self.group_data.position.x = new_left
        self.group_data.position.y = new_top
        self.group_data.width = new_right - new_left
        self.group_data.height = new_bottom - new_top

