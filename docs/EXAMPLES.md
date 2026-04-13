# Query MCP - SQL Query Examples

Real-world SQL query examples with explanations.

## Simple SELECT Queries

### Example 1: List All Drugs

**User:** "Show me all drugs"

**Generated SQL:**
```sql
SELECT * FROM drugs LIMIT 100;
```

**Result:** All 15 sample drugs

---

### Example 2: Filter by Price

**User:** "Show me drugs under $20"

**Generated SQL:**
```sql
SELECT * FROM drugs WHERE price < 20 ORDER BY price ASC;
```

**Result:** Aspirin, Acetaminophen, Metformin, etc.

---

### Example 3: Order by Price

**User:** "Show me the most expensive drugs"

**Generated SQL:**
```sql
SELECT * FROM drugs ORDER BY price DESC LIMIT 10;
```

**Result:** Clopidogrel ($45.99), Warfarin ($28.99), etc.

---

## Filtering Queries

### Example 4: Filter by Status

**User:** "Find all active drugs"

**Generated SQL:**
```sql
SELECT * FROM drugs WHERE status = 'active';
```

**Result:** 14 active drugs (Fluoxetine is inactive)

---

### Example 5: Multiple Conditions

**User:** "Find active drugs with price between $10 and $30"

**Generated SQL:**
```sql
SELECT * FROM drugs 
WHERE status = 'active' 
AND price >= 10 
AND price <= 30 
ORDER BY price;
```

**Result:** Omeprazole, Lisinopril, Atorvastatin, etc.

---

### Example 6: Text Search

**User:** "Find all drugs with 'anti' in the name"

**Generated SQL:**
```sql
SELECT * FROM drugs 
WHERE name ILIKE '%anti%' 
ORDER BY name;
```

**Result:** Antibiotic, Antidepressant, Antihistamine, Antiplatelet, Anticoagulant drugs

---

## Aggregation Queries

### Example 7: Count by Category

**User:** "How many drugs are in each category?"

**Generated SQL:**
```sql
SELECT category, COUNT(*) as drug_count 
FROM drugs 
GROUP BY category 
ORDER BY drug_count DESC;
```

**Result:**
```
category          | drug_count
------------------|----------
Pain Relief       | 3
Antibiotic        | 2
Antidepressant    | 2
...               | ...
```

---

### Example 8: Average Price by Category

**User:** "What's the average price per drug category?"

**Generated SQL:**
```sql
SELECT category, AVG(price) as avg_price 
FROM drugs 
GROUP BY category 
ORDER BY avg_price DESC;
```

**Result:**
```
category          | avg_price
------------------|----------
Antiplatelet      | 45.99
Anticoagulant     | 28.99
Antibiotic        | 30.49
...               | ...
```

---

### Example 9: Count Total Stock

**User:** "What's the total stock across all drugs?"

**Generated SQL:**
```sql
SELECT SUM(stock) as total_stock 
FROM drugs;
```

**Result:** `4255` (total units)

---

### Example 10: Most Stocked Item

**User:** "Which drug has the most stock?"

**Generated SQL:**
```sql
SELECT name, stock 
FROM drugs 
ORDER BY stock DESC 
LIMIT 1;
```

**Result:** Acetaminophen with 600 units

---

## JOIN Queries

### Example 11: Orders with User Names

**User:** "Show me all orders with customer names"

**Generated SQL:**
```sql
SELECT u.name, o.id, o.total, o.status 
FROM orders o 
JOIN users u ON o.user_id = u.id 
ORDER BY o.total DESC;
```

**Result:** Displays order details with customer names

---

### Example 12: User Purchase Summary

**User:** "How much has each user spent?"

**Generated SQL:**
```sql
SELECT u.name, COUNT(o.id) as order_count, COALESCE(SUM(o.total), 0) as total_spent 
FROM users u 
LEFT JOIN orders o ON u.id = o.user_id 
GROUP BY u.id, u.name 
ORDER BY total_spent DESC;
```

**Result:** User spending summary

---

## Complex Queries

### Example 13: Drugs by Price Range

**User:** "Categorize drugs into price ranges: cheap (<$15), medium ($15-$30), expensive (>$30)"

**Generated SQL:**
```sql
SELECT 
  CASE 
    WHEN price < 15 THEN 'Cheap'
    WHEN price >= 15 AND price < 30 THEN 'Medium'
    ELSE 'Expensive'
  END as price_range,
  COUNT(*) as drug_count,
  AVG(price) as avg_price
FROM drugs
GROUP BY price_range
ORDER BY avg_price;
```

**Result:** Price range distribution

---

### Example 14: High-Value Orders

**User:** "Find orders over $200 with customer details"

**Generated SQL:**
```sql
SELECT u.name, u.email, o.id, o.total, o.status, o.created_at 
FROM orders o 
JOIN users u ON o.user_id = u.id 
WHERE o.total > 200 
ORDER BY o.total DESC;
```

