-- Migration: 003_create_views
-- Description: Create reporting views

CREATE OR REPLACE VIEW active_drugs AS
SELECT id, name, category, price, stock
FROM drugs
WHERE status = 'active';

CREATE OR REPLACE VIEW drugs_by_category AS
SELECT category, COUNT(*) as drug_count, AVG(price) as avg_price
FROM drugs
GROUP BY category;

CREATE OR REPLACE VIEW expensive_items AS
SELECT name, category, price
FROM items
WHERE price > 50
ORDER BY price DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
