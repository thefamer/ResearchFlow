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
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPolygonF,
    QPainterPath, QPixmap, QFontMetrics, QCursor
)

from models import Snippet, NodeData, NodeMetadata, Position, generate_uuid

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
    IMAGE_MAX_HEIGHT = 100
    SOURCE_LABEL_HEIGHT = 18
    
    def __init__(self, snippet_data: Snippet, parent_node: "BaseNodeItem"):
        super().__init__(parent_node)
        self.snippet_data = snippet_data
        self.parent_node = parent_node
        self._pixmap: Optional[QPixmap] = None
        self._is_hover = False
        self._is_editing_label = False
        
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        # Load image if this is an image snippet
        if snippet_data.type == "image" and snippet_data.content:
            self._load_image()
        
        self._update_geometry()
    
    def _load_image(self) -> None:
        """Load the image from the content path."""
        # Get absolute path from project manager
        # For now, just try to load directly
        try:
            from utils import get_app_root
            # Try relative path first
            path = get_app_root() / "projects" / self.snippet_data.content
            if path.exists():
                self._pixmap = QPixmap(str(path))
            else:
                # Try as absolute path
                self._pixmap = QPixmap(self.snippet_data.content)
        except Exception:
            self._pixmap = None
    
    def _update_geometry(self) -> None:
        """Calculate and update the item geometry."""
        height = self.MIN_HEIGHT
        
        if self.snippet_data.type == "image" and self._pixmap and not self._pixmap.isNull():
            # Scale image to fit width while maintaining aspect ratio
            scaled = self._pixmap.scaledToWidth(
                self.SNIPPET_WIDTH - 2 * self.TEXT_PADDING,
                Qt.TransformationMode.SmoothTransformation
            )
            height = min(scaled.height(), self.IMAGE_MAX_HEIGHT) + 2 * self.TEXT_PADDING
        else:
            # Text snippet - calculate height based on text
            font = QFont("Segoe UI", 9)
            metrics = QFontMetrics(font)
            text_width = self.SNIPPET_WIDTH - 2 * self.TEXT_PADDING
            text = self.snippet_data.content or "(Empty)"
            
            # Word wrap calculation
            words = text.split()
            lines = 1
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if metrics.horizontalAdvance(test_line) > text_width:
                    lines += 1
                    current_line = word
                else:
                    current_line = test_line
            
            height = max(self.MIN_HEIGHT, lines * metrics.height() + 2 * self.TEXT_PADDING)
        
        # Add source label height if present
        if self.snippet_data.source_label:
            height += self.SOURCE_LABEL_HEIGHT
        
        self.setRect(0, 0, self.SNIPPET_WIDTH, height)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        """Paint the snippet."""
        rect = self.rect()
        
        # Background
        bg_color = Colors.SNIPPET_IMAGE_BG if self.snippet_data.type == "image" else Colors.SNIPPET_BG
        if self._is_hover:
            bg_color = bg_color.lighter(110)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(Colors.BORDER, 1))
        painter.drawRoundedRect(rect, 4, 4)
        
        y_offset = self.TEXT_PADDING
        
        # Draw source label if present (editable)
        if self.snippet_data.source_label:
            label_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(label_font)
            painter.setPen(QPen(QColor("#1565C0")))  # Blue color
            label_rect = QRectF(
                self.TEXT_PADDING, y_offset,
                self.SNIPPET_WIDTH - 2 * self.TEXT_PADDING,
                self.SOURCE_LABEL_HEIGHT
            )
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft, self.snippet_data.source_label)
            y_offset += self.SOURCE_LABEL_HEIGHT
        
        # Draw content
        content_rect = QRectF(
            self.TEXT_PADDING, y_offset,
            self.SNIPPET_WIDTH - 2 * self.TEXT_PADDING,
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
            painter.drawPixmap(int(content_rect.x()), int(content_rect.y()), scaled)
        else:
            # Draw text
            text_font = QFont("Segoe UI", 9)
            painter.setFont(text_font)
            painter.setPen(QPen(Colors.TEXT))
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
                    self.SNIPPET_WIDTH - 2 * self.TEXT_PADDING,
                    self.SOURCE_LABEL_HEIGHT
                )
                if label_rect.contains(event.pos()):
                    self._edit_source_label()
                    return
            
            # Edit text content
            if self.snippet_data.type == "text":
                self._edit_text_content()
        
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
        """Show dialog to edit text content."""
        current = self.snippet_data.content
        text, ok = QInputDialog.getMultiLineText(
            None, "Edit Snippet",
            "Content:",
            current
        )
        if ok:
            self.snippet_data.content = text
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


