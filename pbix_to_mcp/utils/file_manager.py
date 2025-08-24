"""
File Manager Utility

Handles file operations for the PBIX to MCP conversion process.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Union


class FileManager:
    """
    Manages file operations for the conversion process.

    This class handles:
    - Saving JSON files
    - Saving text files
    - Managing output directories
    - File path validation
    """

    def __init__(self, output_dir: Path):
        """
        Initialize the file manager.

        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}")

    def save_json(self, data: Dict[str, Any], filename: str, subdir: str = None) -> Path:
        """
        Save data as JSON file.

        Args:
            data: Data to save
            filename: Name of the file
            subdir: Optional subdirectory

        Returns:
            Path to saved file
        """
        if subdir:
            save_dir = self.output_dir / subdir
            save_dir.mkdir(exist_ok=True)
        else:
            save_dir = self.output_dir

        file_path = save_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.debug(f"Saved JSON file: {file_path}")
            return file_path

        except Exception as e:
            self.logger.error(f"Failed to save JSON file {file_path}: {e}")
            raise

    def save_text(self, content: str, filename: str, subdir: str = None) -> Path:
        """
        Save text content to file.

        Args:
            content: Text content to save
            filename: Name of the file
            subdir: Optional subdirectory

        Returns:
            Path to saved file
        """
        if subdir:
            save_dir = self.output_dir / subdir
            save_dir.mkdir(exist_ok=True)
        else:
            save_dir = self.output_dir

        file_path = save_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.debug(f"Saved text file: {file_path}")
            return file_path

        except Exception as e:
            self.logger.error(f"Failed to save text file {file_path}: {e}")
            raise

    def load_json(self, filename: str, subdir: str = None) -> Dict[str, Any]:
        """
        Load JSON file.

        Args:
            filename: Name of the file
            subdir: Optional subdirectory

        Returns:
            Loaded data
        """
        if subdir:
            load_dir = self.output_dir / subdir
        else:
            load_dir = self.output_dir

        file_path = load_dir / filename

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.logger.debug(f"Loaded JSON file: {file_path}")
            return data

        except Exception as e:
            self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            raise

    def load_text(self, filename: str, subdir: str = None) -> str:
        """
        Load text file.

        Args:
            filename: Name of the file
            subdir: Optional subdirectory

        Returns:
            File content
        """
        if subdir:
            load_dir = self.output_dir / subdir
        else:
            load_dir = self.output_dir

        file_path = load_dir / filename

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.logger.debug(f"Loaded text file: {file_path}")
            return content

        except Exception as e:
            self.logger.error(f"Failed to load text file {file_path}: {e}")
            raise

    def ensure_dir(self, subdir: str) -> Path:
        """
        Ensure subdirectory exists.

        Args:
            subdir: Subdirectory name

        Returns:
            Path to directory
        """
        dir_path = self.output_dir / subdir
        dir_path.mkdir(exist_ok=True)
        return dir_path

    def list_files(self, pattern: str = "*", subdir: str = None) -> list[Path]:
        """
        List files matching pattern.

        Args:
            pattern: File pattern (glob)
            subdir: Optional subdirectory

        Returns:
            List of matching file paths
        """
        if subdir:
            search_dir = self.output_dir / subdir
        else:
            search_dir = self.output_dir

        if search_dir.exists():
            return list(search_dir.glob(pattern))
        else:
            return []

    def file_exists(self, filename: str, subdir: str = None) -> bool:
        """
        Check if file exists.

        Args:
            filename: Name of the file
            subdir: Optional subdirectory

        Returns:
            True if file exists
        """
        if subdir:
            check_dir = self.output_dir / subdir
        else:
            check_dir = self.output_dir

        file_path = check_dir / filename
        return file_path.exists()

    def get_file_path(self, filename: str, subdir: str = None) -> Path:
        """
        Get full file path.

        Args:
            filename: Name of the file
            subdir: Optional subdirectory

        Returns:
            Full file path
        """
        if subdir:
            file_dir = self.output_dir / subdir
        else:
            file_dir = self.output_dir

        return file_dir / filename

    def clean_directory(self, subdir: str = None, pattern: str = "*") -> int:
        """
        Clean files from directory.

        Args:
            subdir: Optional subdirectory (if None, cleans output_dir)
            pattern: File pattern to delete

        Returns:
            Number of files deleted
        """
        if subdir:
            clean_dir = self.output_dir / subdir
        else:
            clean_dir = self.output_dir

        deleted_count = 0

        if clean_dir.exists():
            for file_path in clean_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        self.logger.debug(f"Deleted file: {file_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not delete file {file_path}: {e}")

        return deleted_count
