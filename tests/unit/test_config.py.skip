"""
Unit tests for configuration management.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ocode_python.utils.config import DEFAULT_CONFIG, ConfigManager


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager functionality."""

    def test_init_default_config_dir(self):
        """Test initialization with default config directory."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path("/fake/home")
            manager = ConfigManager()
            assert manager.config_dir == Path("/fake/home/.ocode")

    def test_init_custom_config_dir(self, temp_dir: Path):
        """Test initialization with custom config directory."""
        manager = ConfigManager(temp_dir)
        assert manager.config_dir == temp_dir

    def test_ensure_config_dir_created(self, temp_dir: Path):
        """Test that config directory is created."""
        config_dir = temp_dir / "test_config"
        assert not config_dir.exists()

        manager = ConfigManager(config_dir)
        manager._ensure_config_dir()

        assert config_dir.exists()

    def test_get_default_config(self, temp_dir: Path):
        """Test getting default configuration."""
        manager = ConfigManager(temp_dir)
        config = manager.get_config()

        # Should return default config when no file exists
        assert config["model"] == DEFAULT_CONFIG["model"]
        assert config["temperature"] == DEFAULT_CONFIG["temperature"]

    def test_save_and_load_config(self, temp_dir: Path):
        """Test saving and loading configuration."""
        manager = ConfigManager(temp_dir)

        # Save custom config
        custom_config = {
            "model": "custom-model",
            "temperature": 0.8,
            "max_tokens": 2000,
            "custom_setting": "test_value",
        }

        success = manager.save_config(custom_config)
        assert success

        # Load config
        loaded_config = manager.get_config()

        assert loaded_config["model"] == "custom-model"
        assert loaded_config["temperature"] == 0.8
        assert loaded_config["custom_setting"] == "test_value"

    def test_get_setting(self, temp_dir: Path):
        """Test getting specific setting."""
        manager = ConfigManager(temp_dir)

        # Save config with custom setting
        config = {"test_key": "test_value", "nested": {"key": "value"}}
        manager.save_config(config)

        # Get specific settings
        assert manager.get_setting("test_key") == "test_value"
        assert manager.get_setting("nested.key") == "value"
        assert manager.get_setting("nonexistent") is None
        assert manager.get_setting("nonexistent", "default") == "default"

    def test_set_setting(self, temp_dir: Path):
        """Test setting specific setting."""
        manager = ConfigManager(temp_dir)

        # Set simple setting
        success = manager.set_setting("test_key", "test_value")
        assert success
        assert manager.get_setting("test_key") == "test_value"

        # Set nested setting
        success = manager.set_setting("nested.key", "nested_value")
        assert success
        assert manager.get_setting("nested.key") == "nested_value"

    def test_update_config(self, temp_dir: Path):
        """Test updating configuration."""
        manager = ConfigManager(temp_dir)

        # Save initial config
        initial_config = {"model": "initial", "temperature": 0.5}
        manager.save_config(initial_config)

        # Update with partial config
        updates = {"model": "updated", "new_setting": "new_value"}
        success = manager.update_config(updates)
        assert success

        # Verify updates
        config = manager.get_config()
        assert config["model"] == "updated"
        assert config["temperature"] == 0.5  # Should preserve existing
        assert config["new_setting"] == "new_value"

    def test_config_validation(self, temp_dir: Path):
        """Test configuration validation."""
        manager = ConfigManager(temp_dir)

        # Valid config
        valid_config = {"model": "valid-model", "temperature": 0.7, "max_tokens": 1000}
        assert manager._validate_config(valid_config)

        # Invalid temperature
        invalid_temp = {"temperature": 2.0}  # > 1.0
        assert not manager._validate_config(invalid_temp)

        # Invalid max_tokens
        invalid_tokens = {"max_tokens": 0}  # <= 0
        assert not manager._validate_config(invalid_tokens)

        # Invalid type
        invalid_type = {"model": 123}  # Should be string
        assert not manager._validate_config(invalid_type)

    def test_config_migration(self, temp_dir: Path):
        """Test configuration migration."""
        manager = ConfigManager(temp_dir)

        # Create old config format
        old_config = {
            "llm_model": "old-model",  # Old key
            "temp": 0.5,  # Old key
            "version": 1,
        }

        config_file = temp_dir / "settings.json"
        with open(config_file, "w") as f:
            json.dump(old_config, f)

        # Load should migrate automatically
        config = manager.get_config()

        # Should have migrated keys and updated version
        assert config["model"] == "old-model"
        assert config["temperature"] == 0.5
        assert config.get("version", 1) > 1

    def test_environment_override(self, temp_dir: Path):
        """Test environment variable override."""
        manager = ConfigManager(temp_dir)

        # Set environment variables
        env_vars = {
            "OCODE_MODEL": "env-model",
            "OCODE_TEMPERATURE": "0.9",
            "OCODE_VERBOSE": "true",
        }

        with patch.dict("os.environ", env_vars):
            config = manager.get_config()

            # Should use environment values
            assert config["model"] == "env-model"
            assert config["temperature"] == 0.9
            assert config["verbose"] is True

    def test_config_merge_hierarchy(self, temp_dir: Path):
        """Test configuration merge hierarchy."""
        # Global config
        global_config_dir = temp_dir / "global"
        global_config_dir.mkdir()
        global_config = {"model": "global-model", "temperature": 0.5}
        with open(global_config_dir / "settings.json", "w") as f:
            json.dump(global_config, f)

        # Project config
        project_config_dir = temp_dir / "project"
        project_config_dir.mkdir()
        project_config = {"model": "project-model", "max_tokens": 2000}
        with open(project_config_dir / "settings.json", "w") as f:
            json.dump(project_config, f)

        # Manager should merge configs (project overrides global)
        manager = ConfigManager(project_config_dir)
        manager.global_config_dir = global_config_dir

        config = manager.get_merged_config()

        assert config["model"] == "project-model"  # Project overrides
        assert config["temperature"] == 0.5  # From global
        assert config["max_tokens"] == 2000  # From project

    def test_config_file_corruption(self, temp_dir: Path):
        """Test handling of corrupted config file."""
        manager = ConfigManager(temp_dir)

        # Create corrupted config file
        config_file = temp_dir / "settings.json"
        config_file.write_text("{ invalid json")

        # Should fallback to default config
        config = manager.get_config()
        assert config == DEFAULT_CONFIG

    def test_config_backup_and_restore(self, temp_dir: Path):
        """Test config backup and restore."""
        manager = ConfigManager(temp_dir)

        # Save initial config
        original_config = {"model": "test-model", "temperature": 0.7}
        manager.save_config(original_config)

        # Create backup
        backup_path = manager.backup_config()
        assert backup_path.exists()

        # Modify config
        modified_config = {"model": "modified-model", "temperature": 0.9}
        manager.save_config(modified_config)

        # Restore from backup
        success = manager.restore_config(backup_path)
        assert success

        # Verify restoration
        restored_config = manager.get_config()
        assert restored_config["model"] == "test-model"
        assert restored_config["temperature"] == 0.7

    def test_list_available_models(self, temp_dir: Path):
        """Test listing available models."""
        manager = ConfigManager(temp_dir)

        # Mock model list
        mock_models = ["llama3:8b", "codellama:7b", "custom:latest"]

        with patch.object(manager, "_fetch_available_models", return_value=mock_models):
            models = manager.list_available_models()
            assert len(models) == 3
            assert "llama3:8b" in models

    def test_validate_model_exists(self, temp_dir: Path):
        """Test model existence validation."""
        manager = ConfigManager(temp_dir)

        mock_models = ["llama3:8b", "codellama:7b"]

        with patch.object(manager, "_fetch_available_models", return_value=mock_models):
            assert manager.validate_model("llama3:8b")
            assert not manager.validate_model("nonexistent:model")

    def test_config_schema_validation(self, temp_dir: Path):
        """Test configuration schema validation."""
        manager = ConfigManager(temp_dir)

        # Valid schema
        valid_config = {
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 1000,
            "permissions": {
                "allow_file_read": True,
                "allow_file_write": False,
                "allow_shell_exec": False,
            },
        }
        assert manager._validate_config_schema(valid_config)

        # Invalid schema - missing required field
        invalid_config = {"temperature": 0.7}  # Missing model
        assert not manager._validate_config_schema(invalid_config)

        # Invalid schema - wrong type for permissions
        invalid_permissions = {
            "model": "test",
            "permissions": "invalid",  # Should be dict
        }
        assert not manager._validate_config_schema(invalid_permissions)


@pytest.mark.unit
class TestDefaultConfig:
    """Test default configuration values."""

    def test_default_config_structure(self):
        """Test default configuration has required keys."""
        required_keys = [
            "model",
            "temperature",
            "max_tokens",
            "max_context_files",
            "output_format",
            "verbose",
        ]

        for key in required_keys:
            assert key in DEFAULT_CONFIG

    def test_default_config_types(self):
        """Test default configuration value types."""
        assert isinstance(DEFAULT_CONFIG["model"], str)
        assert isinstance(DEFAULT_CONFIG["temperature"], (int, float))
        assert isinstance(DEFAULT_CONFIG["max_tokens"], int)
        assert isinstance(DEFAULT_CONFIG["verbose"], bool)

    def test_default_config_ranges(self):
        """Test default configuration value ranges."""
        assert 0 <= DEFAULT_CONFIG["temperature"] <= 1
        assert DEFAULT_CONFIG["max_tokens"] > 0
        assert DEFAULT_CONFIG["max_context_files"] > 0


@pytest.mark.unit
class TestConfigUtilities:
    """Test configuration utility functions."""

    def test_normalize_model_name(self, temp_dir: Path):
        """Test model name normalization."""
        manager = ConfigManager(temp_dir)

        # Test various model name formats
        test_cases = [
            ("llama3", "llama3:latest"),
            ("llama3:8b", "llama3:8b"),
            ("custom/model", "custom/model:latest"),
            ("registry.com/model:tag", "registry.com/model:tag"),
        ]

        for input_name, expected in test_cases:
            normalized = manager._normalize_model_name(input_name)
            assert normalized == expected

    def test_config_diff(self, temp_dir: Path):
        """Test configuration difference calculation."""
        manager = ConfigManager(temp_dir)

        config1 = {"model": "test1", "temperature": 0.5, "shared": "value"}
        config2 = {"model": "test2", "temperature": 0.5, "new_key": "new_value"}

        diff = manager._calculate_config_diff(config1, config2)

        assert "model" in diff["changed"]
        assert diff["changed"]["model"]["from"] == "test1"
        assert diff["changed"]["model"]["to"] == "test2"
        assert "new_key" in diff["added"]
        assert "shared" in diff["removed"]

    def test_export_import_config(self, temp_dir: Path):
        """Test configuration export and import."""
        manager = ConfigManager(temp_dir)

        # Save config
        config = {"model": "export-test", "temperature": 0.8}
        manager.save_config(config)

        # Export config
        export_path = temp_dir / "exported_config.json"
        success = manager.export_config(export_path)
        assert success
        assert export_path.exists()

        # Modify current config
        manager.save_config({"model": "different"})

        # Import config
        success = manager.import_config(export_path)
        assert success

        # Verify import
        imported_config = manager.get_config()
        assert imported_config["model"] == "export-test"
        assert imported_config["temperature"] == 0.8
