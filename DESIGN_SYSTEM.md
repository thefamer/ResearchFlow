# ResearchFlow Design System

This document serves as the Single Source of Truth (SSOT) for the visual design and user interface interactions of ResearchFlow.

## 🎨 Design Philosophy
**"Minimalist, Fluid, Content-First"**
Inspired by **Notion** and **Apple** design principles, ResearchFlow aims to reduce visual clutter, favoring whitespace, clean typography, and subtle, meaningful animations over heavy skeumorphism or complex gradients.

---

## 🌈 Color Palette

### Backgrounds
| Token | Hex | Usage |
|-------|-----|-------|
| `BG_PRIMARY` | `#FFFFFF` | Main content areas, Node bodies |
| `BG_SECONDARY` | `#F7F7F5` | Canvas background, Sidebar, Panel backgrounds |
| `BG_TERTIARY` | `#EBEBEB` | Hover states, Inputs on focus, Separators |

### Typography
| Token | Hex | Usage |
|-------|-----|-------|
| `TEXT_PRIMARY` | `#37352F` | Main bodies, Node headers (Notion Black) |
| `TEXT_SECONDARY` | `#787774` | Metadata, Placeholders, Icon buttons |
| `TEXT_INVERTED` | `#FFFFFF` | Text on headers/colored badges |

### Accents
| Token | Hex | Usage |
|-------|-----|-------|
| `ACCENT_COLOR` | `#2EAADC` | Primary actions, Selected states, Focus rings |
| `ACCENT_HOVER` | `#1B8FBf` | Button active states |

### Structural
| Token | Hex | Usage |
|-------|-----|-------|
| `BORDER_LIGHT` | `#E0E0E0` | Subtle dividers, Input borders, Node borders |
| `BORDER_FOCUS` | `rgba(46, 170, 220, 0.4)` | Focus halos |

---

## 🔤 Typography

### Font Stack
**Primary**: `"Microsoft YaHei UI"`, `"Segoe UI"`, `"Roboto"`, `sans-serif`
*Prioritizes **Microsoft YaHei UI** on Windows to ensure consistent CJK (Chinese) rendering.*

### Hierarchy
*   **Window Titles**: 10pt Bold
*   **Node Headers**: 10pt Bold
*   **Body Text**: 9pt Regular (Snippets, Content)
*   **Labels/Tags**: 7pt-8pt Bold (Source labels, Badges)
*   **UI Controls**: 16px Bold (Sidebar Toggles, Close Buttons)

---

## 🧩 Components & Graphics

### 1. Nodes (BaseNodeItem)
*   **Shape**: Rounded Rectangle (12px radius).
*   **Header**: Color strip (6px height) + Bold Title + Date/Subtitle.
*   **Shadow**: None by default (Flat) -> `SHADOW_MEDIUM` can be applied if needed in future.
*   **Interaction**: "Snappy Zoom"
    *   **Hover**: Scale `1.02x`, Z-Index `10` (Pop to front).
    *   **Leave**: Scale `1.0x`, Z-Index `0`.

### 2. Snippets (SnippetItem)
*   **Shape**: Rounded Rect (8px radius).
*   **Background**: White (Default) -> `BG_TERTIARY` (Hover).
*   **Border**: 1px `BORDER_LIGHT` (Default) -> 2px `ACCENT_COLOR` (Selected).
*   **Content**:
    *   **Text**: Word-wrapped, 9pt.
    *   **Image**: Max height 300px, aspect-ratio preserved. Double-click to expand.

### 3. Connections (EdgeItem)
*   **Style**: Cubic Bezier Curve.
*   **Path**: Computed from source edge to target edge.
*   **Arrowhead**: Re-calculated using **Path Tangent** at 100% length to ensure perfect alignment with the curve direction.
*   **Stroke**: 2px width (Default) -> 3px (Hover) -> 4px (Selected).

### 4. Sidebar (ProjectDockWidget)
*   **Behavior**: Collapsible dock.
*   **Title Bar**: Custom `ModernDockTitleBar`.
    *   Buttons: Minimalist glyphs (`❐`, `✕`), 28px hit area, `#666` text.
*   **Toggle**: Floating `›` button, 24px Bold, `#555` Dark Gray for high visibility.

### 5. Scrollbars (Global)
*   **Style**: Mac-OS style thin overlay.
*   **Width/Height**: 10px.
*   **Track**: Transparent.
*   **Handle**: `#D0D0D0` rounded (5px radius), darkens to `#A0A0A0` on hover.

---

## 🕹️ Interaction Models

*   **Double Click**:
    *   **Node Header**: Edit Title/Date.
    *   **Snippet Text**: Edit Content.
    *   **Snippet Image**: Open Full-Screen Viewer.
    *   **Sidebar Title**: Toggle Float/Dock.
*   **Drag & Drop**:
    *   **.md Files**: Import as Reference Node.
    *   **Images**: Paste (`Ctrl+V`) into selected node.
*   **Key Combos**:
    *   `Shift + Drag`: Grid Snap (20px).
    *   `Delete`: Remove selection.
