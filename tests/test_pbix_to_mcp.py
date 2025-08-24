"""Tests for PBIX to MCP converter package."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from pbix_to_mcp import PBIXConverter
from pbix_to_mcp.utils import FileManager, setup_logger


class TestFileManager:
    """Test file management utilities."""

    def test_file_manager_init(self):
        """Test FileManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager(Path(temp_dir))
            assert fm.output_dir == Path(temp_dir)
            assert fm.output_dir.exists()

    def test_save_and_load_json(self):
        """Test JSON save and load operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager(Path(temp_dir))

            test_data = {"test": "data", "number": 42}
            file_path = fm.save_json(test_data, "test.json")

            assert file_path.exists()
            loaded_data = fm.load_json("test.json")
            assert loaded_data == test_data

    def test_save_and_load_text(self):
        """Test text save and load operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fm = FileManager(Path(temp_dir))

            test_content = "Hello, World!\nThis is a test."
            file_path = fm.save_text(test_content, "test.txt")

            assert file_path.exists()
            loaded_content = fm.load_text("test.txt")
            assert loaded_content == test_content


class TestPBIXConverter:
    """Test main converter functionality."""

    @patch("pbix_to_mcp.core.DataExtractor")
    @patch("pbix_to_mcp.core.UIExtractor")
    @patch("pbix_to_mcp.core.DAXExtractor")
    def test_converter_init(self, mock_dax, mock_ui, mock_data):
        """Test PBIXConverter initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a dummy PBIX file
            pbix_file = Path(temp_dir) / "test.pbix"
            pbix_file.write_text("dummy content")

            converter = PBIXConverter(str(pbix_file))

            assert converter.pbix_path == pbix_file
            assert converter.pbix_name == "test"
            assert converter.output_dir.name == "test_mcp"

    @patch("pbix_to_mcp.core.DataExtractor")
    @patch("pbix_to_mcp.core.UIExtractor")
    @patch("pbix_to_mcp.core.DAXExtractor")
    @patch("pbix_to_mcp.core.SQLiteGenerator")
    def test_extract_all(self, mock_sqlite, mock_dax, mock_ui, mock_data):
        """Test complete extraction process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a dummy PBIX file
            pbix_file = Path(temp_dir) / "test.pbix"
            pbix_file.write_text("dummy content")

            # Mock extractor responses
            mock_data_instance = mock_data.return_value
            mock_data_instance.extract_data_model.return_value = {
                "tables": [{"name": "TestTable", "columns": []}],
                "relationships": [],
                "metadata": {},
            }

            mock_ui_instance = mock_ui.return_value
            mock_ui_instance.extract_ui_structure.return_value = {
                "pages": [{"name": "Page1"}],
                "visualizations": [],
            }

            mock_dax_instance = mock_dax.return_value
            mock_dax_instance.extract_all_dax.return_value = {
                "measures": [{"name": "TestMeasure"}],
                "calculated_columns": [],
            }

            mock_sqlite_instance = mock_sqlite.return_value
            mock_sqlite_instance.create_database.return_value = Path(temp_dir) / "test.db"

            converter = PBIXConverter(str(pbix_file), temp_dir)
            results = converter.extract_all()

            assert "data_model" in results
            assert "ui_structure" in results
            assert "dax_expressions" in results
            assert results["extraction_summary"]["data_model"] == "✅ Complete"


def test_logger_setup():
    """Test logger setup functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = Path(temp_dir) / "test.log"
        logger = setup_logger("test_logger", log_file)

        logger.info("Test message")

        assert log_file.exists()
        log_content = log_file.read_text()
        assert "Test message" in log_content


if __name__ == "__main__":
    pytest.main([__file__])