**Result:** High-value customer orders

---

### Example 15: Items on Sale

**User:** "Show me all items in Electronics category under $100"

**Generated SQL:**
```sql
SELECT name, category, price, quantity, status 
FROM items 
WHERE category = 'Electronics' 
AND price < 100 
AND status = 'active' 
ORDER BY price DESC;
```

**Result:** Electronics within budget

---

## VIEW Queries

### Example 16: Active Drugs (from view)

**User:** "Show me all active drugs with price and stock"

**Generated SQL:**
```sql
SELECT * FROM active_drugs ORDER BY price DESC;
```

**Result:** Uses pre-defined view: id, name, category, price, stock

---

### Example 17: Drugs by Category (from view)

**User:** "Give me the category breakdown with average prices"

**Generated SQL:**
```sql
SELECT * FROM drugs_by_category ORDER BY drug_count DESC;
```

**Result:** Category summary: category, drug_count, avg_price

---

### Example 18: Expensive Items (from view)

**User:** "What are the most expensive items we carry?"

**Generated SQL:**
```sql
SELECT * FROM expensive_items;
```

**Result:** Items over $50 sorted by price

---

## Edge Case Queries

### Example 19: NULL Handling

**User:** "Find users who haven't placed any orders"

**Generated SQL:**
```sql
SELECT u.* 
FROM users u 
LEFT JOIN orders o ON u.id = o.user_id 
WHERE o.id IS NULL;
```

**Result:** Users with no orders

---

### Example 20: HAVING Clause

**User:** "Which categories have more than 2 drugs?"

**Generated SQL:**
```sql
SELECT category, COUNT(*) as drug_count 
FROM drugs 
GROUP BY category 
HAVING COUNT(*) > 2 
ORDER BY drug_count DESC;
```

**Result:** Categories with multiple drugs

---

## Performance Considerations

### Good Queries (Indexed)
```sql
-- Uses indexes
SELECT * FROM drugs WHERE price > 100;
SELECT * FROM users WHERE status = 'active';
SELECT * FROM orders WHERE user_id = 5;
```

### Queries to Avoid (Slow)
```sql
-- Full table scans
SELECT * FROM drugs WHERE name LIKE '%drug%';
SELECT * FROM orders WHERE EXTRACT(YEAR FROM created_at) = 2026;
```

---

## Query Patterns

### Pattern 1: Recent Activity
```sql
SELECT * FROM orders 
ORDER BY created_at DESC 
LIMIT 10;
```

### Pattern 2: Top N Items
```sql
SELECT name, price FROM drugs 
ORDER BY price DESC 
LIMIT 5;
```

### Pattern 3: Group and Count
```sql
SELECT category, COUNT(*) FROM drugs 
GROUP BY category 
ORDER BY COUNT(*) DESC;
```

### Pattern 4: Join with Aggregation
```sql
SELECT u.name, COUNT(o.id) 
FROM users u 
LEFT JOIN orders o ON u.id = o.user_id 
GROUP BY u.id, u.name;
```

---

## How to Use These Examples

1. **In Claude:** Paste any example query
2. **Ask Claude:** "Run this query on the drugs table"
3. **Modify:** Ask Claude to modify for your needs
4. **Learn:** Understand the SQL patterns used

---

## Sample Data Reference

### drugs table (15 rows)
- Columns: id, name, category, price, stock, status, manufacturer
- Categories: Pain Relief, Antibiotic, Diabetes, Hypertension, etc.
- Price range: $8.99 - $45.99

### items table (10 rows)
- Columns: id, name, category, price, status, quantity
- Categories: Electronics, Gadgets, Tools, Books, Office
- Price range: $9.99 - $199.99

### users table (10 rows)
- Columns: id, name, email, status
- Status: active, inactive

### orders table (10 rows)
- Columns: id, user_id, total, status
- Status: completed, pending

---

## Advanced SQL Features

### Window Functions
```sql
SELECT name, price,
  ROW_NUMBER() OVER (ORDER BY price DESC) as rank
FROM drugs;
```

### Subqueries
```sql
SELECT * FROM drugs
WHERE price > (SELECT AVG(price) FROM drugs);
```

### UNION
```sql
SELECT name, price FROM drugs WHERE status = 'active'
UNION
SELECT name, price FROM items WHERE status = 'active';
```

---

## Tips for Better Queries

1. **Be Specific:** "Show me active drugs under $20" not "Show me drugs"
2. **Mention Order:** "...sorted by price" or "...top 10"
3. **Use Conditions:** "where status = active" filters better than general queries
4. **Ask for Aggregates:** "count", "total", "average" triggers GROUP BY
5. **Include JOINs When Needed:** "orders with customer names" indicates JOIN

---

See [API_REFERENCE.md](API_REFERENCE.md) for tool parameters.
