# ResearchFlow

**Version 2.1.0** | The Ultimate Academic Research Workflow Manager

ResearchFlow is a portable, aesthetically pleasing desktop application designed for academic researchers to manage workflows, literature, and ideas. Built with a focus on modern design and fluid user experience, it features a Notion-like interface, rich interactions, and powerful project management tools.

---

## ✨ What's New in V2.1.0

### 🖼️ Enhanced Media & Layout
- **Image Snippets**: Auto-scaling images that fit perfectly within nodes. Double-click to view in full-size.
- **Dynamic Resizing**: Nodes can now be resized horizontally! Drag the handle at the bottom-right corner to adjust layout.
- **Smart Wrapping**: Long text snippets now automatically wrap and calculate height accurately, adapting to the node's width.

### 🎨 UI Refinements
- **Polished Sidebar**: Improved toggle button interactions and layout.
- **Design System**: Standardized horizontal scrolling and consistent icon usage (`icon.ico`).

### ✨ Smooth Animations
- **Animated Zoom**: Smooth, eased zoom transitions when scrolling for a premium feel.
- **Sliding Sidebar**: The project dock slides in/out with fluid animation.
- **Background Grid**: Subtle grid overlay on the canvas for easy node alignment.

## ✨ What's New in V2.0.0

### 🎨 Modern UI/UX Overhaul
- **Apple/Notion-Inspired Design**: Completely redesigned interface with rounded corners, subtle shadows, and a clean, minimalist aesthetic.
- **Fluid Animations**: "Snappy" hover effects on nodes, smooth sidebar transitions, and refined interactions.
- **Advanced Connections**: Bezier curves with tangent-correct arrowhead alignment for beautiful, readable flowcharts.

### 🎛️ Enhanced Global Management
- **Smart Sidebar**: Collapsible project manager that tucks away neatly, accessible via a subtle floating toggle.
- **Project Dashboard**: Integrated description editor, rich TODO list with strikethrough support, and global tag management.
- **Theme Customization**: Global settings for pipeline and reference edge colors.

---

## 🚀 Key Features

### 📊 Flow & Design
- **Pipeline Modules**: Drag-and-drop Input, Process, Decision, and Output modules.
- **Smart Linking**: Right-click and drag to create smooth Bezier connections.
- **Snap-to-Grid**: Hold `Shift` while moving nodes for precise 20px grid alignment.

### 📄 Literature & Snippets
- **Markdown Support**: Drag `.md` files to import papers.
- **LaTeX Rendering**: Native rendering of inline `$math$` and block `$$math$$` formulas with automatic numbering.
- **Multimedia Snippets**: Paste images (`Ctrl+V`) or drag them directly onto nodes.
- **Snippet Management**: Reorder snippets with `↑`/`↓` keys, delete with `Delete`.
- **Text Snippets**: Add text notes with support for Chinese characters (auto-fallback to Microsoft YaHei).

### 🏷️ Organization
- **Tag System**: Create, rename, and drag tags onto nodes. Click tags on nodes to remove them.
- **TODOs**: Integrated task management within your project view.

---

## �️ Quick Start

### Installation

```bash
pip install PyQt6 latex2mathml
```

### Running

```bash
python main.py
```

### Usage Tips

| Action | Shortcut / Gesture |
|--------|-------------------|
| **Delete** | `Delete` key (Nodes, Edges, Snippets) |
| **Snap Move** | Hold `Shift` + Drag Node |
| **Reorder Snippets** | `↑` / `↓` keys |
| **Paste Image** | `Ctrl+V` (with node selected) |
| **Pan Canvas** | Middle Mouse Button Drag |
| **Zoom** | Mouse Wheel |

---

## 📁 Project Structure

```
ResearchFlow/
├── main.py              # Application Entry & Main Window
├── models.py            # Data Models (Dataclasses)
├── graphics_items.py    # Custom QGraphicsItems (Nodes, Edges)
├── widgets.py           # Custom UI Widgets & Modern Components
├── utils.py             # Utilities, ModernTheme, ProjectManager
└── projects/            # Local Data Storage
```

---

## 🔧 Technology

- **Python 3.10+**
- **PyQt6**
- **latex2mathml**

---

*Verified on Windows 10/11.*
