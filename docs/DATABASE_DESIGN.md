# Database Design

## Schema Overview

**Application tables:** `medicine_bid`, `items`, `users`, `orders`
**System tables:** `query_sessions`, `query_history`, `import_log`
**Views:** `active_drugs`, `drugs_by_category`, `expensive_items`

Managed by Alembic. Single migration file: `alembic/versions/8f9881ec5d77_initial_schema.py`.

---

## `medicine_bid` Table

Source: *Danh mục thuốc trúng thầu* (procurement bid catalogue from VSS/med-tech service).

### Core Fields (from XLS)

| Column | Type | XLS column | Description |
|--------|------|------------|-------------|
| `id` | `SERIAL` PK | — | Auto-increment |
| `name` | `TEXT` NOT NULL | — | Drug trade name (Tên thuốc) |
| `active_ingredient` | `TEXT` | `hoatchat` | Active substance (Tên hoạt chất) |
| `registration_number` | `TEXT` | `sodk` | Registration number (Số DK) |
| `route` | `TEXT` | `duongdung` | Route of administration (Đường dùng) |
| `concentration` | `TEXT` | `hamluong` | Dosage/strength (Hàm lượng) |
| `unit` | `TEXT` | `donvitinh` | Unit of measure (ĐVT) |
| `stock` | `INTEGER` | `soluong` | Quantity (Số lượng) |
| `price` | `NUMERIC(10,2)` | `gia` | Unit price (Giá) |
| `total_amount` | `NUMERIC(15,2)` | `thanhtien` | Total value (Thành tiền) |
| `category` | `TEXT` | `nhomthau` | Bid group (Nhóm thầu) |
| `manufacturer` | `TEXT` | `nhasx` | Manufacturer name (Nhà SX) |
| `country` | `TEXT` | `nuocsx` | Country of manufacture (Nước SX) |
| `province_code` | `VARCHAR(10)` | `ma_tinh` | Province code (Mã tỉnh) |
| `facility_code` | `VARCHAR(20)` | `ma_cskcb` | Healthcare facility code (Mã CSKCB) |
| `contract_start_date` | `DATE` | `tungay_hd` | Contract effective date (Từ ngày HD) |
| `contract_end_date` | `DATE` | `denngay_hd` | Contract expiry date (Đến ngày HD) |
| `bid_type` | `VARCHAR(50)` | `loai_thau` | Bid type |
| `province_name` | `VARCHAR(200)` | `ten_tinh` | Province name |
| `department_name` | `VARCHAR(300)` | `ten_don_vi` | Department name |
| `facility_name` | `VARCHAR(300)` | `ten_cskcb` | Facility name |
| `drug_code` | `VARCHAR(50)` | `ma` | Drug code |
| `drug_code_gy` | `VARCHAR(50)` | `ma_gy` | Drug code (GY system) |
| `route_code` | `VARCHAR(20)` | `maduongdung` | Route code |
| `route_code_gy` | `VARCHAR(20)` | `madd_gy` | Route code (GY system) |
| `dosage_form` | `VARCHAR(200)` | `dangbaoche` | Dosage form |
| `packaging` | `VARCHAR(300)` | `donggoi` | Packaging description |
| `contractor_name` | `VARCHAR(300)` | `tennhathau` | Contractor name |
| `decision_number` | `VARCHAR(100)` | `quyetdinh` | Decision/decree number |
| `valid_from` | `TIMESTAMP` | `tungay` | Validity start date |
| `valid_to` | `TIMESTAMP` | `denngay` | Validity end date |
| `bid_package` | `VARCHAR(20)` | `goithau` | Bid lot/package (e.g. G1) |
| `standard` | `VARCHAR(200)` | `tieuchuan` | Quality standard |
| `drug_type` | `VARCHAR(100)` | `loai` | Drug type (e.g. Tân dược, Chế phẩm) |
| `approval_sequence` | `VARCHAR(50)` | `sttpheduyet` | Approval sequence number |
| `validity` | `VARCHAR(10)` | `hieuluc` | Validity flag |
| `published_at` | `TIMESTAMP` | `congbo` | Publication date |
| `bid_form` | `VARCHAR(20)` | `ht_thau` | Bidding form code |
| `source_created_at` | `TIMESTAMP` | `created_date` | Record creation date in source system |

### System Fields

