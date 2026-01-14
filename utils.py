"""
ResearchFlow - Utility Functions and Project Manager
Handles file operations, project management, and asset copying.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from models import ProjectData


def get_app_root() -> Path:
    """Get the application root directory."""
    return Path(__file__).parent.resolve()


def get_projects_dir() -> Path:
    """Get the projects directory path."""
    return get_app_root() / "projects"


def ensure_directory(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)


def sanitize_project_name(name: str) -> str:
    """Convert project name to a valid directory name."""
    # Replace spaces with underscores and remove invalid characters
    valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    sanitized = name.replace(" ", "_")
    sanitized = "".join(c for c in sanitized if c in valid_chars)
    return sanitized or "Untitled_Project"


class ProjectManager:
    """
    Manages project lifecycle: creation, loading, saving.
    Ensures all data stays within the application folder.
    """
    
    def __init__(self):
        self.current_project_name: Optional[str] = None
        self.current_project_path: Optional[Path] = None
        self.project_data: Optional[ProjectData] = None
        
        # Ensure projects directory exists
        ensure_directory(get_projects_dir())
    
    @property
    def is_project_open(self) -> bool:
        return self.current_project_path is not None
    
    @property
    def assets_path(self) -> Optional[Path]:
        """Get the assets directory for the current project."""
        if self.current_project_path:
            return self.current_project_path / "assets"
        return None
    
    @property
    def papers_path(self) -> Optional[Path]:
        """Get the papers directory for the current project."""
        if self.assets_path:
            return self.assets_path / "papers"
        return None
    
    @property
    def images_path(self) -> Optional[Path]:
        """Get the images directory for the current project."""
        if self.assets_path:
            return self.assets_path / "images"
        return None
    
    def list_existing_projects(self) -> list[str]:
        """List all existing project names in the projects directory."""
        projects_dir = get_projects_dir()
        if not projects_dir.exists():
            return []
        
        projects = []
        for item in projects_dir.iterdir():
            if item.is_dir():
                # Check if it has a project_data.json file
                if (item / "project_data.json").exists():
                    projects.append(item.name)
        return sorted(projects)
    
    def create_project(self, name: str) -> bool:
        """
        Create a new project with the given name.
        Returns True if successful, False if project already exists.
        """
        sanitized_name = sanitize_project_name(name)
        project_path = get_projects_dir() / sanitized_name
        
        if project_path.exists():
            return False
        
        # Create project structure
        ensure_directory(project_path)
        ensure_directory(project_path / "assets" / "papers")
        ensure_directory(project_path / "assets" / "images")
        
        # Initialize empty project data
        self.current_project_name = sanitized_name
        self.current_project_path = project_path
        self.project_data = ProjectData()
        
        # Save initial project data
        self.save_project()
        
        return True
    
    def open_project(self, name: str) -> bool:
        """
        Open an existing project by name.
        Returns True if successful, False if project doesn't exist.
        """
        project_path = get_projects_dir() / name
        data_file = project_path / "project_data.json"
        
        if not data_file.exists():
            return False
        
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                json_content = f.read()
            
            self.project_data = ProjectData.from_json(json_content)
            self.current_project_name = name
            self.current_project_path = project_path
            
            # Ensure asset directories exist
            ensure_directory(self.papers_path)
            ensure_directory(self.images_path)
            
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading project: {e}")
            return False
    
    def save_project(self) -> bool:
        """
        Save the current project state to disk.
        Returns True if successful.
        """
        if not self.is_project_open or self.project_data is None:
            return False
        
        data_file = self.current_project_path / "project_data.json"
        
        try:
            json_content = self.project_data.to_json(indent=2)
            with open(data_file, "w", encoding="utf-8") as f:
                f.write(json_content)
            return True
        except IOError as e:
            print(f"Error saving project: {e}")
            return False
    
    def close_project(self) -> None:
        """Close the current project."""
        self.current_project_name = None
        self.current_project_path = None
        self.project_data = None
    
    def copy_markdown_to_assets(self, source_path: str) -> Optional[str]:
        """
        Copy a markdown file to the project's assets/papers directory.
        Returns the relative path to the copied file, or None if failed.
        """
        if not self.is_project_open or not self.papers_path:
            return None
        
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            return None
        
        # Generate unique filename if needed
        dest_name = source.name
        dest_path = self.papers_path / dest_name
        
        # If file exists, add timestamp
        if dest_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = source.stem
            suffix = source.suffix
            dest_name = f"{stem}_{timestamp}{suffix}"
            dest_path = self.papers_path / dest_name
        
        try:
            shutil.copy2(source, dest_path)
            # Return relative path from project root
            return f"assets/papers/{dest_name}"
        except IOError as e:
            print(f"Error copying file: {e}")
            return None
    
    def copy_image_to_assets(self, source_path: str) -> Optional[str]:
        """
        Copy an image file to the project's assets/images directory.
        Returns the relative path to the copied file, or None if failed.
        """
        if not self.is_project_open or not self.images_path:
            return None
        
        source = Path(source_path)
        if not source.exists() or not source.is_file():
            return None
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = source.stem
        suffix = source.suffix
        dest_name = f"{stem}_{timestamp}{suffix}"
        dest_path = self.images_path / dest_name
        
        try:
            shutil.copy2(source, dest_path)
            return f"assets/images/{dest_name}"
        except IOError as e:
            print(f"Error copying image: {e}")
            return None
    
    def save_clipboard_image(self, image_data: bytes, extension: str = ".png") -> Optional[str]:
        """
        Save clipboard image data to the project's assets/images directory.
        Returns the relative path to the saved file, or None if failed.
        """
        if not self.is_project_open or not self.images_path:
            return None
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"clipboard_{timestamp}{extension}"
        dest_path = self.images_path / filename
        
        try:
            with open(dest_path, "wb") as f:
                f.write(image_data)
            return f"assets/images/{filename}"
        except IOError as e:
            print(f"Error saving clipboard image: {e}")
            return None
    
    def get_absolute_asset_path(self, relative_path: str) -> Optional[Path]:
        """Convert a relative asset path to an absolute path."""
        if not self.is_project_open:
            return None
        return self.current_project_path / relative_path
    
    def delete_project(self, name: str) -> bool:
        """
        Delete a project and all its contents.
        Returns True if successful.
        """
        project_path = get_projects_dir() / name
        
        if not project_path.exists():
            return False
        
        try:
            shutil.rmtree(project_path)
            return True
        except IOError as e:
            print(f"Error deleting project: {e}")
            return False


def extract_title_from_filename(filename: str) -> str:
    """Extract a readable title from a markdown filename."""
    # Remove extension
    name = Path(filename).stem
    # Replace underscores and hyphens with spaces
    name = name.replace("_", " ").replace("-", " ")
    # Title case
    return name.title()
