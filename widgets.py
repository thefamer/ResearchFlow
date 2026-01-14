"""
ResearchFlow - Custom Widgets
PyQt6 widgets for the application UI.
"""

from typing import Optional, TYPE_CHECKING
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QWidget, QDockWidget,
    QTextBrowser, QFrame, QMessageBox, QInputDialog, QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QDrag, QFont, QColor, QPalette, QPixmap

if TYPE_CHECKING:
    from utils import ProjectManager


# ============================================================================
# Welcome Dialog
# ============================================================================
class WelcomeDialog(QDialog):
    """
    Initial dialog for creating or opening projects.
    """
    
    project_selected = pyqtSignal(str, bool)  # name, is_new
    
    def __init__(self, existing_projects: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("ResearchFlow - Welcome")
        self.setMinimumSize(450, 400)
        self.setModal(True)
        
        self._setup_ui(existing_projects)
        self._apply_styles()
    
    def _setup_ui(self, existing_projects: list[str]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("ResearchFlow")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Portable Research Management Tool")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Create new project section
        new_frame = QFrame()
        new_frame.setFrameShape(QFrame.Shape.StyledPanel)
        new_layout = QVBoxLayout(new_frame)
        
        new_label = QLabel("Create New Project")
        new_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        new_layout.addWidget(new_label)
        
        name_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter project name...")
        self.name_input.returnPressed.connect(self._create_new)
        name_layout.addWidget(self.name_input)
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self._create_new)
        create_btn.setFixedWidth(80)
        name_layout.addWidget(create_btn)
        
        new_layout.addLayout(name_layout)
        layout.addWidget(new_frame)
        
        # Open existing project section
        if existing_projects:
            open_frame = QFrame()
            open_frame.setFrameShape(QFrame.Shape.StyledPanel)
            open_layout = QVBoxLayout(open_frame)
            
            open_label = QLabel("Open Existing Project")
            open_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            open_layout.addWidget(open_label)
            
            self.project_list = QListWidget()
            self.project_list.setMaximumHeight(150)
            for project in existing_projects:
                item = QListWidgetItem(project)
                item.setIcon(self._create_folder_icon())
                self.project_list.addItem(item)
            self.project_list.itemDoubleClicked.connect(self._open_selected)
            open_layout.addWidget(self.project_list)
            
            open_btn = QPushButton("Open Selected")
            open_btn.clicked.connect(self._open_selected)
            open_layout.addWidget(open_btn)
            
            layout.addWidget(open_frame)
        else:
            no_projects = QLabel("No existing projects found.")
            no_projects.setStyleSheet("color: #999; font-style: italic;")
            no_projects.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_projects)
        
        layout.addStretch()
    
    def _create_folder_icon(self) -> "QPixmap":
        """Create a simple folder icon."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor("#FFC107"))
        return pixmap
    
    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
            }
            QFrame {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
        """)
    
    def _create_new(self) -> None:
        name = self.name_input.text().strip()
        if name:
            self.project_selected.emit(name, True)
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid Name", "Please enter a project name.")
    
    def _open_selected(self) -> None:
        if hasattr(self, 'project_list'):
            current = self.project_list.currentItem()
            if current:
                self.project_selected.emit(current.text(), False)
                self.accept()
            else:
                QMessageBox.warning(self, "No Selection", "Please select a project to open.")