| Column | Type | Description |
|--------|------|-------------|
| `record_hash` | `TEXT` GENERATED UNIQUE | MD5 deduplication key (see below) |
| `created_at` | `TIMESTAMP` | Insert timestamp |
| `updated_at` | `TIMESTAMP` | Last update timestamp |

### Indexes

| Index | Column(s) | Unique |
|-------|-----------|--------|
| `medicine_bid_pkey` | `id` | Yes |
| `ix_medicine_bid_record_hash` | `record_hash` | Yes |
| `idx_medicine_bid_registration_number` | `registration_number` | No |
| `idx_medicine_bid_facility_code` | `facility_code` | No |
| `idx_medicine_bid_province_code` | `province_code` | No |
| `idx_medicine_bid_contract_end_date` | `contract_end_date` | No |
| `idx_medicine_bid_category` | `category` | No |
| `idx_medicine_bid_price` | `price` | No |

### Deduplication (`record_hash`)

`record_hash` is a PostgreSQL `GENERATED ALWAYS AS ... STORED` column:

```sql
md5(
    COALESCE(registration_number, '') || '|' ||
    COALESCE(active_ingredient, '')   || '|' ||
    COALESCE(name, '')                || '|' ||
    COALESCE(concentration, '')       || '|' ||
    COALESCE(facility_code, '')       || '|' ||
    COALESCE((contract_start_date - '1970-01-01'::date)::TEXT, '') || '|' ||
    COALESCE((contract_end_date   - '1970-01-01'::date)::TEXT, '')
)
```

On upsert: `ON CONFLICT (record_hash) DO UPDATE SET ..., updated_at = CURRENT_TIMESTAMP`

---

## `items` Table

Generic inventory items (not from VSS source).

| Column | Type | Notes |
|--------|------|-------|
| `id` | `SERIAL` PK | |
| `name` | `VARCHAR(255)` NOT NULL | |
| `category` | `VARCHAR(100)` | |
| `price` | `NUMERIC(10,2)` | |
| `status` | `VARCHAR(50)` | |
| `quantity` | `INTEGER` | |
| `created_at` | `TIMESTAMP` | |

---

## `users` / `orders` Tables

Standard user and order tables. `orders.user_id` → `users.id` (FK).

---

## `import_log` Table

Tracks every file upload from the med-tech service.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `SERIAL` PK | |
| `filename` | `VARCHAR(500)` NOT NULL | Original uploaded filename |
| `source` | `VARCHAR(100)` | Default `'med-tech'` |
| `status` | `VARCHAR(20)` | `pending` / `in_progress` / `success` / `failed` |
| `rows_inserted` | `INTEGER` | New rows added |
| `rows_updated` | `INTEGER` | Existing rows upserted |
| `rows_failed` | `INTEGER` | Rows that failed |
| `error_message` | `TEXT` | Populated when `status = 'failed'` |
| `note` | `TEXT` | Free-text note from uploader |
| `started_at` | `TIMESTAMP` | When processing began |
| `finished_at` | `TIMESTAMP` | When processing completed/failed |
| `created_at` | `TIMESTAMP` NOT NULL | Auto |

---

## `query_sessions` / `query_history` Tables

Track every text-to-SQL query execution.

`query_history` fields: `session_id`, `user_message`, `table_name`, `generated_sql`, `success`, `row_count`, `error`, `llm_provider`, `llm_model`, `execution_time_ms`, `created_at`.

Logging is best-effort — failures never break the main request.

---

## Views

| View | Definition |
|------|------------|
| `active_drugs` | `SELECT id, name, category, price, stock FROM medicine_bid` |
| `drugs_by_category` | `SELECT category, count(*), avg(price) FROM medicine_bid GROUP BY category` |
| `expensive_items` | `SELECT name, category, price FROM items WHERE price > 50 ORDER BY price DESC` |

---

## Migrations

Managed by **Alembic**. Single migration file for v1:

```
alembic/versions/8f9881ec5d77_initial_schema.py
```

```bash
# Apply migrations
alembic upgrade head

# Check current revision
alembic current

# Roll back one step
alembic downgrade -1
```

Config: `alembic.ini` + `alembic/env.py` (reads DB URL from `~/.query-mcp/config.json`).

---

## REST Table IDs

REST endpoints use stable URL-safe table IDs derived from the table name:

```python
"src_" + hashlib.md5(table_name.encode()).hexdigest()[:8]
```

Example: `medicine_bid` → `src_<8-char-hash>`. Lookup via `_find_table_by_id()` in `server.py`.
