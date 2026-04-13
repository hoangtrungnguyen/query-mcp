"""Workflow: Download from VSS and load into PostgreSQL"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Import from med_tech (if available)
try:
    from med_tech.downloader import Downloader
    from med_tech.config import DOWNLOAD_PATH
    MEDTECH_AVAILABLE = True
except ImportError:
    MEDTECH_AVAILABLE = False
    print("⚠️  med_tech module not available. Use download_file parameter.")

from .data_loader import DataLoader


class DownloadAndLoadWorkflow:
    """
    Orchestrate: Download Excel from VSS → Parse → Load to PostgreSQL

    Workflow:
    1. Download Excel file from VSS website
    2. Parse Excel data using BeautifulSoup
    3. Transform data to match PostgreSQL schema
    4. Create tables if they don't exist
    5. Load data into PostgreSQL
    6. Log operation status
    """

    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 5432,
        db_name: str = "testdb",
        db_user: str = "postgres",
        db_password: str = "postgres",
        vss_url: str = None,
        vss_username: str = None,
        vss_password: str = None
    ):
        """Initialize workflow"""
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.vss_url = vss_url
        self.vss_username = vss_username
        self.vss_password = vss_password
        self.data_loader = None
        self.downloader = None
        self.status = "pending"
        self.summary = {}

    def download_from_vss(self, date: str = None) -> bool:
        """Download Excel from VSS website"""
        print(f"\n📥 Step 1: Downloading from VSS...")

        if not MEDTECH_AVAILABLE:
            print("❌ med_tech module not available for download")
            return False

        try:
            self.downloader = Downloader(
                vss_url=self.vss_url,
                username=self.vss_username,
                password=self.vss_password
            )
            filepath = self.downloader.download(date=date)
            print(f"✅ Downloaded to: {filepath}")
            self.summary['download'] = {
                'status': 'success',
                'file': str(filepath)
            }
            return True
        except Exception as e:
            print(f"❌ Download failed: {e}")
            self.summary['download'] = {
                'status': 'failed',
                'error': str(e)
            }
            return False

    def connect_database(self) -> bool:
        """Connect to PostgreSQL"""
        print(f"\n🔌 Step 2: Connecting to PostgreSQL...")

        self.data_loader = DataLoader(
            db_host=self.db_host,
            db_port=self.db_port,
            db_name=self.db_name,
            db_user=self.db_user,
            db_password=self.db_password
        )

        if self.data_loader.connect():
            self.summary['database'] = {'status': 'connected'}
            return True
        else:
            self.summary['database'] = {'status': 'failed'}
            return False

    def create_schema(self) -> bool:
        """Create tables if they don't exist"""
        print(f"\n📋 Step 3: Creating database schema...")

        if self.data_loader.create_tables():
            self.summary['schema'] = {'status': 'created'}
            return True
        else:
            self.summary['schema'] = {'status': 'failed'}
            return False

    def parse_excel(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Parse Excel file"""
        print(f"\n📖 Step 4: Parsing Excel data...")

        try:
            from bs4 import BeautifulSoup

            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            soup = BeautifulSoup(content, 'xml')

            # Parse headers from first row
            headers = []
            first_row = soup.find('Row')
            if first_row:
                for cell in first_row.find_all('Cell'):
                    val = cell.find('Data')
                    headers.append(val.text if val else '')

            # Parse data rows
            drugs = []
            rows = soup.find_all('Row')[1:]  # Skip header row

            for row in rows:
                cells = row.find_all('Cell')
                if cells:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        val = cell.find('Data')
                        if i < len(headers):
                            row_data[headers[i]] = val.text if val else ''
                    if row_data.get('name') or row_data.get('tên'):
                        drugs.append(row_data)

            print(f"✅ Parsed {len(drugs)} drug records")
            self.summary['parse'] = {
                'status': 'success',
                'records': len(drugs)
            }
            return {'drugs': drugs}

        except Exception as e:
            print(f"❌ Parse failed: {e}")
            self.summary['parse'] = {
                'status': 'failed',
                'error': str(e)
            }
            return None

    def load_to_database(self, data: Dict[str, Any]) -> bool:
        """Load parsed data to PostgreSQL"""
        print(f"\n💾 Step 5: Loading to PostgreSQL...")

        if not data:
            print("❌ No data to load")
            return False

        drugs = data.get('drugs', [])
        if drugs:
            loaded = self.data_loader.load_drugs(drugs)
            self.summary['load'] = {
                'status': 'success',
                'records_loaded': loaded
            }
            return True
        else:
            self.summary['load'] = {
                'status': 'failed',
                'error': 'No drug records'
            }
            return False

    def get_statistics(self):
        """Get final statistics"""
        print(f"\n📊 Step 6: Getting statistics...")

        stats = self.data_loader.get_statistics()
        print(f"  Drugs: {stats.get('drugs', 0)}")
        print(f"  Items: {stats.get('items', 0)}")
        print(f"  Load operations: {stats.get('load_operations', 0)}")

        self.summary['statistics'] = stats
        return stats

    def run(self, download_file: str = None, skip_download: bool = False) -> bool:
        """
        Execute full workflow

        Args:
            download_file: Path to existing Excel file (skips download)
            skip_download: Skip download step, use existing file

        Returns:
            True if workflow succeeded, False otherwise
        """
        print("=" * 60)
        print("WORKFLOW: Download Excel → Parse → Load to PostgreSQL")
        print("=" * 60)

        try:
            # Step 1: Download
            if not skip_download and not download_file:
                if not self.download_from_vss():
                    self.status = "failed"
                    return False
                download_file = str(Path(DOWNLOAD_PATH) / "Danh mục thuốc trúng thầu.xlsx") if MEDTECH_AVAILABLE else None

            # Step 2: Connect database
            if not self.connect_database():
                self.status = "failed"
                return False

            # Step 3: Create schema
            if not self.create_schema():
                self.status = "failed"
                return False

            # Step 4: Parse Excel
            if not download_file:
                print("❌ No Excel file available")
                self.status = "failed"
                return False

            data = self.parse_excel(download_file)
            if not data:
                self.status = "failed"
                return False

            # Step 5: Load to database
            if not self.load_to_database(data):
                self.status = "failed"
                return False

            # Step 6: Get statistics
            self.get_statistics()

            # Cleanup
            self.data_loader.disconnect()

            self.status = "success"
            print("\n" + "=" * 60)
            print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
            print("=" * 60)
            return True

        except Exception as e:
            print(f"\n❌ Workflow failed: {e}")
            self.status = "failed"
            if self.data_loader:
                self.data_loader.disconnect()
            return False

    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary"""
        return {
            'status': self.status,
            'timestamp': datetime.now().isoformat(),
            'steps': self.summary
        }

    def print_summary(self):
        """Print workflow summary"""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("WORKFLOW SUMMARY")
        print("=" * 60)
        print(f"Status: {summary['status'].upper()}")
        print(f"Time: {summary['timestamp']}")
        print("\nSteps:")
        for step, result in summary['steps'].items():
            status = result.get('status', 'unknown')
            print(f"  {step}: {status}")
            if result.get('error'):
                print(f"    Error: {result['error']}")
            if result.get('records'):
                print(f"    Records: {result['records']}")
        print("=" * 60)
