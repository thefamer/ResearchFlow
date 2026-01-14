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
    snippet_added = pyqtSignal(str)  # node_id
    snippet_removed = pyqtSignal(str, str)  # node_id, snippet_id
    expand_requested = pyqtSignal(str)  # node_id
    connection_started = pyqtSignal(str)  # source_node_id
    connection_completed = pyqtSignal(str, str)  # source_node_id, target_node_id
    data_changed = pyqtSignal(str)  # node_id


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
        """Show dialog to edit source label."""
        current = self.snippet_data.source_label
        text, ok = QInputDialog.getText(
            None, "Edit Source Label",
            "Source Label:",
            QLineEdit.EchoMode.Normal,
            current
        )
        if ok:
            self.snippet_data.source_label = text
            self._update_geometry()
            self.update()
            self.parent_node.update_layout()
    
    def _edit_text_content(self) -> None:
        """Show dialog to edit text content with word wrap."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
        
        dialog = QDialog()
        dialog.setWindowTitle("Edit Snippet")
        dialog.setMinimumSize(400, 300)
        dialog.resize(500, 350)
        
        layout = QVBoxLayout(dialog)
        
        # Text edit with word wrap
        text_edit = QTextEdit()
        text_edit.setPlainText(self.snippet_data.content)
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
            self.snippet_data.content = text_edit.toPlainText()
            self._update_geometry()
            self.update()
            self.parent_node.update_layout()
    
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
    
    def __init__(self, tag_name: str, parent: "BaseNodeItem"):
        super().__init__(parent)
        self.tag_name = tag_name
        self.parent_node = parent
        self._color = self._generate_color(tag_name)
        self._is_hover = False
        
        # Make interactive
        self.setAcceptHoverEvents(True)
        
        # Calculate width based on text
        font = ModernTheme.get_ui_font(7, bold=True)
        metrics = QFontMetrics(font)
        width = metrics.horizontalAdvance(tag_name) + 2 * self.PADDING
        
        self.setRect(0, 0, width, self.BADGE_HEIGHT)
    
    def _generate_color(self, text: str) -> QColor:
        """Generate a consistent color based on tag name."""
        hash_val = sum(ord(c) for c in text)
        hue = (hash_val * 37) % 360
        return QColor.fromHsl(hue, 200, 120)
    
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
            badge = TagBadge(tag, self)
            self._tag_badges.append(badge)
        
        self._layout_tags()
    
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
            # Snap to grid when Shift is held
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
        
        delete_action = menu.addAction("Delete Node")
        delete_action.triggered.connect(self._request_delete)
        
        menu.exec(event.screenPos())
    
    def _add_text_snippet(self) -> None:
        """Add a new empty text snippet."""
        snippet = Snippet(type="text", content="")
        self.node_data.snippets.append(snippet)
        
        item = SnippetItem(snippet, self)
        self._snippet_items.append(item)
        
        self.update_layout()
        self.signals.snippet_added.emit(self.node_data.id)
        self.signals.data_changed.emit(self.node_data.id)
    
    def add_image_snippet(self, relative_path: str) -> None:
        """Add an image snippet with the given path."""
        snippet = Snippet(type="image", content=relative_path)
        self.node_data.snippets.append(snippet)
        
        item = SnippetItem(snippet, self)
        self._snippet_items.append(item)
        
        self.update_layout()
        self.signals.snippet_added.emit(self.node_data.id)
        self.signals.data_changed.emit(self.node_data.id)
    
    def add_cloned_snippets(self, source_snippets: list[Snippet], source_title: str) -> None:
        """Add deep-copied snippets from another node."""
        for snippet in source_snippets:
            cloned = snippet.deep_copy(source_title)
            self.node_data.snippets.append(cloned)
            
            item = SnippetItem(cloned, self)
            self._snippet_items.append(item)
        
        self.update_layout()
        self.signals.data_changed.emit(self.node_data.id)
    
    def add_tag(self, tag_name: str) -> None:
        """Assign a tag to this node."""
        if tag_name not in self.node_data.tags:
            self.node_data.tags.append(tag_name)
            badge = TagBadge(tag_name, self)
            self._tag_badges.append(badge)
            self._layout_tags()
            self.update_layout()
            self.signals.data_changed.emit(self.node_data.id)
    
    def remove_tag(self, tag_name: str) -> None:
        """Remove a tag from this node."""
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
        """Remove a snippet from this node."""
        if snippet_item in self._snippet_items:
            # Remove from data
            if snippet_item.snippet_data in self.node_data.snippets:
                self.node_data.snippets.remove(snippet_item.snippet_data)
            
            # Remove from UI
            self._snippet_items.remove(snippet_item)
            if snippet_item.scene():
                snippet_item.scene().removeItem(snippet_item)
            
            self.update_layout()
            self.signals.snippet_removed.emit(self.node_data.id, snippet_item.snippet_data.id)
            self.signals.data_changed.emit(self.node_data.id)
    
    def move_snippet_up(self, snippet_item: "SnippetItem") -> None:
        """Move a snippet up in the list."""
        if snippet_item in self._snippet_items:
            idx = self._snippet_items.index(snippet_item)
            if idx > 0:
                # Swap in UI list
                self._snippet_items[idx], self._snippet_items[idx-1] = \
                    self._snippet_items[idx-1], self._snippet_items[idx]
                
                # Swap in data list
                data_idx = self.node_data.snippets.index(snippet_item.snippet_data)
                if data_idx > 0:
                    self.node_data.snippets[data_idx], self.node_data.snippets[data_idx-1] = \
                        self.node_data.snippets[data_idx-1], self.node_data.snippets[data_idx]
                
                self.update_layout()
                self.signals.data_changed.emit(self.node_data.id)
    
    def move_snippet_down(self, snippet_item: "SnippetItem") -> None:
        """Move a snippet down in the list."""
        if snippet_item in self._snippet_items:
            idx = self._snippet_items.index(snippet_item)
            if idx < len(self._snippet_items) - 1:
                # Swap in UI list
                self._snippet_items[idx], self._snippet_items[idx+1] = \
                    self._snippet_items[idx+1], self._snippet_items[idx]
                
                # Swap in data list
                data_idx = self.node_data.snippets.index(snippet_item.snippet_data)
                if data_idx < len(self.node_data.snippets) - 1:
                    self.node_data.snippets[data_idx], self.node_data.snippets[data_idx+1] = \
                        self.node_data.snippets[data_idx+1], self.node_data.snippets[data_idx]
                
                self.update_layout()
                self.signals.data_changed.emit(self.node_data.id)


# ============================================================================
# Pipeline Module Item
# ============================================================================
class PipelineModuleItem(BaseNodeItem):
    """
    A pipeline module node (flowchart shape).
    Types: input, output, process, decision
    """
    
    MODULE_COLORS = {
        "input": Colors.PIPELINE_INPUT,
        "output": Colors.PIPELINE_OUTPUT,
        "process": Colors.PIPELINE_PROCESS,
        "decision": Colors.PIPELINE_DECISION,
    }
    
    def __init__(self, node_data: NodeData):
        super().__init__(node_data)
    
    def _get_header_color(self) -> QColor:
        module_type = self.node_data.metadata.module_type or "process"
        return self.MODULE_COLORS.get(module_type, Colors.PIPELINE_PROCESS)
    
    def _get_header_text(self) -> str:
        name = self.node_data.metadata.module_name or "Module"
        type_label = self.node_data.metadata.module_type.capitalize() if self.node_data.metadata.module_type else ""
        if type_label:
            return f"{name} [{type_label}]"
        return name
    
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Edit module name on double-click header."""
        if event.pos().y() < self.HEADER_HEIGHT:
            text, ok = QInputDialog.getText(
                None, "Edit Module Name",
                "Module Name:",
                QLineEdit.EchoMode.Normal,
                self.node_data.metadata.module_name
            )
            if ok and text:
                self.node_data.metadata.module_name = text
                self.update()
                self.signals.data_changed.emit(self.node_data.id)
        else:
            super().mouseDoubleClickEvent(event)


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
        border_pen = QPen(Colors.SELECTION if self.isSelected() else Colors.BORDER, 2 if self.isSelected() else 1)
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
                text, ok = QInputDialog.getText(
                    None, "Edit Title",
                    "Paper Title:",
                    QLineEdit.EchoMode.Normal,
                    self.node_data.metadata.title
                )
                if ok and text:
                    self.node_data.metadata.title = text
                    self.update()
                    self.signals.data_changed.emit(self.node_data.id)
            else:
                # Edit year/conference
                year, ok = QInputDialog.getText(
                    None, "Edit Year",
                    "Year:",
                    QLineEdit.EchoMode.Normal,
                    self.node_data.metadata.year
                )
                if ok:
                    self.node_data.metadata.year = year
                
                conf, ok = QInputDialog.getText(
                    None, "Edit Conference",
                    "Conference/Journal:",
                    QLineEdit.EchoMode.Normal,
                    self.node_data.metadata.conference
                )
                if ok:
                    self.node_data.metadata.conference = conf
                
                self.update()
                self.signals.data_changed.emit(self.node_data.id)
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
    A connection arrow between two nodes.
    Drawn as a curved bezier path with an arrowhead.
    Supports selection and deletion via context menu.
    Different colors for reference vs pipeline connections.
    """
    
    ARROW_SIZE = 10
    
    def __init__(self, source_node: BaseNodeItem, target_node: BaseNodeItem, edge_id: str = None,
                 pipeline_color: str = "#607D8B", reference_color: str = "#4CAF50"):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.edge_id = edge_id or generate_uuid()
        self._is_hover = False
        
        # Determine edge type and color
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
        
        # Calculate edge intersection points
        source_edge = self._get_edge_point(source_rect, source_center, target_center)
        target_edge = self._get_edge_point(target_rect, target_center, source_center)
        
        # Calculate control points for bezier curve
        dx = target_edge.x() - source_edge.x()
        dy = target_edge.y() - source_edge.y()
        
        # Adjust control points based on direction
        ctrl_offset = min(abs(dx) * 0.5, 80)  # Cap the curve
        ctrl1 = QPointF(source_edge.x() + ctrl_offset * (1 if dx >= 0 else -1), source_edge.y())
        ctrl2 = QPointF(target_edge.x() - ctrl_offset * (1 if dx >= 0 else -1), target_edge.y())
        
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