# ============================================================================
# Tag Badge
# ============================================================================
class TagBadge(QGraphicsRectItem):
    """Small colored badge showing an assigned tag."""
    
    BADGE_HEIGHT = 16
    PADDING = 6
    
    def __init__(self, tag_name: str, parent: QGraphicsItem):
        super().__init__(parent)
        self.tag_name = tag_name
        self._color = self._generate_color(tag_name)
        
        # Calculate width based on text
        font = QFont("Segoe UI", 7, QFont.Weight.Bold)
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
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 8, 8)
        
        # Draw text
        font = QFont("Segoe UI", 7, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(Colors.TEXT_LIGHT))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.tag_name)


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
        self.signals = NodeSignals()
        
        self._snippet_items: list[SnippetItem] = []
        self._tag_badges: list[TagBadge] = []
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
    
    def update_layout(self) -> None:
        """Update positions of all child items and recalculate size."""
        # Position snippets vertically
        y = self.HEADER_HEIGHT + 25  # Space for tags
        if self._tag_badges:
            y += 20  # Extra space if tags exist
        
        x = (self.NODE_WIDTH - SnippetItem.SNIPPET_WIDTH) / 2
        
        for snippet_item in self._snippet_items:
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
        
        self.setRect(0, 0, self.NODE_WIDTH, height)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        rect = self.rect()
        
        # Draw body background
        body_rect = QRectF(0, self.HEADER_HEIGHT, rect.width(), rect.height() - self.HEADER_HEIGHT)
        painter.setBrush(QBrush(self._get_body_color()))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(body_rect, 0, 0)
        painter.drawRect(QRectF(0, self.HEADER_HEIGHT, rect.width(), 10))  # Overlap
        
        # Draw header
        header_rect = QRectF(0, 0, rect.width(), self.HEADER_HEIGHT)
        painter.setBrush(QBrush(self._get_header_color()))
        painter.drawRoundedRect(header_rect, 8, 8)
        painter.drawRect(QRectF(0, self.HEADER_HEIGHT - 10, rect.width(), 10))  # Overlap
        
        # Draw header text
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(Colors.TEXT_LIGHT))
        text_rect = QRectF(10, 5, rect.width() - 20, self.HEADER_HEIGHT - 10)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._get_header_text()
        )
        
        # Draw border
        border_pen = QPen(Colors.SELECTION if self.isSelected() else Colors.BORDER, 2 if self.isSelected() else 1)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
        
        # Draw connection indicator if this is being used as connection source
        if self._is_connection_source:
            painter.setPen(QPen(Colors.CONNECTION_LINE, 3))
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 10, 10)
    
    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update node data
            pos = self.pos()
            self.node_data.position.x = pos.x()
            self.node_data.position.y = pos.y()
            self.signals.position_changed.emit(self.node_data.id, pos.x(), pos.y())
        return super().itemChange(change, value)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self._is_hover = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def contextMenuEvent(self, event):
        """Show context menu on right-click."""
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
        """Request deletion of this node."""
        # This will be handled by the scene/main window
        if self.scene():
            self.scene().removeItem(self)
    
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
    """
    
    ARROW_SIZE = 10
    
    def __init__(self, source_node: BaseNodeItem, target_node: BaseNodeItem, edge_id: str = None):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.edge_id = edge_id or generate_uuid()
        
        self.setPen(QPen(Colors.CONNECTION_LINE, 2))
        self.setZValue(-1)  # Draw behind nodes
        
        self.update_path()
    
    def update_path(self) -> None:
        """Recalculate the path based on node positions."""
        if not self.source_node or not self.target_node:
            return
        
        source_center = self.source_node.sceneBoundingRect().center()
        target_center = self.target_node.sceneBoundingRect().center()
        
        # Calculate control points for bezier curve
        dx = target_center.x() - source_center.x()
        dy = target_center.y() - source_center.y()
        
        ctrl1 = QPointF(source_center.x() + dx * 0.5, source_center.y())
        ctrl2 = QPointF(target_center.x() - dx * 0.5, target_center.y())
        
        # Create path
        path = QPainterPath()
        path.moveTo(source_center)
        path.cubicTo(ctrl1, ctrl2, target_center)
        
        self.setPath(path)
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        # Draw the path
        painter.setPen(self.pen())
        painter.drawPath(self.path())
        
        # Draw arrowhead at target
        if self.source_node and self.target_node:
            target_center = self.target_node.sceneBoundingRect().center()
            source_center = self.source_node.sceneBoundingRect().center()
            
            # Calculate angle
            dx = target_center.x() - source_center.x()
            dy = target_center.y() - source_center.y()
            angle = math.atan2(dy, dx)
            
            # Arrowhead points
            arrow_p1 = QPointF(
                target_center.x() - self.ARROW_SIZE * math.cos(angle - math.pi / 6),
                target_center.y() - self.ARROW_SIZE * math.sin(angle - math.pi / 6)
            )
            arrow_p2 = QPointF(
                target_center.x() - self.ARROW_SIZE * math.cos(angle + math.pi / 6),
                target_center.y() - self.ARROW_SIZE * math.sin(angle + math.pi / 6)
            )
            
            # Draw arrowhead
            arrow = QPolygonF([target_center, arrow_p1, arrow_p2])
            painter.setBrush(QBrush(Colors.CONNECTION_LINE))
            painter.drawPolygon(arrow)


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
