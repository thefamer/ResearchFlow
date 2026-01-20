# ResearchFlow

<p align="center">
  <img src="icon.ico" alt="ResearchFlow Logo" width="80" height="80">
</p>

<p align="center">
  <strong>The Ultimate Academic Research Workflow Manager</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-4.1.0-blue.svg" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green.svg" alt="Python">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-orange.svg" alt="License">
  <img src="https://img.shields.io/badge/PyQt6-6.0+-purple.svg" alt="PyQt6">
</p>

<p align="center">
  <a href="https://github.com/thefamer/ResearchFlow/releases"><strong>📥 Download v4.1.0 .exe from Releases</strong></a>
</p>

> **💡 Just want it to work?** v4.1.0 **portable standalone .exe** is available in [Releases](https://github.com/thefamer/ResearchFlow/releases) – download and run, no Python required!

---

ResearchFlow is a portable, aesthetically pleasing desktop application designed for academic researchers to manage workflows, literature, and ideas. Built with a focus on modern design and fluid user experience, it features a Notion-like interface, rich interactions, and powerful project management tools.

---

## ✨ What's New in V4.1.0

### 🎨 Infinite Canvas
- **Expanded Workspace**: Canvas now extends to ±25,000 units in all directions, similar to Figma's infinite canvas design.
- **Seamless Panning**: Navigate freely without hitting boundaries.

### ⌨️ Smart Description Undo
- **Command Batching**: Consecutive text edits within 3 seconds are merged into a single undo action.
- **Cursor Preservation**: Fixed bug where cursor would jump to the beginning after each keystroke during undo/redo.
- **Efficient History**: Reduces undo stack clutter from rapid typing.

### 🛠️ Technical Details
- Description changes use `can_merge_with()` and `merge_with()` pattern for intelligent batching.
- New `set_description_no_cursor_reset()` method preserves cursor position during text updates.

<details>
<summary><strong>📜 Previous Versions</strong></summary>

### V4.0.0
- **Complete Undo/Redo System**: Stable version covering canvas, snippets, metadata, tags, groups, and node states.
- **Flag & Lock Undo**: Toggling flag or lock state is fully undoable.
- **Locked Group Protection**: Nodes cannot be added to locked groups.
- **Position Preservation**: Fixed critical bug with locked nodes resetting to origin.

### V3.9.0
- **Comprehensive Undo/Redo**: Every canvas action is undoable with 100-step history.
- **Waypoint Nodes**: Flexible bend points for connections with adaptive visuals.
- **Node Flagging & Locking**: Mark important nodes and prevent accidental movement.
- **Global Color Sync**: Fixed palette and tag color synchronization.

### V3.5.0
- **Node Grouping**: Visual containers with auto-containment (Ctrl+Drag).
- **TODO Enhancements**: Context menu for editing and reordering tasks.

### V3.1.0
- **Tag Customization**: Custom colors and reordering.
- **Module Palette**: Global color management for module types.

### V3.0.0
- **Portable .exe**: Standalone build with local data storage.

</details>

---

## 🚀 Key Features

### 📊 Flow & Design
- **Pipeline & Reference**: Distinguish between your research pipeline and supporting literature.
- **Smart Waypoints**: Use waypoints to manage complex flowchart layouts without overlapping lines.
- **Snap-to-Grid**: Hold `Shift` while moving nodes for precise 20px grid alignment.
- **Node Status**: Toggle "Locked" or "Flagged" states for better organization.

### 🔄 State Persistence
- **Auto-Save**: Project data is saved automatically on every interaction.
- **Undo History**: Full persistence of your operation history across sessions.

### 📄 Literature & Snippets
- **Markdown Support**: Drag `.md` files to import papers as reference nodes.
- **PDF to Markdown**: We recommend using [MinerU](https://github.com/opendatalab/MinerU) to convert PDF papers to Markdown format for import.
- **LaTeX Rendering**: Native rendering of inline `$math$` and block `$$math$$` formulas with automatic numbering.
- **Multimedia Snippets**: Paste images (`Ctrl+V`) or drag them directly onto nodes.
- **Snippet Management**: Reorder snippets with `↑`/`↓` keys, delete with `Delete`.
- **Text Snippets**: Add text notes with support for Chinese characters (auto-fallback to Microsoft YaHei).

### 🏷️ Organization
- **Tag System**: Create, rename, and drag tags onto nodes. Click tags on nodes to remove them.
- **TODOs**: Integrated task management within your project view.

---

## 🛠️ Installation

### Prerequisites

- Python 3.10 or higher
- Windows 10/11 (primary platform)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/thefamer/ResearchFlow.git
cd ResearchFlow

# Install dependencies
pip install -r requirements.txt
```

Or install dependencies manually:

```bash
pip install PyQt6 latex2mathml
```

### Running

```bash
python main.py
```

### 📦 Building Portable .exe (Optional)

Create a standalone portable executable that runs without Python installed:

```bash
pip install pyinstaller

# Option 1: Single folder (recommended, faster startup)
pyinstaller --noconsole --onedir --icon=icon.ico --add-data "icon.ico;." --collect-all latex2mathml --name="ResearchFlow" main.py

# Option 2: Single file (slower startup, but just one file)
pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." --collect-all latex2mathml --name="ResearchFlow" main.py
```

The generated files will be in the `dist/` folder. 

> **✅ True Portable**: The `projects/` data folder is automatically created next to the `.exe` file, not in any temp or system folder. Copy the folder and your `projects/` anywhere!

---

## ⌨️ Keyboard Shortcuts

| Action | Shortcut / Gesture |
|--------|-------------------|
| **Delete** | `Delete` key (Nodes, Edges, Snippets) |
| **Snap Move** | Hold `Shift` + Drag Node |
| **Reorder Snippets** | `↑` / `↓` keys |
| **Paste Image** | `Ctrl+V` (with node selected) |
| **Pan Canvas** | Middle Mouse Button Drag |
| **Zoom** | Mouse Wheel (Smooth animated) |
| **Save Project** | `Ctrl+S` |
| **New Project** | `Ctrl+N` |
| **Open Project** | `Ctrl+O` |
| **Undo** | `Ctrl+Z` |
| **Redo** | `Ctrl+Y` / `Ctrl+Shift+Z` |
| **Delete** | `Delete` key |
| **Snap Move** | Hold `Shift` + Drag |
| **Group Bind** | Hold `Ctrl` + Drag into Group |
| **Multi-Select** | `Ctrl` + Click |
| **Zoom** | Mouse Wheel |
| **Pan** | Middle Mouse Button Drag |

---

## 📁 Project Structure

```
ResearchFlow/
├── main.py              # Application Entry & MainWindow
├── models.py            # Data Models (Dataclasses)
├── undo.py              # Undo/Redo Engine & Commands (V3.9.0)
├── graphics_items.py    # Custom QGraphicsItems (Nodes, Groups, Waypoints)
├── widgets.py           # Custom UI (Sidebar, Color Palette, Tags)
├── utils.py             # Theme & Project Logic
└── projects/            # Local Data Storage
    └── <project_name>/
        ├── project_data.json
        └── assets/
            ├── papers/
            └── images/
```

---

## 🔧 Technology Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.10+ |
| **UI Framework** | PyQt6 |
| **Math Rendering** | latex2mathml |
| **Data Storage** | JSON (portable, no database) |
| **Graphics** | QGraphicsView Framework |

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. **Open** a Pull Request

### Development Notes

- Follow PEP 8 style guidelines
- Add type hints to new functions
- Update documentation for new features
- Test on Windows before submitting

---

## 📋 Roadmap

- [ ] macOS / Linux support
- [ ] Export to PNG / PDF
- [ ] Cloud sync integration
- [ ] Plugin system
- [ ] Dark theme

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by [Notion](https://notion.so) and [Obsidian](https://obsidian.md)
- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- Icons and design inspired by Apple Human Interface Guidelines

---

<p align="center">
  Made with ❤️ for researchers everywhere
</p>

<p align="center">
  <a href="#researchflow">Back to Top ↑</a>
</p>