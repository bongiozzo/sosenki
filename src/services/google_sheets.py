"""Google Sheets API client for fetching data.

Handles authentication and data retrieval from Google Sheets using
service account credentials.
"""

import logging
from typing import Any, List

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.services.errors import APIError, CredentialsError


class GoogleSheetsClient:
    """Client for Google Sheets API operations."""

    def __init__(self, credentials_path: str):
        """
        Initialize Google Sheets API client.

        Args:
            credentials_path: Path to service account JSON credentials file

        Raises:
            CredentialsError: If credentials file not found or invalid
            APIError: If authentication fails
        """
        self.logger = logging.getLogger("sostenki.seeding.google_sheets")
        self.credentials_path = credentials_path

        try:
            # Load credentials from JSON file
            self.credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
            )
            self.logger.info(f"Loaded credentials from {credentials_path}")
        except FileNotFoundError as e:
            raise CredentialsError(f"Credentials file not found: {credentials_path}") from e
        except ValueError as e:
            raise CredentialsError(f"Invalid credentials file format: {credentials_path}") from e

        # Build Sheets API service
        try:
            self.service = build("sheets", "v4", credentials=self.credentials)
            self.logger.info("Google Sheets API service initialized")
        except Exception as e:
            raise APIError(f"Failed to initialize Google Sheets API: {e}") from e

    def fetch_sheet_data(self, spreadsheet_id: str, range_spec: str = None) -> List[List[Any]]:
        """
        Fetch data from a named range in Google Sheets.

        Args:
            spreadsheet_id: Google Sheet ID
            range_spec: Named range name (e.g., "PropertiesOwners")
                       If None, raises error (sheet_name no longer supported)

        Returns:
            List of rows, each row is a list of cell values

        Raises:
            APIError: If API call fails
            ValueError: If range_spec not provided

        Example:
            ```python
            import os
            client = GoogleSheetsClient("credentials.json")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            # Fetch named range
            data = client.fetch_sheet_data(sheet_id, range_spec="MyRange")
            print(f"Fetched {len(data)} rows")
            ```
        """
        try:
            if not range_spec:
                raise ValueError("range_spec (named range name) is required")

            self.logger.info(f"Fetching data from named range: {range_spec}...")

            # Call Sheets API
            request = (
                self.service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_spec,
                    valueRenderOption="FORMATTED_VALUE",  # Get formatted values (e.g., "Да", "3,85%")
                )
            )
            result = request.execute()

            # Extract values
            values = result.get("values", [])
            self.logger.info(f"Fetched {len(values)} rows from range {range_spec}")

            return values

        except HttpError as e:
            if e.resp.status == 404:
                raise APIError(f"Sheet not found: {spreadsheet_id} or range '{range_spec}'") from e
            elif e.resp.status == 403:
                raise APIError(
                    f"Access denied to sheet {spreadsheet_id}. Check service account permissions."
                ) from e
            else:
                raise APIError(f"Google Sheets API error: {e}") from e
        except Exception as e:
            raise APIError(f"Failed to fetch sheet data: {e}") from e
