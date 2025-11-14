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

    def fetch_sheet_data(
        self, spreadsheet_id: str, sheet_name: str, range_spec: str = None
    ) -> List[List[Any]]:
        """
        Fetch data from a Google Sheet.

        Args:
            spreadsheet_id: Google Sheet ID
            sheet_name: Sheet name (e.g., "Дома")
            range_spec: Optional range in A1 notation (e.g., "A1:Z100")
                       If None, fetches entire sheet

        Returns:
            List of rows, each row is a list of cell values

        Raises:
            APIError: If API call fails

        Example:
            ```python
            import os
            client = GoogleSheetsClient("credentials.json")
            sheet_id = os.getenv("GOOGLE_SHEET_ID")
            data = client.fetch_sheet_data(sheet_id, "Дома")
            print(f"Fetched {len(data)} rows")
            ```
        """
        try:
            # Construct range: "Sheet Name" or "Sheet Name!A1:Z100"
            if range_spec:
                range_notation = f"'{sheet_name}'!{range_spec}"
            else:
                range_notation = f"'{sheet_name}'"

            self.logger.info(f"Fetching data from {sheet_name} sheet...")

            # Call Sheets API
            request = (
                self.service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_notation,
                    valueRenderOption="FORMATTED_VALUE",  # Get formatted values (e.g., "Да", "3,85%")
                )
            )
            result = request.execute()

            # Extract values
            values = result.get("values", [])
            self.logger.info(f"Fetched {len(values)} rows from {sheet_name}")

            return values

        except HttpError as e:
            if e.resp.status == 404:
                raise APIError(f"Sheet not found: {spreadsheet_id} or sheet '{sheet_name}'") from e
            elif e.resp.status == 403:
                raise APIError(
                    f"Access denied to sheet {spreadsheet_id}. Check service account permissions."
                ) from e
            else:
                raise APIError(f"Google Sheets API error: {e}") from e
        except Exception as e:
            raise APIError(f"Failed to fetch sheet data: {e}") from e

    def fetch_header_row(self, spreadsheet_id: str, sheet_name: str) -> List[str]:
        """
        Fetch header row from a sheet (first row).

        Args:
            spreadsheet_id: Google Sheet ID
            sheet_name: Sheet name

        Returns:
            List of header names

        Raises:
            APIError: If API call fails
        """
        rows = self.fetch_sheet_data(spreadsheet_id, sheet_name, range_spec="1:1")
        return rows[0] if rows else []

    def fetch_data_rows(
        self, spreadsheet_id: str, sheet_name: str, skip_header: bool = True
    ) -> List[List[Any]]:
        """
        Fetch data rows from a sheet (excluding header).

        Args:
            spreadsheet_id: Google Sheet ID
            sheet_name: Sheet name
            skip_header: If True, skip first row (header)

        Returns:
            List of data rows (excluding header if skip_header=True)

        Raises:
            APIError: If API call fails
        """
        rows = self.fetch_sheet_data(spreadsheet_id, sheet_name)

        if skip_header and rows:
            return rows[1:]  # Skip header row

        return rows
