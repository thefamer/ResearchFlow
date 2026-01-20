"""
ResearchFlow - Undo/Redo System
Command pattern implementation for reversible operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
import json
from pathlib import Path


class Command(ABC):
    """Base class for undoable commands."""
    
    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass
    
    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass
    
    @abstractmethod
    def to_dict(self) -> dict:
        """Serialize command for persistence."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict, context: Any) -> "Command":
        """Deserialize command from dict."""
        pass


@dataclass
class DescriptionChangeCommand(Command):
    """Command for changing project description with merge support."""
    context: Any  # MainWindow or ProjectManager reference
    old_value: str
    new_value: str
    timestamp: float = field(default_factory=lambda: __import__('time').time())
    
    # V4.1.0: Merge timeout in seconds
    MERGE_TIMEOUT = 3.0
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.set_description_no_cursor_reset(self.new_value)
    
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.set_description_no_cursor_reset(self.old_value)
    
    def can_merge_with(self, other: "DescriptionChangeCommand") -> bool:
        """Check if this command can be merged with another."""
        import time
        if not isinstance(other, DescriptionChangeCommand):
            return False
        # Check time difference
        if time.time() - self.timestamp > self.MERGE_TIMEOUT:
            return False
        return True
    
    def merge_with(self, other: "DescriptionChangeCommand") -> None:
        """Merge another command into this one (update new_value and timestamp)."""
        import time
        self.new_value = other.new_value
        self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        return {
            "type": "DescriptionChange",
            "old_value": self.old_value,
            "new_value": self.new_value
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "DescriptionChangeCommand":
        return cls(
            context=context,
            old_value=data["old_value"],
            new_value=data["new_value"]
        )


@dataclass
class TodoAddCommand(Command):
    """Command for adding a todo item."""
    context: Any
    todo_text: str
    todo_index: int = -1
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.add_todo(self.todo_text)
    
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.remove_todo_at(self.todo_index)
    
    def to_dict(self) -> dict:
        return {
            "type": "TodoAdd",
            "todo_text": self.todo_text,
            "todo_index": self.todo_index
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TodoAddCommand":
        return cls(
            context=context,
            todo_text=data["todo_text"],
            todo_index=data["todo_index"]
        )


@dataclass
class TodoRemoveCommand(Command):
    """Command for removing a todo item."""
    context: Any
    todo_index: int
    todo_text: str
    is_done: bool
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.remove_todo_at(self.todo_index)
    
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.insert_todo(self.todo_index, self.todo_text, self.is_done)
    
    def to_dict(self) -> dict:
        return {
            "type": "TodoRemove",
            "todo_index": self.todo_index,
            "todo_text": self.todo_text,
            "is_done": self.is_done
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TodoRemoveCommand":
        return cls(
            context=context,
            todo_index=data["todo_index"],
            todo_text=data["todo_text"],
            is_done=data["is_done"]
        )

@dataclass
class TodoEditCommand(Command):
    """Command for editing todo text."""
    context: Any
    todo_index: int
    old_text: str
    new_text: str
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.update_todo_text(self.todo_index, self.new_text)
            
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.update_todo_text(self.todo_index, self.old_text)

    def to_dict(self) -> dict:
        return {
            "type": "TodoEdit",
            "todo_index": self.todo_index,
            "old_text": self.old_text,
            "new_text": self.new_text
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TodoEditCommand":
        return cls(
            context=context,
            todo_index=data["todo_index"],
            old_text=data["old_text"],
            new_text=data["new_text"]
        )

@dataclass
class TodoToggleCommand(Command):
    """Command for toggling todo completion status."""
    context: Any
    todo_index: int
    new_state: bool  # True for done
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.set_todo_status(self.todo_index, self.new_state)

    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.set_todo_status(self.todo_index, not self.new_state)

    def to_dict(self) -> dict:
        return {
            "type": "TodoToggle",
            "todo_index": self.todo_index,
            "new_state": self.new_state
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TodoToggleCommand":
        return cls(
            context=context,
            todo_index=data["todo_index"],
            new_state=data["new_state"]
        )

@dataclass
class TodoMoveCommand(Command):
    """Command for moving a todo item."""
    context: Any
    from_index: int
    to_index: int
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.move_todo(self.from_index, self.to_index)

    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.move_todo(self.to_index, self.from_index)

    def to_dict(self) -> dict:
        return {
            "type": "TodoMove",
            "from_index": self.from_index,
            "to_index": self.to_index
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TodoMoveCommand":
        return cls(
            context=context,
            from_index=data["from_index"],
            to_index=data["to_index"]
        )

# --- Tag Commands ---

@dataclass
class TagAddCommand(Command):
    """Command for adding a tag."""
    context: Any
    tag_name: str
    tag_index: int = -1  # Will be set to end of list
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            # Add at end
            self.context.project_dock.insert_tag(
                len(self.context.project_dock._tags), 
                self.tag_name, 
                None  # Default color
            )
            self.tag_index = len(self.context.project_dock._tags) - 1
    
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.remove_tag_by_name(self.tag_name)
    
    def to_dict(self) -> dict:
        return {
            "type": "TagAdd",
            "tag_name": self.tag_name,
            "tag_index": self.tag_index
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TagAddCommand":
        return cls(
            context=context,
            tag_name=data["tag_name"],
            tag_index=data.get("tag_index", -1)
        )

@dataclass
class TagRemoveCommand(Command):
    """Command for removing a tag."""
    context: Any
    tag_name: str
    tag_color: str
    tag_index: int
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.remove_tag_by_name(self.tag_name)
            
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.insert_tag(self.tag_index, self.tag_name, self.tag_color)
            
    def to_dict(self) -> dict:
        return {
            "type": "TagRemove",
            "tag_name": self.tag_name,
            "tag_color": self.tag_color,
            "tag_index": self.tag_index
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TagRemoveCommand":
        return cls(
            context=context,
            tag_name=data["tag_name"],
            tag_color=data["tag_color"],
            tag_index=data["tag_index"]
        )

@dataclass
class TagRenameCommand(Command):
    """Command for renaming a tag."""
    context: Any
    old_name: str
    new_name: str
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.rename_tag_item(self.old_name, self.new_name)
            
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.rename_tag_item(self.new_name, self.old_name)
            
    def to_dict(self) -> dict:
        return {
            "type": "TagRename",
            "old_name": self.old_name,
            "new_name": self.new_name
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TagRenameCommand":
        return cls(
            context=context,
            old_name=data["old_name"],
            new_name=data["new_name"]
        )

@dataclass
class TagColorChangeCommand(Command):
    """Command for changing tag color."""
    context: Any
    tag_name: str
    old_color: str
    new_color: str
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.set_tag_color(self.tag_name, self.new_color)
            self._sync_to_nodes(self.new_color)
            
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.set_tag_color(self.tag_name, self.old_color)
            self._sync_to_nodes(self.old_color)
    
    def _sync_to_nodes(self, color: str) -> None:
        """Sync tag color to all nodes that have this tag."""
        if hasattr(self.context, 'scene'):
            for node in self.context.scene._nodes.values():
                if self.tag_name in node.node_data.tags:
                    for badge in node._tag_badges:
                        if badge.tag_name == self.tag_name:
                            badge.set_color(color)
    
    def to_dict(self) -> dict:
        return {
            "type": "TagColorChange",
            "tag_name": self.tag_name,
            "old_color": self.old_color,
            "new_color": self.new_color
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TagColorChangeCommand":
        return cls(
            context=context,
            tag_name=data["tag_name"],
            old_color=data["old_color"],
            new_color=data["new_color"]
        )

@dataclass
class TagMoveCommand(Command):
    """Command for moving a tag."""
    context: Any
    from_index: int
    to_index: int
    
    def execute(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.move_tag(self.from_index, self.to_index)
            
    def undo(self) -> None:
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.move_tag(self.to_index, self.from_index)
            
    def to_dict(self) -> dict:
        return {
            "type": "TagMove",
            "from_index": self.from_index,
            "to_index": self.to_index
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "TagMoveCommand":
        return cls(
            context=context,
            from_index=data["from_index"],
            to_index=data["to_index"]
        )

# --- Canvas Commands (Nodes/Edges/Groups) ---

@dataclass
class NodePositionCommand(Command):
    """Command for moving a node position."""
    context: Any
    node_id: str
    old_x: float
    old_y: float
    new_x: float
    new_y: float
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id) or \
                   self.context.scene._waypoints.get(self.node_id)
            if node:
                node.setPos(self.new_x, self.new_y)
                # Update node_data position
                node.node_data.position.x = self.new_x
                node.node_data.position.y = self.new_y
    
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id) or \
                   self.context.scene._waypoints.get(self.node_id)
            if node:
                node.setPos(self.old_x, self.old_y)
                node.node_data.position.x = self.old_x
                node.node_data.position.y = self.old_y
    
    def to_dict(self) -> dict:
        return {
            "type": "NodePosition",
            "node_id": self.node_id,
            "old_x": self.old_x,
            "old_y": self.old_y,
            "new_x": self.new_x,
            "new_y": self.new_y
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "NodePositionCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            old_x=data["old_x"],
            old_y=data["old_y"],
            new_x=data["new_x"],
            new_y=data["new_y"]
        )


# ============================================================================
# Snippet Commands (V3.9.0)
# ============================================================================

@dataclass
class SnippetAddCommand(Command):
    """Command for adding a snippet to a node."""
    context: Any
    node_id: str
    snippet_data: dict  # Serialized Snippet
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                node.add_snippet_internal(self.snippet_data)
    
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                snippet_id = self.snippet_data.get('id')
                node.remove_snippet_internal(snippet_id)
    
    def to_dict(self) -> dict:
        return {
            "type": "SnippetAdd",
            "node_id": self.node_id,
            "snippet_data": self.snippet_data
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "SnippetAddCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            snippet_data=data["snippet_data"]
        )


@dataclass
class SnippetRemoveCommand(Command):
    """Command for removing a snippet from a node."""
    context: Any
    node_id: str
    snippet_data: dict  # Serialized Snippet for restoration
    snippet_index: int  # Position in the list
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                snippet_id = self.snippet_data.get('id')
                node.remove_snippet_internal(snippet_id)
    
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                # Re-insert at original position using internal method variant
                from models import Snippet
                from graphics_items import SnippetItem
                snippet = Snippet.from_dict(self.snippet_data)
                idx = min(self.snippet_index, len(node.node_data.snippets))
                node.node_data.snippets.insert(idx, snippet)
                item = SnippetItem(snippet, node)
                node._snippet_items.insert(idx, item)
                node.update_layout()
    
    def to_dict(self) -> dict:
        return {
            "type": "SnippetRemove",
            "node_id": self.node_id,
            "snippet_data": self.snippet_data,
            "snippet_index": self.snippet_index
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "SnippetRemoveCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            snippet_data=data["snippet_data"],
            snippet_index=data["snippet_index"]
        )


@dataclass
class SnippetEditCommand(Command):
    """Command for editing snippet content or source label."""
    context: Any
    node_id: str
    snippet_id: str
    field: str  # "content" or "source_label"
    old_value: str
    new_value: str
    
    def execute(self) -> None:
        self._set_value(self.new_value)
    
    def undo(self) -> None:
        self._set_value(self.old_value)
    
    def _set_value(self, value: str) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                for item in node._snippet_items:
                    if item.snippet_data.id == self.snippet_id:
                        if self.field == "content":
                            item.snippet_data.content = value
                        elif self.field == "source_label":
                            item.snippet_data.source_label = value
                        item._update_geometry()
                        item.update()
                        break
                node.update_layout()
    
    def to_dict(self) -> dict:
        return {
            "type": "SnippetEdit",
            "node_id": self.node_id,
            "snippet_id": self.snippet_id,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "SnippetEditCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            snippet_id=data["snippet_id"],
            field=data["field"],
            old_value=data["old_value"],
            new_value=data["new_value"]
        )


@dataclass
class SnippetMoveCommand(Command):
    """Command for moving a snippet within a node's list."""
    context: Any
    node_id: str
    snippet_id: str
    from_index: int
    to_index: int
    
    def execute(self) -> None:
        self._move(self.from_index, self.to_index)
    
    def undo(self) -> None:
        self._move(self.to_index, self.from_index)
    
    def _move(self, from_idx: int, to_idx: int) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                node.move_snippet_internal(from_idx, to_idx)
    
    def to_dict(self) -> dict:
        return {
            "type": "SnippetMove",
            "node_id": self.node_id,
            "snippet_id": self.snippet_id,
            "from_index": self.from_index,
            "to_index": self.to_index
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "SnippetMoveCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            snippet_id=data["snippet_id"],
            from_index=data["from_index"],
            to_index=data["to_index"]
        )


@dataclass
class NodeMetadataEditCommand(Command):
    """Command for editing node metadata (title, year, conference, module_name)."""
    context: Any
    node_id: str
    field: str  # "title", "year", "conference", "module_name"
    old_value: str
    new_value: str
    
    def execute(self) -> None:
        self._set_value(self.new_value)
    
    def undo(self) -> None:
        self._set_value(self.old_value)
    
    def _set_value(self, value: str) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                setattr(node.node_data.metadata, self.field, value)
                node.update()
    
    def to_dict(self) -> dict:
        return {
            "type": "NodeMetadataEdit",
            "node_id": self.node_id,
            "field": self.field,
            "old_value": self.old_value,
            "new_value": self.new_value
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "NodeMetadataEditCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            field=data["field"],
            old_value=data["old_value"],
            new_value=data["new_value"]
        )

@dataclass
class AddNodeCommand(Command):
    """Command for adding a node or waypoint."""
    context: Any
    node_data_dict: dict  # Serialized NodeData
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            from models import NodeData
            node_data = NodeData.from_dict(self.node_data_dict)
            self.context.scene.restore_node(node_data)
            
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
            self.context.scene._is_undo_operation = True
            try:
                node_id = self.node_data_dict['id']
                if node_id in self.context.scene._nodes:
                    self.context.scene._remove_node_internal(node_id)
                elif node_id in self.context.scene._waypoints:
                    self.context.scene._remove_waypoint_internal(node_id)
            finally:
                self.context.scene._is_undo_operation = False
            
    def to_dict(self) -> dict:
        return {
            "type": "AddNode",
            "node_data_dict": self.node_data_dict
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "AddNodeCommand":
        return cls(
            context=context,
            node_data_dict=data["node_data_dict"]
        )

@dataclass
class RemoveNodeCommand(Command):
    """Command for removing a node (and its connected edges)."""
    context: Any
    node_data_dict: dict
    connected_edges: list[dict] # List of serialized EdgeData
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            self.context.scene._is_undo_operation = True
            try:
                node_id = self.node_data_dict['id']
                if node_id in self.context.scene._nodes:
                    self.context.scene._remove_node_internal(node_id)
                elif node_id in self.context.scene._waypoints:
                    self.context.scene._remove_waypoint_internal(node_id)
            finally:
                self.context.scene._is_undo_operation = False
            
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
            from models import NodeData, EdgeData
            # Restore node
            node_data = NodeData.from_dict(self.node_data_dict)
            self.context.scene.restore_node(node_data)
            # Restore edges
            for edge_dict in self.connected_edges:
                edge_data = EdgeData.from_dict(edge_dict)
                self.context.scene.restore_edge(edge_data)
                
    def to_dict(self) -> dict:
        return {
            "type": "RemoveNode",
            "node_data_dict": self.node_data_dict,
            "connected_edges": self.connected_edges
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "RemoveNodeCommand":
        return cls(
            context=context,
            node_data_dict=data["node_data_dict"],
            connected_edges=data["connected_edges"]
        )

@dataclass
class AddEdgeCommand(Command):
    """Command for adding a connection.
    For Reference→Pipeline connections, also handles cloned snippets.
    Stores both snippet IDs and their full data for undo/redo.
    """
    context: Any
    edge_data_dict: dict
    target_node_id: str = ""  # Node that received cloned snippets
    cloned_snippet_ids: list = field(default_factory=list)  # IDs of cloned snippets
    cloned_snippet_data: list = field(default_factory=list)  # Full snippet data for redo
    _first_execute: bool = True
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            from models import EdgeData
            edge_data = EdgeData.from_dict(self.edge_data_dict)
            self.context.scene.restore_edge(edge_data)
            
            # On redo (not first execute), restore cloned snippets
            if not self._first_execute and self.target_node_id and self.cloned_snippet_data:
                node = self.context.scene._nodes.get(self.target_node_id)
                if node:
                    for snippet_dict in self.cloned_snippet_data:
                        node.add_snippet_internal(snippet_dict)
            
            self._first_execute = False
            
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
            self.context.scene._is_undo_operation = True
            try:
                # Capture snippet data before removing (for redo)
                if self.target_node_id and self.cloned_snippet_ids and not self.cloned_snippet_data:
                    node = self.context.scene._nodes.get(self.target_node_id)
                    if node:
                        for snippet in node.node_data.snippets:
                            if snippet.id in self.cloned_snippet_ids:
                                self.cloned_snippet_data.append(snippet.to_dict())
                
                # Remove edge
                self.context.scene._remove_edge_internal(self.edge_data_dict['id'])
                
                # Remove cloned snippets if any
                if self.target_node_id and self.cloned_snippet_ids:
                    node = self.context.scene._nodes.get(self.target_node_id)
                    if node:
                        for snippet_id in self.cloned_snippet_ids:
                            node.remove_snippet_internal(snippet_id)
            finally:
                self.context.scene._is_undo_operation = False

    def to_dict(self) -> dict:
        return {
            "type": "AddEdge",
            "edge_data_dict": self.edge_data_dict,
            "target_node_id": self.target_node_id,
            "cloned_snippet_ids": self.cloned_snippet_ids,
            "cloned_snippet_data": self.cloned_snippet_data
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "AddEdgeCommand":
        cmd = cls(
            context=context,
            edge_data_dict=data["edge_data_dict"],
            target_node_id=data.get("target_node_id", ""),
            cloned_snippet_ids=data.get("cloned_snippet_ids", []),
            cloned_snippet_data=data.get("cloned_snippet_data", [])
        )
        cmd._first_execute = False  # Loaded from file
        return cmd

@dataclass
class RemoveEdgeCommand(Command):
    """Command for removing an connection."""
    context: Any
    edge_data_dict: dict
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            self.context.scene._is_undo_operation = True
            try:
                self.context.scene._remove_edge_internal(self.edge_data_dict['id'])
            finally:
                self.context.scene._is_undo_operation = False
            
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
             from models import EdgeData
             edge_data = EdgeData.from_dict(self.edge_data_dict)
             self.context.scene.restore_edge(edge_data)

    def to_dict(self) -> dict:
        return {
            "type": "RemoveEdge",
            "edge_data_dict": self.edge_data_dict
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "RemoveEdgeCommand":
        return cls(
            context=context,
            edge_data_dict=data["edge_data_dict"]
        )

@dataclass
class AddGroupCommand(Command):
    """Command for adding a group."""
    context: Any
    group_data_dict: dict
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
             from models import GroupData
             group_data = GroupData.from_dict(self.group_data_dict)
             self.context.scene.restore_group(group_data)
             
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
            self.context.scene.remove_group(self.group_data_dict['id'])

    def to_dict(self) -> dict:
        return {
            "type": "AddGroup",
            "group_data_dict": self.group_data_dict
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "AddGroupCommand":
        return cls(
            context=context,
            group_data_dict=data["group_data_dict"]
        )

@dataclass
class RemoveGroupCommand(Command):
    """Command for removing a group."""
    context: Any
    group_data_dict: dict
    
    def execute(self) -> None:
        if hasattr(self.context, 'scene'):
            self.context.scene.remove_group(self.group_data_dict['id'])
            
    def undo(self) -> None:
        if hasattr(self.context, 'scene'):
             from models import GroupData
             group_data = GroupData.from_dict(self.group_data_dict)
             self.context.scene.restore_group(group_data)

    def to_dict(self) -> dict:
        return {
            "type": "RemoveGroup",
            "group_data_dict": self.group_data_dict
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "RemoveGroupCommand":
        return cls(
            context=context,
            group_data_dict=data["group_data_dict"]
        )

@dataclass
class GroupMoveCommand(Command):
    """Command for moving a group (and its children)."""
    context: Any
    group_id: str
    old_pos: tuple[float, float]
    new_pos: tuple[float, float]
    child_positions: dict = None  # {node_id: (old_x, old_y)} - captured at creation
    _first_execute: bool = True  # Skip child move on first execute (drag already moved them)
    
    def __post_init__(self):
        # Capture child positions at command creation (before any undo/redo)
        if self.child_positions is None and hasattr(self.context, 'scene'):
            self.child_positions = {}
            group = self.context.scene._groups.get(self.group_id)
            if group:
                dx = self.new_pos[0] - self.old_pos[0]
                dy = self.new_pos[1] - self.old_pos[1]
                for node_id in group.group_data.node_ids:
                    node = self.context.scene._nodes.get(node_id) or \
                           self.context.scene._waypoints.get(node_id)
                    if node:
                        # Store old position (before drag)
                        self.child_positions[node_id] = (
                            node.pos().x() - dx,  # Subtract delta to get old pos
                            node.pos().y() - dy
                        )
    
    def execute(self) -> None:
        # First execute: nodes already moved by drag, just skip
        if self._first_execute:
            self._first_execute = False
            return
        # Subsequent executes (redo): need to actually move
        self._move_to(self.new_pos)

    def undo(self) -> None:
        self._move_to(self.old_pos)
    
    def _move_to(self, target_pos: tuple) -> None:
        if hasattr(self.context, 'scene'):
            group = self.context.scene._groups.get(self.group_id)
            if group:
                from PyQt6.QtCore import QPointF
                # Move group
                group.setPos(QPointF(target_pos[0], target_pos[1]))
                group.group_data.position.x = target_pos[0]
                group.group_data.position.y = target_pos[1]
                
                # Calculate target child positions
                dx = target_pos[0] - self.old_pos[0]
                dy = target_pos[1] - self.old_pos[1]
                
                # Move contained nodes to their target positions
                for node_id, (old_x, old_y) in (self.child_positions or {}).items():
                    node = self.context.scene._nodes.get(node_id) or \
                           self.context.scene._waypoints.get(node_id)
                    if node:
                        target_x = old_x + dx
                        target_y = old_y + dy
                        node.setPos(target_x, target_y)
                        node.node_data.position.x = target_x
                        node.node_data.position.y = target_y

    def to_dict(self) -> dict:
        return {
            "type": "GroupMove",
            "group_id": self.group_id,
            "old_pos": self.old_pos,
            "new_pos": self.new_pos,
            "child_positions": self.child_positions
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "GroupMoveCommand":
        cmd = cls(
            context=context,
            group_id=data["group_id"],
            old_pos=tuple(data["old_pos"]),
            new_pos=tuple(data["new_pos"]),
            child_positions=data.get("child_positions", {})
        )
        cmd._first_execute = False  # Loaded from file, must always apply
        return cmd

@dataclass
class NodeGroupChangeCommand(Command):
    """Command for adding/removing a node from a group."""
    context: Any
    node_id: str
    old_group_id: Optional[str]  # None if node wasn't in any group
    new_group_id: Optional[str]  # None if removing from group
    
    def execute(self) -> None:
        self._apply_grouping(self.old_group_id, self.new_group_id)

    def undo(self) -> None:
        self._apply_grouping(self.new_group_id, self.old_group_id)
    
    def _apply_grouping(self, from_group_id: Optional[str], to_group_id: Optional[str]) -> None:
        if hasattr(self.context, 'scene'):
            # Remove from old group
            if from_group_id:
                old_group = self.context.scene._groups.get(from_group_id)
                if old_group and self.node_id in old_group.group_data.node_ids:
                    old_group.group_data.node_ids.remove(self.node_id)
            
            # Add to new group
            if to_group_id:
                new_group = self.context.scene._groups.get(to_group_id)
                if new_group and self.node_id not in new_group.group_data.node_ids:
                    new_group.group_data.node_ids.append(self.node_id)
            
            # Update node visual
            node = self.context.scene._nodes.get(self.node_id) or \
                   self.context.scene._waypoints.get(self.node_id)
            if node:
                if to_group_id:
                    new_group = self.context.scene._groups.get(to_group_id)
                    if new_group:
                        node.set_group_color(new_group.group_data.color)
                else:
                    node.set_group_color(None)

    def to_dict(self) -> dict:
        return {
            "type": "NodeGroupChange",
            "node_id": self.node_id,
            "old_group_id": self.old_group_id,
            "new_group_id": self.new_group_id
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "NodeGroupChangeCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            old_group_id=data.get("old_group_id"),
            new_group_id=data.get("new_group_id")
        )


@dataclass
class GroupNameEditCommand(Command):
    """Command for editing group name."""
    context: Any
    group_id: str
    old_name: str
    new_name: str
    
    def execute(self) -> None:
        self._set_name(self.new_name)
    
    def undo(self) -> None:
        self._set_name(self.old_name)
    
    def _set_name(self, name: str) -> None:
        if hasattr(self.context, 'scene'):
            group = self.context.scene._groups.get(self.group_id)
            if group:
                group.group_data.name = name
                group.update()
    
    def to_dict(self) -> dict:
        return {
            "type": "GroupNameEdit",
            "group_id": self.group_id,
            "old_name": self.old_name,
            "new_name": self.new_name
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "GroupNameEditCommand":
        return cls(
            context=context,
            group_id=data["group_id"],
            old_name=data["old_name"],
            new_name=data["new_name"]
        )


@dataclass
class GroupSizeCommand(Command):
    """Command for resizing a group."""
    context: Any
    group_id: str
    old_rect: tuple  # (x, y, width, height) in scene coords
    new_rect: tuple
    
    def execute(self) -> None:
        self._apply_rect(self.new_rect)
    
    def undo(self) -> None:
        self._apply_rect(self.old_rect)
    
    def _apply_rect(self, rect: tuple) -> None:
        if hasattr(self.context, 'scene'):
            group = self.context.scene._groups.get(self.group_id)
            if group:
                x, y, w, h = rect
                group.setPos(x, y)
                group.setRect(0, 0, w, h)
                group.group_data.position.x = x
                group.group_data.position.y = y
                group.group_data.width = w
                group.group_data.height = h
                group.update()
    
    def to_dict(self) -> dict:
        return {
            "type": "GroupSize",
            "group_id": self.group_id,
            "old_rect": list(self.old_rect),
            "new_rect": list(self.new_rect)
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "GroupSizeCommand":
        return cls(
            context=context,
            group_id=data["group_id"],
            old_rect=tuple(data["old_rect"]),
            new_rect=tuple(data["new_rect"])
        )

@dataclass
class NodeTagToggleCommand(Command):
    """Command for adding/removing a tag from a node."""
    context: Any
    node_id: str
    tag_name: str
    was_added: bool  # True if tag was added, False if removed
    
    def execute(self) -> None:
        self._apply_toggle(add=self.was_added)
    
    def undo(self) -> None:
        self._apply_toggle(add=not self.was_added)
    
    def _apply_toggle(self, add: bool) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                if add:
                    node.add_tag_internal(self.tag_name)
                else:
                    node.remove_tag_internal(self.tag_name)
    
    def to_dict(self) -> dict:
        return {
            "type": "NodeTagToggle",
            "node_id": self.node_id,
            "tag_name": self.tag_name,
            "was_added": self.was_added
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "NodeTagToggleCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            tag_name=data["tag_name"],
            was_added=data["was_added"]
        )


@dataclass
class NodeFlagToggleCommand(Command):
    """Command for toggling node flag state."""
    context: Any
    node_id: str
    new_state: bool  # The state after toggle
    
    def execute(self) -> None:
        self._set_flag(self.new_state)
    
    def undo(self) -> None:
        self._set_flag(not self.new_state)
    
    def _set_flag(self, flagged: bool) -> None:
        if hasattr(self.context, 'scene'):
            node = self.context.scene._nodes.get(self.node_id)
            if node:
                node.set_flag_internal(flagged)
    
    def to_dict(self) -> dict:
        return {
            "type": "NodeFlagToggle",
            "node_id": self.node_id,
            "new_state": self.new_state
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "NodeFlagToggleCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            new_state=data["new_state"]
        )


@dataclass
class NodeLockToggleCommand(Command):
    """Command for toggling node lock state."""
    context: Any
    node_id: str
    new_state: bool  # The state after toggle
    is_group: bool = False  # True if this is a group, not a node
    
    def execute(self) -> None:
        self._set_lock(self.new_state)
    
    def undo(self) -> None:
        self._set_lock(not self.new_state)
    
    def _set_lock(self, locked: bool) -> None:
        if hasattr(self.context, 'scene'):
            if self.is_group:
                group = self.context.scene._groups.get(self.node_id)
                if group:
                    group.set_lock_internal(locked)
            else:
                node = self.context.scene._nodes.get(self.node_id)
                if not node:
                    node = self.context.scene._waypoints.get(self.node_id)
                if node:
                    node.set_lock_internal(locked)
    
    def to_dict(self) -> dict:
        return {
            "type": "NodeLockToggle",
            "node_id": self.node_id,
            "new_state": self.new_state,
            "is_group": self.is_group
        }
    
    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "NodeLockToggleCommand":
        return cls(
            context=context,
            node_id=data["node_id"],
            new_state=data["new_state"],
            is_group=data.get("is_group", False)
        )


@dataclass
class GlobalEdgeColorChangeCommand(Command):
    """Command for changing global edge colors."""
    context: Any
    old_pipeline_color: str
    old_reference_color: str
    new_pipeline_color: str
    new_reference_color: str
    
    def execute(self) -> None:
        self._apply_colors(self.new_pipeline_color, self.new_reference_color)

    def undo(self) -> None:
        self._apply_colors(self.old_pipeline_color, self.old_reference_color)
    
    def _apply_colors(self, pipeline: str, reference: str) -> None:
        # Update project data
        if hasattr(self.context, 'project_manager') and self.context.project_manager.is_project_open:
            self.context.project_manager.project_data.pipeline_edge_color = pipeline
            self.context.project_manager.project_data.reference_edge_color = reference
        # Update dock widget (without emitting signal)
        if hasattr(self.context, 'project_dock'):
            self.context.project_dock.set_edge_colors(pipeline, reference)
        # Update scene
        if hasattr(self.context, 'scene'):
            self.context.scene.set_edge_colors(pipeline, reference)
        # Update waypoint palette color
        if hasattr(self.context, 'module_palette'):
            self.context.module_palette.waypoint_item.set_color(pipeline)

    def to_dict(self) -> dict:
        return {
            "type": "GlobalEdgeColorChange",
            "old_pipeline_color": self.old_pipeline_color,
            "old_reference_color": self.old_reference_color,
            "new_pipeline_color": self.new_pipeline_color,
            "new_reference_color": self.new_reference_color
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "GlobalEdgeColorChangeCommand":
        return cls(
            context=context,
            old_pipeline_color=data["old_pipeline_color"],
            old_reference_color=data["old_reference_color"],
            new_pipeline_color=data["new_pipeline_color"],
            new_reference_color=data["new_reference_color"]
        )

@dataclass
class ModulePaletteColorChangeCommand(Command):
    """Command for changing module palette colors."""
    context: Any
    module_type: str
    old_color: str
    new_color: str
    
    def execute(self) -> None:
        # 1. Update Project Data
        if hasattr(self.context, 'project_manager') and self.context.project_manager.is_project_open:
            self.context.project_manager.project_data.module_colors[self.module_type] = self.new_color
            
        # 2. Update Palette (this will emit signal)
        if hasattr(self.context, 'module_palette'):
            self.context.module_palette.set_color_for_type(self.module_type, self.new_color)
            
        # 3. Update existing nodes in Scene
        if hasattr(self.context, 'scene'):
            # Update existing groups
            if self.module_type == "group":
                for group in self.context.scene._groups.values():
                    group.set_color(self.new_color)
            elif self.module_type == "waypoint":
                # Waypoints usually follow pipeline color, but if we support custom waypoint palette color:
                # Actually main.py synced waypoint color with pipeline color.
                # If module_type is specific to waypoint palette item?
                pass
            
            # Update pipeline modules
            from graphics_items import PipelineModuleItem
            for node in self.context.scene._nodes.values():
                if isinstance(node, PipelineModuleItem) and node.module_type == self.module_type:
                    node.set_color(self.new_color)
            
    def undo(self) -> None:
        # 1. Update Project Data
        if hasattr(self.context, 'project_manager') and self.context.project_manager.is_project_open:
            self.context.project_manager.project_data.module_colors[self.module_type] = self.old_color

        # 2. Update Palette
        if hasattr(self.context, 'module_palette'):
            self.context.module_palette.set_color_for_type(self.module_type, self.old_color)
            
        # 3. Update Scene
        if hasattr(self.context, 'scene'):
            if self.module_type == "group":
                for group in self.context.scene._groups.values():
                    group.set_color(self.old_color)
            
            from graphics_items import PipelineModuleItem
            for node in self.context.scene._nodes.values():
                if isinstance(node, PipelineModuleItem) and node.module_type == self.module_type:
                    node.set_color(self.old_color)

    def to_dict(self) -> dict:
        return {
            "type": "ModulePaletteColorChange",
            "module_type": self.module_type,
            "old_color": self.old_color,
            "new_color": self.new_color
        }

    @classmethod
    def from_dict(cls, data: dict, context: Any) -> "ModulePaletteColorChangeCommand":
        return cls(
            context=context,
            module_type=data["module_type"],
            old_color=data["old_color"],
            new_color=data["new_color"]
        )

class UndoManager:
    """
    Manages undo/redo stacks with persistence.
    Stores up to MAX_HISTORY commands.
    """
    
    MAX_HISTORY = 100
    HISTORY_FILENAME = "undo_history.json"
    
    def __init__(self, context: Any = None):
        self.context = context
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._is_undoing = False  # V3.9.0: Flag to prevent recording during undo/redo
    
    def execute(self, command: Command) -> None:
        """Execute a command and add to undo stack."""
        # V3.9.0: Don't record commands if we're in the middle of undo/redo
        if self._is_undoing:
            return
        
        # V4.1.0: Try to merge with previous command (for text input batching)
        if self._undo_stack:
            last_cmd = self._undo_stack[-1]
            if (hasattr(last_cmd, 'can_merge_with') and 
                hasattr(last_cmd, 'merge_with') and
                last_cmd.can_merge_with(command)):
                # Merge: don't execute, just update the last command
                last_cmd.merge_with(command)
                # Apply the new value directly
                if hasattr(command, 'new_value') and hasattr(self.context, 'project_dock'):
                    self.context.project_dock.set_description_no_cursor_reset(command.new_value)
                    if hasattr(self.context, 'project_manager') and self.context.project_manager.is_project_open:
                        self.context.project_manager.project_data.description = command.new_value
                self._save_history_if_possible()
                return
        
        command.execute()
        self._undo_stack.append(command)
        
        # Limit stack size
        if len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.pop(0)
        
        # Clear redo stack on new action
        self._redo_stack.clear()
        
        # Trigger autosave of history if possible
        self._save_history_if_possible()
    
    def undo(self) -> bool:
        """Undo the last command. Returns True if successful."""
        if not self._undo_stack:
            return False
        
        self._is_undoing = True
        try:
            command = self._undo_stack.pop()
            command.undo()
            self._redo_stack.append(command)
        finally:
            self._is_undoing = False
        
        self._save_history_if_possible()
        return True
    
    def redo(self) -> bool:
        """Redo the last undone command. Returns True if successful."""
        if not self._redo_stack:
            return False
        
        self._is_undoing = True
        try:
            command = self._redo_stack.pop()
            command.execute()
            self._undo_stack.append(command)
        finally:
            self._is_undoing = False
        
        self._save_history_if_possible()
        return True
    
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0
    
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0
    
    def clear(self) -> None:
        """Clear all history."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        
    def _save_history_if_possible(self):
        # Helper to trigger save
        if hasattr(self.context, 'project_manager') and self.context.project_manager.is_project_open:
            self.save_to_file(self.context.project_manager.current_project_path)
    
    def save_to_file(self, project_path: Path) -> None:
        """Save undo history to project directory."""
        history_file = project_path / self.HISTORY_FILENAME
        
        data = {
            "undo_stack": [cmd.to_dict() for cmd in self._undo_stack],
            "redo_stack": [cmd.to_dict() for cmd in self._redo_stack]
        }
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save undo history: {e}")
    
    def load_from_file(self, project_path: Path) -> None:
        """Load undo history from project directory."""
        history_file = project_path / self.HISTORY_FILENAME
        
        if not history_file.exists():
            self.clear()  # Start fresh if no history file
            return
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Deserialize undo stack (only once per command)
            self._undo_stack = []
            for cmd_data in data.get("undo_stack", []):
                cmd = self._deserialize_command(cmd_data)
                if cmd is not None:
                    self._undo_stack.append(cmd)
            
            # Deserialize redo stack (only once per command)
            self._redo_stack = []
            for cmd_data in data.get("redo_stack", []):
                cmd = self._deserialize_command(cmd_data)
                if cmd is not None:
                    self._redo_stack.append(cmd)
                    
        except Exception as e:
            print(f"Warning: Could not load undo history: {e}")
            self.clear()  # Clear on error to prevent corruption
    
    def _deserialize_command(self, data: dict) -> Optional[Command]:
        """Deserialize a command from dict."""
        cmd_type = data.get("type")
        
        command_classes = {
            "DescriptionChange": DescriptionChangeCommand,
            "TodoAdd": TodoAddCommand,
            "TodoRemove": TodoRemoveCommand,
            "TodoEdit": TodoEditCommand,
            "TodoToggle": TodoToggleCommand,
            "TodoMove": TodoMoveCommand,
            "TagAdd": TagAddCommand,
            "TagRemove": TagRemoveCommand,
            "TagRename": TagRenameCommand,
            "TagColorChange": TagColorChangeCommand,
            "TagMove": TagMoveCommand,
            "NodePosition": NodePositionCommand,
            "AddNode": AddNodeCommand,
            "RemoveNode": RemoveNodeCommand,
            "AddEdge": AddEdgeCommand,
            "RemoveEdge": RemoveEdgeCommand,
            "AddGroup": AddGroupCommand,
            "RemoveGroup": RemoveGroupCommand,
            "GroupMove": GroupMoveCommand,
            "NodeGroupChange": NodeGroupChangeCommand,
            "GlobalEdgeColorChange": GlobalEdgeColorChangeCommand,
            "ModulePaletteColorChange": ModulePaletteColorChangeCommand,
            # Snippet commands
            "SnippetAdd": SnippetAddCommand,
            "SnippetRemove": SnippetRemoveCommand,
            "SnippetEdit": SnippetEditCommand,
            "SnippetMove": SnippetMoveCommand,
            # Node metadata edit
            "NodeMetadataEdit": NodeMetadataEditCommand,
            # Group and tag
            "GroupNameEdit": GroupNameEditCommand,
            "GroupSize": GroupSizeCommand,
            "NodeTagToggle": NodeTagToggleCommand,
            # Flag and lock
            "NodeFlagToggle": NodeFlagToggleCommand,
            "NodeLockToggle": NodeLockToggleCommand
        }
        
        cls = command_classes.get(cmd_type)
        if cls:
            try:
                return cls.from_dict(data, self.context)
            except Exception:
                return None
        return None
