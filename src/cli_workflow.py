#!/usr/bin/env python3
"""CLI for Download → Parse → Load workflow"""

import argparse
import sys
from pathlib import Path

from workflow import DownloadAndLoadWorkflow


def main():
    """Run workflow from command line"""
    parser = argparse.ArgumentParser(
        description="Download from VSS and load to PostgreSQL"
    )

    parser.add_argument(
        "--file",
        type=str,
        help="Path to existing Excel file (skips download)"
    )

    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step (requires --file)"
    )

    parser.add_argument(
        "--db-host",
        type=str,
        default="localhost",
        help="PostgreSQL host (default: localhost)"
    )

    parser.add_argument(
        "--db-port",
        type=int,
        default=5440,
        help="PostgreSQL port (default: 5440)"
    )

    parser.add_argument(
        "--db-name",
        type=str,
        default="testdb",
        help="Database name (default: testdb)"
    )

    parser.add_argument(
        "--db-user",
        type=str,
        default="postgres",
        help="Database user (default: postgres)"
    )

    parser.add_argument(
        "--db-password",
        type=str,
        default="postgres",
        help="Database password (default: postgres)"
    )

    parser.add_argument(
        "--date",
        type=str,
        help="Date for VSS download (DD/MM/YYYY)"
    )

    parser.add_argument(
        "--vss-url",
        type=str,
        help="VSS website URL"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.skip_download and not args.file:
        print("❌ Error: --skip-download requires --file")
        sys.exit(1)

    # Create and run workflow
    workflow = DownloadAndLoadWorkflow(
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        db_password=args.db_password,
        vss_url=args.vss_url
    )

    success = workflow.run(
        download_file=args.file,
        skip_download=args.skip_download
    )

    # Print summary
    workflow.print_summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
