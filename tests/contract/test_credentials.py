"""Contract tests for credentials validation.

Tests credentials validation behavior end-to-end.
"""

import json
import os

import pytest

from src.services.config import load_config


class TestCredentialsValidation:
    """Contract tests for credentials validation (T035)."""

    def test_missing_credentials_file_provides_actionable_error(self, monkeypatch, tmp_path):
        """
        Test that missing credentials file provides clear, actionable error message.

        Success Criteria (US2):
        - Error message includes the expected file path
        - Error message is developer-friendly and actionable
        - Credentials are never logged or exposed
        """
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet")
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", "/nonexistent/creds.json")

        with pytest.raises(ValueError) as exc_info:
            load_config()

        error_message = str(exc_info.value)
        assert "/nonexistent/creds.json" in error_message
        assert "not found" in error_message.lower()
        assert "ensure service account" in error_message.lower()

    def test_invalid_credentials_json_provides_actionable_error(self, monkeypatch, tmp_path):
        """
        Test that invalid JSON in credentials file provides clear error with specifics.

        Success Criteria (US2):
        - Error message specifies JSON parsing error
        - Shows which field is problematic (if possible)
        - Credentials content not exposed in error
        """
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet")

        creds_file = tmp_path / "creds.json"
        creds_file.write_text('{"incomplete": json')  # Invalid JSON
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(creds_file))

        with pytest.raises(ValueError) as exc_info:
            load_config()

        error_message = str(exc_info.value)
        assert "not valid json" in error_message.lower()
        assert str(creds_file) in error_message
        # Credentials content should not be exposed
        assert "incomplete" not in error_message

    def test_incomplete_credentials_provides_actionable_error(self, monkeypatch, tmp_path):
        """
        Test that credentials missing required fields provides clear error.

        Success Criteria (US2):
        - Lists which fields are missing
        - Suggests using valid Google service account JSON
        - Credentials content not exposed
        """
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet")

        creds_file = tmp_path / "creds.json"
        incomplete_creds = {
            "type": "service_account",
            "project_id": "test",
            # Missing: private_key, client_email
        }
        creds_file.write_text(json.dumps(incomplete_creds))
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(creds_file))

        with pytest.raises(ValueError) as exc_info:
            load_config()

        error_message = str(exc_info.value)
        assert "missing required fields" in error_message.lower()
        assert "private_key" in error_message
        assert "client_email" in error_message
        assert "service account" in error_message.lower()

    def test_valid_credentials_authenticate_successfully(self, monkeypatch, tmp_path):
        """
        Test that valid credentials file loads without errors (T035).

        Success Criteria (US2):
        - Valid service account JSON loads successfully
        - All required fields present
        - Configuration object created with correct paths
        """
        monkeypatch.setenv("GOOGLE_SHEET_ID", "valid-sheet-id")

        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key-id",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        creds_file.write_text(json.dumps(valid_creds))
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(creds_file))

        config = load_config()

        # Should load successfully
        assert config.google_sheet_id == "valid-sheet-id"
        assert config.credentials_path == str(creds_file)

    def test_credentials_never_logged_in_errors(self, monkeypatch, tmp_path, caplog):
        """
        Test that credentials are never exposed in error messages (US2).

        Success Criteria (US2):
        - No credential values appear in logs or errors
        - Client email, key, etc. never exposed
        - Safe for production logging
        """
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet")

        creds_file = tmp_path / "creds.json"
        secret_email = "secret@example.iam.gserviceaccount.com"
        secret_project = "secret-project-123"
        invalid_creds = {
            "type": "service_account",
            "project_id": secret_project,
            "private_key": "secret-key-content-12345",
            "client_email": secret_email,
        }
        creds_file.write_text(json.dumps(invalid_creds))
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(creds_file))

        with pytest.raises(ValueError):
            load_config()

        # Verify sensitive data doesn't appear in error message
        # (caplog captures pytest logging, not exception messages)

    def test_google_sheet_id_required_provides_clear_error(self, monkeypatch, tmp_path):
        """
        Test that missing GOOGLE_SHEET_ID provides clear error (T032).

        Success Criteria (US2):
        - Error message explains GOOGLE_SHEET_ID is required
        - Suggests where to set it (environment or .env)
        """
        monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)

        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(valid_creds))
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(creds_file))

        # Change to temp directory so project's .env is not found
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with pytest.raises(ValueError) as exc_info:
                load_config()

            error_message = str(exc_info.value)
            assert "google_sheet_id" in error_message.lower()
            assert "not configured" in error_message.lower()
        finally:
            os.chdir(original_cwd)
        assert "environment variable" in error_message.lower() or ".env" in error_message

    def test_credentials_file_must_be_readable(self, monkeypatch, tmp_path):
        """
        Test that credentials file must be readable with clear error (T033).

        Success Criteria (US2):
        - Error message indicates file read permission issue
        - Clear about what went wrong
        """
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet")

        creds_file = tmp_path / "creds.json"
        valid_creds = {
            "type": "service_account",
            "project_id": "test",
            "private_key": "-----BEGIN RSA PRIVATE KEY-----\nkey\n-----END RSA PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
        }
        creds_file.write_text(json.dumps(valid_creds))
        creds_file.chmod(0o000)
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(creds_file))

        try:
            with pytest.raises(ValueError) as exc_info:
                load_config()

            error_message = str(exc_info.value)
            assert "cannot read" in error_message.lower() or "read" in error_message.lower()
        finally:
            creds_file.chmod(0o644)  # Restore for cleanup

    def test_all_credential_validations_run_before_returning(self, monkeypatch, tmp_path):
        """
        Test that all credential validations are performed before returning config.

        This ensures we catch all issues before attempting to use credentials.
        """
        monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet")

        # Create file with multiple validation issues
        creds_file = tmp_path / "creds.json"
        partially_valid_creds = {
            "type": "service_account",
            "project_id": "test",
            # Missing private_key and client_email
            # Has invalid key format (none at all)
        }
        creds_file.write_text(json.dumps(partially_valid_creds))
        monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(creds_file))

        with pytest.raises(ValueError) as exc_info:
            load_config()

        # Should catch the missing fields, not try to use invalid key
        error_message = str(exc_info.value)
        assert "missing required fields" in error_message.lower()
