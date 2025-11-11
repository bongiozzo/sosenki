"""Unit tests for configuration loading.

Tests credential validation, configuration loading, and error handling.
"""

import json
import os

import pytest

from src.services.config import load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_missing_google_sheet_id(self, monkeypatch, tmp_path):
        """Test that missing GOOGLE_SHEET_ID raises ValueError with clear message."""
        # Clear environment
        monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)
        monkeypatch.delenv("CREDENTIALS_PATH", raising=False)

        # Create fake credentials file
        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(valid_creds))
        monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

        # Should raise ValueError
        with pytest.raises(ValueError, match="GOOGLE_SHEET_ID not configured"):
            load_config()

    def test_load_config_missing_credentials_file(self, monkeypatch):
        """Test that missing credentials file raises ValueError with clear message."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")
        monkeypatch.setenv("CREDENTIALS_PATH", "/nonexistent/path/creds.json")

        with pytest.raises(ValueError, match="Credentials file not found"):
            load_config()

    def test_load_config_invalid_credentials_json(self, monkeypatch, tmp_path):
        """Test that invalid JSON in credentials file raises ValueError."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")

        # Create invalid JSON file
        creds_file = tmp_path / "creds.json"
        creds_file.write_text("{invalid json")
        monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

        with pytest.raises(ValueError, match="not valid JSON"):
            load_config()

    def test_load_config_missing_credentials_fields(self, monkeypatch, tmp_path):
        """Test that credentials file missing required fields raises ValueError."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")

        # Create credentials with missing fields
        creds_file = tmp_path / "creds.json"
        incomplete_creds = {
            "type": "service_account",
            "project_id": "test-project",
            # Missing: private_key, client_email
        }
        creds_file.write_text(json.dumps(incomplete_creds))
        monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

        with pytest.raises(ValueError, match="missing required fields"):
            load_config()

    def test_load_config_invalid_private_key_format(self, monkeypatch, tmp_path):
        """Test that invalid private key format raises ValueError."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")

        # Create credentials with invalid key format
        creds_file = tmp_path / "creds.json"
        invalid_key_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "invalid-key-format",  # Missing RSA header
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(invalid_key_creds))
        monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

        with pytest.raises(ValueError, match="invalid private key format"):
            load_config()

    def test_load_config_valid_configuration(self, monkeypatch, tmp_path):
        """Test that valid configuration loads successfully."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id-12345")

        # Create valid credentials file
        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(valid_creds))
        monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

        # Should load successfully
        config = load_config()
        assert config.google_sheet_id == "test-sheet-id-12345"
        assert config.credentials_path == str(creds_file)
        # Note: DATABASE_URL may be overridden by test environment
        assert "sqlite://" in config.database_url or "postgresql://" in config.database_url
        assert config.log_file == "logs/seed.log"  # default

    def test_load_config_with_custom_database_url(self, monkeypatch, tmp_path):
        """Test that custom DATABASE_URL loads correctly."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/sostenki")

        # Create valid credentials
        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(valid_creds))
        monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

        config = load_config()
        assert config.database_url == "postgresql://localhost/sostenki"

    def test_load_config_credentials_not_readable(self, monkeypatch, tmp_path):
        """Test that unreadable credentials file raises clear error."""
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id")

        # Create credentials file but make it unreadable
        creds_file = tmp_path / "creds.json"
        creds_file.write_text("{}")
        creds_file.chmod(0o000)
        monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

        try:
            with pytest.raises(ValueError, match="Cannot read credentials file"):
                load_config()
        finally:
            # Restore permissions for cleanup
            creds_file.chmod(0o644)

    def test_load_config_from_env_file(self, monkeypatch, tmp_path):
        """Test that configuration loads from .env file (T032)."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("GOOGLE_SHEET_ID=sheet-from-env\n")

        # Create valid credentials
        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(valid_creds))

        # Change to temp directory so .env is found
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))
            monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)  # Clear env var

            config = load_config()
            assert config.google_sheet_id == "sheet-from-env"
        finally:
            os.chdir(original_cwd)

    def test_load_config_env_overrides_env_file(self, monkeypatch, tmp_path):
        """Test that environment variables override .env file."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("GOOGLE_SHEET_ID=sheet-from-env\n")

        # Create valid credentials
        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(valid_creds))

        # Set environment variable that should override .env
        monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-from-env-var")

        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            monkeypatch.setenv("CREDENTIALS_PATH", str(creds_file))

            config = load_config()
            # Environment variable should take precedence
            assert config.google_sheet_id == "sheet-from-env-var"
        finally:
            os.chdir(original_cwd)
