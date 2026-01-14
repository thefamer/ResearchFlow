"""
ResearchFlow - Data Models
Dataclasses for project data serialization/deserialization.
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid
import json


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


@dataclass
class Snippet:
    """
    Represents a content snippet attached to a node.
    Can be either text or an image.
    """
    id: str = field(default_factory=generate_uuid)
    type: str = "text"  # "text" or "image"
    content: str = ""   # Text content or relative path to image
    source_label: str = ""  # Attribution label, e.g., "From: Paper Title"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "source_label": self.source_label
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Snippet":
        return cls(
            id=data.get("id", generate_uuid()),
            type=data.get("type", "text"),
            content=data.get("content", ""),
            source_label=data.get("source_label", "")
        )
    
    def deep_copy(self, source_title: str = "") -> "Snippet":
        """Create an independent copy with a new UUID and source attribution."""
        return Snippet(
            id=generate_uuid(),
            type=self.type,
            content=self.content,
            source_label=f"From: {source_title}" if source_title else self.source_label
        )


@dataclass
class Position:
    """2D position on the canvas."""
    x: float = 0.0
    y: float = 0.0
    
    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}
    
    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        return cls(x=data.get("x", 0.0), y=data.get("y", 0.0))


@dataclass
class NodeMetadata:
    """
    Metadata for nodes. Fields vary by node type.
    - For reference_paper: title, year, conference, relative_path_to_md
    - For pipeline_module: module_name, module_type
    """
    # Reference paper fields
    title: str = ""
    year: str = ""
    conference: str = ""
    relative_path_to_md: str = ""
    
    # Pipeline module fields
    module_name: str = ""
    module_type: str = ""  # "input", "output", "process", "decision"
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "year": self.year,
            "conference": self.conference,
            "relative_path_to_md": self.relative_path_to_md,
            "module_name": self.module_name,
            "module_type": self.module_type
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NodeMetadata":
        return cls(
            title=data.get("title", ""),
            year=data.get("year", ""),
            conference=data.get("conference", ""),
            relative_path_to_md=data.get("relative_path_to_md", ""),
            module_name=data.get("module_name", ""),
            module_type=data.get("module_type", "")
        )


@dataclass
class NodeData:
    """
    Represents a node in the graph.
    Can be either a pipeline_module or reference_paper.
    """
    id: str = field(default_factory=generate_uuid)
    type: str = "pipeline_module"  # "pipeline_module" or "reference_paper"
    position: Position = field(default_factory=Position)
    tags: list[str] = field(default_factory=list)
    metadata: NodeMetadata = field(default_factory=NodeMetadata)
    snippets: list[Snippet] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "position": self.position.to_dict(),
            "tags": self.tags.copy(),
            "metadata": self.metadata.to_dict(),
            "snippets": [s.to_dict() for s in self.snippets]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "NodeData":
        return cls(
            id=data.get("id", generate_uuid()),
            type=data.get("type", "pipeline_module"),
            position=Position.from_dict(data.get("position", {})),
            tags=data.get("tags", []).copy(),
            metadata=NodeMetadata.from_dict(data.get("metadata", {})),
            snippets=[Snippet.from_dict(s) for s in data.get("snippets", [])]
        )


@dataclass
class EdgeData:
    """Represents an edge (connection) between two nodes."""
    id: str = field(default_factory=generate_uuid)
    source_id: str = ""
    target_id: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EdgeData":
        return cls(
            id=data.get("id", generate_uuid()),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", "")
        )


@dataclass
class ProjectData:
    """
    Complete project state including all nodes, edges, and tags.
    Serialized to project_data.json.
    """
    global_tags: list[str] = field(default_factory=list)
    nodes: list[NodeData] = field(default_factory=list)
    edges: list[EdgeData] = field(default_factory=list)
    pipeline_initialized: bool = False
    
    def to_dict(self) -> dict:
        return {
            "global_tags": self.global_tags.copy(),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "pipeline_initialized": self.pipeline_initialized
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ProjectData":
        return cls(
            global_tags=data.get("global_tags", []).copy(),
            nodes=[NodeData.from_dict(n) for n in data.get("nodes", [])],
            edges=[EdgeData.from_dict(e) for e in data.get("edges", [])],
            pipeline_initialized=data.get("pipeline_initialized", False)
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ProjectData":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def get_node_by_id(self, node_id: str) -> Optional[NodeData]:
        """Find a node by its ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edges_for_node(self, node_id: str) -> list[EdgeData]:
        """Get all edges connected to a node."""
        return [e for e in self.edges if e.source_id == node_id or e.target_id == node_id]
    
    def has_pipeline_module(self) -> bool:
        """Check if any pipeline module exists."""
        return any(n.type == "pipeline_module" for n in self.nodes)
