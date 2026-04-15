# Query MCP - Download & Load Workflow

Automated workflow to download drug data from VSS and load into PostgreSQL.

## Overview

```
VSS Website
    ↓
Download Excel (Selenium)
    ↓
Parse Excel (BeautifulSoup)
    ↓
Transform Data
    ↓
PostgreSQL Database
    ├─ medicine_bid table
    ├─ items table
    └─ import_log table
```

## Workflow Steps

### 1. Download from VSS
- Uses Selenium to navigate VSS website
- Downloads Excel file with drug list
- Handles authentication if needed

### 2. Connect to PostgreSQL
- Establishes connection to PostgreSQL database
- Validates credentials
- Checks database availability

### 3. Create Schema
- Schema managed by Alembic (`alembic upgrade head`)
- Tables: `medicine_bid`, `items`, `import_log`
- Creates indexes for performance

### 4. Parse Excel
- Reads Excel XML file using BeautifulSoup
- Extracts headers and data rows
- Handles encoding/format issues
- Returns structured data

### 5. Load to Database
- Inserts drug records
- Handles duplicates with UPSERT
- Logs load operation
- Returns record count

### 6. Get Statistics
- Counts records in each table
- Reports load operation count
- Validates data integrity

## Database Schema

See [DATABASE_DESIGN.md](DATABASE_DESIGN.md) for full schema details.

Key tables for the workflow:

- **`medicine_bid`** — procurement bid records (42 columns, maps 1:1 to XLS columns)
- **`import_log`** — one row per upload: filename, status, rows_inserted/updated/failed, error_message, note

## Usage

### CLI

#### Basic Usage
```bash
python src/cli_workflow.py
```

#### With Existing File
```bash
python src/cli_workflow.py --file "path/to/drugs.xlsx" --skip-download
```

#### Custom Database
```bash
python src/cli_workflow.py \
  --db-host localhost \
  --db-port 5440 \
  --db-name testdb \
  --db-user postgres \
  --db-password postgres
```

#### Specific Date
```bash
python src/cli_workflow.py --date "13/04/2026"
```

### Python API

```python
from src.workflow import DownloadAndLoadWorkflow

# Create workflow
workflow = DownloadAndLoadWorkflow(
    db_host="localhost",
    db_port=5440,
    db_name="testdb",
    db_user="postgres",
    db_password="postgres"
)

# Run workflow
success = workflow.run()

# Get summary
summary = workflow.get_summary()
print(summary)
```

### Skip Download

If you already have the Excel file:

```bash
python src/cli_workflow.py \
  --file "/path/to/drugs.xlsx" \
  --skip-download
```

### Docker

```bash
docker-compose -f docker/docker-compose.yml up -d
docker exec query-mcp-server python src/cli_workflow.py --db-host postgres
```

## Configuration

### Database Credentials

Edit `~/.query-mcp/config.json`:

```json
{
  "database": {
    "host": "localhost",
    "port": 5440,
    "name": "testdb",
    "user": "postgres",
    "password": "postgres"
  }
}
```

### VSS Configuration

```json
{
  "vss": {
    "url": "https://quanlythuocv1.vss.gov.vn/...",
    "username": "your-username",
    "password": "your-password"
  }
}
```

## Output

### Successful Workflow

```
============================================================
WORKFLOW: Download Excel → Parse → Load to PostgreSQL
============================================================

📥 Step 1: Downloading from VSS...
✅ Downloaded to: data/Danh mục thuốc trúng thầu.xlsx

🔌 Step 2: Connecting to PostgreSQL...
✅ Connected to PostgreSQL: testdb

📋 Step 3: Creating database schema...
✅ Tables created successfully

📖 Step 4: Parsing Excel data...
✅ Parsed 1000 drug records

💾 Step 5: Loading to PostgreSQL...
✅ Loaded 1000 drug records

📊 Step 6: Getting statistics...
  Drugs: 1000
  Items: 0
  Load operations: 1

============================================================
✅ WORKFLOW COMPLETED SUCCESSFULLY
============================================================
```

### Workflow Summary

```json
{
  "status": "success",
  "timestamp": "2026-04-13T10:30:00",
  "steps": {
    "download": {"status": "success", "file": "..."},
    "database": {"status": "connected"},
    "schema": {"status": "created"},
    "parse": {"status": "success", "records": 1000},
    "load": {"status": "success", "records_loaded": 1000},
    "statistics": {
      "drugs": 1000,
      "items": 0,
      "load_operations": 1
    }
  }
}
```

## Error Handling

### No Excel File
```
❌ Error: No Excel file available
→ Run download step first or provide --file
```

### Database Connection Failed
```
❌ Database connection failed: could not connect to server
→ Check PostgreSQL is running and credentials are correct
```

### Parse Error
```
❌ Parse failed: Malformed XML
→ Check Excel file format is valid
```

### Load Error
```
❌ Failed to load drugs: duplicate key value
→ Check for duplicate records or unique constraint violations
```

## Troubleshooting

### "med_tech module not available"
```bash
# Solution: Install med_tech in same environment
cd /home/htnguyen/Space/med-tech
pip install -e .
```

### "Can't connect to PostgreSQL"
```bash
# Check PostgreSQL is running
docker-compose -f docker/docker-compose.yml ps

# Test connection
psql -h localhost -p 5440 -U postgres -c "SELECT 1;"
```

### "Excel parse error"
```bash
# Check file format
file path/to/drugs.xlsx

# Try with --skip-download
python src/cli_workflow.py --file "path/to/drugs.xlsx" --skip-download
```

### "Permission denied"
```bash
# Make script executable
chmod +x src/cli_workflow.py

# Or run with python
python src/cli_workflow.py
```

## Monitoring

### Check Import History
```sql
SELECT * FROM import_log ORDER BY created_at DESC LIMIT 10;
```

### Verify Data
```sql
SELECT COUNT(*) FROM medicine_bid;
SELECT COUNT(*) FROM items;
```

### Find Failures
```sql
SELECT * FROM import_log WHERE status = 'failed';
```

## Performance

### Typical Times
- Download: 20-30 seconds
- Parse: 5-10 seconds
- Database connect: 1 second
- Schema creation: 1 second
- Load 1000 records: 10-20 seconds
- **Total: 40-70 seconds**

### Optimization Tips
1. Use existing file with `--skip-download`
2. Increase batch size for large datasets
3. Run during off-peak hours
4. Monitor database performance with `pg_stat_statements`

## Advanced Features

### Custom Data Transformation

Extend workflow for custom parsing:

```python
from workflow import DownloadAndLoadWorkflow

class CustomWorkflow(DownloadAndLoadWorkflow):
    def parse_excel(self, filepath):
        # Custom parsing logic
        return super().parse_excel(filepath)
```

### Scheduled Runs

With cron:
```bash
0 9 * * * python /path/to/cli_workflow.py
```

### API Integration

Trigger from API:
```python
@app.post("/api/workflow/load")
def trigger_load(file: UploadFile):
    workflow = DownloadAndLoadWorkflow()
    success = workflow.run(download_file=file.filename)
    return {"status": "success" if success else "failed"}
```

## Next Steps

1. Set up PostgreSQL (Docker or local)
2. Configure database credentials
3. Run workflow: `python src/cli_workflow.py`
4. Query data: `SELECT * FROM medicine_bid;`
5. Monitor with `import_log` table

---

See [EXAMPLES.md](EXAMPLES.md) for SQL query examples.
