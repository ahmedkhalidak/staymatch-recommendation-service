#!/usr/bin/env python3
"""CLI script to trigger full data sync from MSSQL to PostgreSQL."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.sync.data_sync import DataSyncService


def main():
    service = DataSyncService()
    print("Starting full data sync...")
    result = service.sync_all()
    print(f"Sync completed: {result}")


if __name__ == "__main__":
    main()