# ============================================================================
# Draggable Tag Item
# ============================================================================
class DraggableTagItem(QLabel):
    """A tag that can be dragged onto nodes."""
    
    def __init__(self, tag_name: str, parent=None):
        super().__init__(tag_name, parent)
        self.tag_name = tag_name
        self._color = self._generate_color(tag_name)
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMinimumHeight(28)
        self.setContentsMargins(10, 5, 10, 5)
        
        self._update_style()
    
    def _generate_color(self, text: str) -> QColor:
        """Generate a consistent color based on tag name."""
        hash_val = sum(ord(c) for c in text)
        hue = (hash_val * 37) % 360
        return QColor.fromHsl(hue, 200, 120)
    
    def _update_style(self) -> None:
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {self._color.name()};
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
            }}
            QLabel:hover {{
                background-color: {self._color.darker(110).name()};
            }}
        """)
    
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"tag:{self.tag_name}")
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


# ============================================================================
# Tag Dock Widget
# ============================================================================
class TagDockWidget(QDockWidget):
    """
    Left sidebar dock containing the global tag list.
    Supports adding, removing, and dragging tags.
    """
    
    tag_added = pyqtSignal(str)
    tag_removed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__("Tags", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.setMinimumWidth(150)
        self.setMaximumWidth(250)
        
        self._tags: list[str] = []
        self._tag_widgets: list[DraggableTagItem] = []
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Add tag input
        input_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("New tag...")
        self.tag_input.returnPressed.connect(self._add_tag)
        input_layout.addWidget(self.tag_input)
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.clicked.connect(self._add_tag)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)
        
        # Scrollable tag area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(5)
        self.tags_layout.addStretch()
        
        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)
        
        # Help text
        help_label = QLabel("Drag tags onto nodes to assign")
        help_label.setStyleSheet("color: #999; font-size: 9pt; font-style: italic;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        self.setWidget(container)
    
    def _add_tag(self) -> None:
        """Add a new tag."""
        tag_name = self.tag_input.text().strip()
        if tag_name and tag_name not in self._tags:
            self._tags.append(tag_name)
            
            widget = DraggableTagItem(tag_name)
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(lambda pos, w=widget: self._show_tag_menu(w))
            
            self._tag_widgets.append(widget)
            # Insert before the stretch
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, widget)
            
            self.tag_input.clear()
            self.tag_added.emit(tag_name)
    
    def _show_tag_menu(self, widget: DraggableTagItem) -> None:
        """Show context menu for a tag."""
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Tag")
        action = menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))
        
        if action == delete_action:
            self._remove_tag(widget.tag_name)
    
    def _remove_tag(self, tag_name: str) -> None:
        """Remove a tag."""
        if tag_name in self._tags:
            self._tags.remove(tag_name)
            
            for widget in self._tag_widgets:
                if widget.tag_name == tag_name:
                    self._tag_widgets.remove(widget)
                    widget.deleteLater()
                    break
            
            self.tag_removed.emit(tag_name)
    
    def set_tags(self, tags: list[str]) -> None:
        """Set the tag list (for loading projects)."""
        # Clear existing
        for widget in self._tag_widgets:
            widget.deleteLater()
        self._tag_widgets.clear()
        self._tags.clear()
        
        # Add new tags
        for tag_name in tags:
            self._tags.append(tag_name)
            widget = DraggableTagItem(tag_name)
            widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            widget.customContextMenuRequested.connect(lambda pos, w=widget: self._show_tag_menu(w))
            self._tag_widgets.append(widget)
            self.tags_layout.insertWidget(self.tags_layout.count() - 1, widget)
    
    def get_tags(self) -> list[str]:
        """Get the current tag list."""
        return self._tags.copy()


# ============================================================================
# Markdown Viewer Dialog
# ============================================================================
class MarkdownViewerDialog(QDialog):
    """
    Floating window for rendering Markdown content.
    """
    
    def __init__(self, title: str, markdown_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📄 {title}")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        self._setup_ui(markdown_path)
    
    def _setup_ui(self, markdown_path: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Text browser for rendering
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet("""
            QTextBrowser {
                background-color: white;
                padding: 20px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11pt;
                line-height: 1.6;
            }
        """)
        
        # Load and display content
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple markdown to HTML conversion
            html = self._markdown_to_html(content)
            self.browser.setHtml(html)
        except Exception as e:
            self.browser.setText(f"Error loading file: {e}")
        
        layout.addWidget(self.browser)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        btn_layout.addWidget(close_btn)
        btn_layout.setContentsMargins(10, 10, 10, 10)
        layout.addLayout(btn_layout)
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Basic markdown to HTML conversion."""
        import re
        
        html = markdown
        
        # Headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Code blocks
        html = re.sub(r'```(\w*)\n(.*?)```', r'<pre style="background:#f5f5f5;padding:10px;border-radius:4px;"><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code style="background:#f5f5f5;padding:2px 5px;border-radius:3px;">\1</code>', html)
        
        # Links
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Line breaks
        html = html.replace('\n\n', '</p><p>')
        html = f'<p>{html}</p>'
        
        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; line-height: 1.6; }}
                h1 {{ color: #1976D2; border-bottom: 2px solid #E3F2FD; padding-bottom: 10px; }}
                h2 {{ color: #1565C0; }}
                h3 {{ color: #0D47A1; }}
                a {{ color: #2196F3; }}
                pre {{ overflow-x: auto; }}
            </style>
        </head>
        <body>{html}</body>
        </html>
        """


# ============================================================================
# Module Palette (Draggable Shapes)
# ============================================================================
class ModulePaletteItem(QLabel):
    """A draggable module shape for the palette."""
    
    def __init__(self, module_type: str, label: str, color: QColor, parent=None):
        super().__init__(label, parent)
        self.module_type = module_type
        self._color = color
        
        self.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedSize(80, 50)
        
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color.name()};
                color: white;
                border-radius: 6px;
                padding: 5px;
            }}
            QLabel:hover {{
                background-color: {color.darker(110).name()};
            }}
        """)
    
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(f"module:{self.module_type}")
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ModulePalette(QWidget):
    """Palette of draggable module shapes."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        label = QLabel("Modules:")
        label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(label)
        
        # Module types
        modules = [
            ("input", "Input", QColor("#4CAF50")),
            ("process", "Process", QColor("#9C27B0")),
            ("decision", "Decision", QColor("#FF9800")),
            ("output", "Output", QColor("#2196F3")),
        ]
        
        for module_type, label_text, color in modules:
            item = ModulePaletteItem(module_type, label_text, color)
            layout.addWidget(item)
        
        layout.addStretch()
        
        # Help text
        help_label = QLabel("Drag modules to canvas")
        help_label.setStyleSheet("color: #999; font-style: italic;")
        layout.addWidget(help_label)


# ============================================================================
# Pipeline Required Dialog
# ============================================================================
class PipelineRequiredDialog(QDialog):
    """Dialog shown when a pipeline must be created first."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pipeline Required")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Icon/Title
        title = QLabel("⚠️ Pipeline Required")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Message
        msg = QLabel(
            "Before importing references, you must create at least one\n"
            "Pipeline Module to define your research workflow.\n\n"
            "Drag a module from the toolbar onto the canvas to begin."
        )
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)
        
        # OK button
        btn = QPushButton("Got it!")
        btn.clicked.connect(self.accept)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
