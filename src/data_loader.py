"""Load data from Excel/CSV to PostgreSQL database"""

import os
import psycopg2
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataLoader:
    """Load drug data from Excel/CSV into PostgreSQL"""

    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 5432,
        db_name: str = "testdb",
        db_user: str = "postgres",
        db_password: str = "postgres"
    ):
        """Initialize data loader with database credentials"""
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.conn = None
        self.cursor = None

    def connect(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            self.cursor = self.conn.cursor()
            print(f"✅ Connected to PostgreSQL: {self.db_name}")
            return True
        except psycopg2.Error as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("🔌 Database connection closed")

    def create_tables(self) -> bool:
        """Create tables if they don't exist"""
        try:
            # Drugs table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS drugs (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100),
                    price DECIMAL(10, 2),
                    stock INTEGER,
                    status VARCHAR(50) DEFAULT 'active',
                    manufacturer VARCHAR(100),
                    description TEXT,
                    source_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Items table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    drug_id INTEGER REFERENCES drugs(id),
                    sku VARCHAR(50) UNIQUE,
                    barcode VARCHAR(50),
                    batch_number VARCHAR(100),
                    expiry_date DATE,
                    quantity_available INTEGER DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Load logs table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS load_logs (
                    id SERIAL PRIMARY KEY,
                    file_name VARCHAR(255),
                    record_type VARCHAR(50),
                    records_loaded INTEGER,
                    load_status VARCHAR(50),
                    error_message TEXT,
                    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create indexes
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_drugs_name ON drugs(name);
                CREATE INDEX IF NOT EXISTS idx_drugs_category ON drugs(category);
                CREATE INDEX IF NOT EXISTS idx_drugs_status ON drugs(status);
                CREATE INDEX IF NOT EXISTS idx_items_drug_id ON items(drug_id);
                CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
            """)

            self.conn.commit()
            print("✅ Tables created successfully")
            return True
        except psycopg2.Error as e:
            print(f"❌ Failed to create tables: {e}")
            self.conn.rollback()
            return False

    def load_drugs(self, data: List[Dict[str, Any]]) -> int:
        """Load drug data into PostgreSQL"""
        loaded = 0
        try:
            for row in data:
                self.cursor.execute("""
                    INSERT INTO drugs (name, category, price, stock, status, manufacturer, description, source_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id) DO UPDATE
                    SET name=EXCLUDED.name,
                        category=EXCLUDED.category,
                        price=EXCLUDED.price,
                        stock=EXCLUDED.stock,
                        status=EXCLUDED.status,
                        manufacturer=EXCLUDED.manufacturer,
                        updated_at=CURRENT_TIMESTAMP
                """, (
                    row.get('name'),
                    row.get('category'),
                    row.get('price'),
                    row.get('stock'),
                    row.get('status', 'active'),
                    row.get('manufacturer'),
                    row.get('description'),
                    row.get('source_id') or row.get('name')  # Use name as fallback ID
                ))
                loaded += 1

            self.conn.commit()
            print(f"✅ Loaded {loaded} drug records")
            self._log_load('drugs', loaded, 'success')
            return loaded
        except psycopg2.Error as e:
            print(f"❌ Failed to load drugs: {e}")
            self.conn.rollback()
            self._log_load('drugs', loaded, 'failed', str(e))
            return 0

    def load_items(self, data: List[Dict[str, Any]]) -> int:
        """Load item data into PostgreSQL"""
        loaded = 0
        try:
            for row in data:
                # Get drug_id by name
                drug_id = self._get_drug_id(row.get('drug_name') or row.get('name'))
                if not drug_id:
                    continue

                self.cursor.execute("""
                    INSERT INTO items (drug_id, sku, barcode, batch_number, expiry_date, quantity_available, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sku) DO UPDATE
                    SET quantity_available=EXCLUDED.quantity_available,
                        expiry_date=EXCLUDED.expiry_date,
                        updated_at=CURRENT_TIMESTAMP
                """, (
                    drug_id,
                    row.get('sku'),
                    row.get('barcode'),
                    row.get('batch_number'),
                    row.get('expiry_date'),
                    row.get('quantity', row.get('stock')),
                    row.get('status', 'active')
                ))
                loaded += 1

            self.conn.commit()
            print(f"✅ Loaded {loaded} item records")
            self._log_load('items', loaded, 'success')
            return loaded
        except psycopg2.Error as e:
            print(f"❌ Failed to load items: {e}")
            self.conn.rollback()
            self._log_load('items', loaded, 'failed', str(e))
            return 0

    def _get_drug_id(self, drug_name: str) -> Optional[int]:
        """Get drug ID by name"""
        try:
            self.cursor.execute("SELECT id FROM drugs WHERE name = %s", (drug_name,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except psycopg2.Error:
            return None

    def _log_load(self, record_type: str, records: int, status: str, error_msg: str = None):
        """Log data load operation"""
        try:
            self.cursor.execute("""
                INSERT INTO load_logs (file_name, record_type, records_loaded, load_status, error_message)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                f"load_{datetime.now().isoformat()}",
                record_type,
                records,
                status,
                error_msg
            ))
            self.conn.commit()
        except psycopg2.Error:
            pass

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM drugs")
            drug_count = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM items")
            item_count = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM load_logs")
            load_count = self.cursor.fetchone()[0]

            return {
                'drugs': drug_count,
                'items': item_count,
                'load_operations': load_count
            }
        except psycopg2.Error as e:
            print(f"❌ Failed to get statistics: {e}")
            return {}
