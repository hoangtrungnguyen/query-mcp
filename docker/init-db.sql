-- Sample database initialization script for Query MCP testing

-- Create drugs table
CREATE TABLE IF NOT EXISTS drugs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    stock INTEGER,
    status VARCHAR(50),
    manufacturer VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create items table
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    status VARCHAR(50),
    quantity INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create orders table
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total DECIMAL(10, 2),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample drugs data
INSERT INTO drugs (name, category, price, stock, status, manufacturer) VALUES
('Aspirin', 'Pain Relief', 9.99, 500, 'active', 'Bayer'),
('Ibuprofen', 'Pain Relief', 12.99, 450, 'active', 'Advil'),
('Acetaminophen', 'Pain Relief', 8.99, 600, 'active', 'Tylenol'),
('Amoxicillin', 'Antibiotic', 24.99, 200, 'active', 'Generic'),
('Ciprofloxacin', 'Antibiotic', 35.99, 150, 'active', 'Generic'),
('Metformin', 'Diabetes', 15.99, 300, 'active', 'Generic'),
('Lisinopril', 'Hypertension', 19.99, 250, 'active', 'Generic'),
('Atorvastatin', 'Cholesterol', 22.99, 280, 'active', 'Generic'),
('Omeprazole', 'Antacid', 14.99, 350, 'active', 'Generic'),
('Sertraline', 'Antidepressant', 18.99, 200, 'active', 'Generic'),
('Loratadine', 'Antihistamine', 11.99, 400, 'active', 'Generic'),
('Cetirizine', 'Antihistamine', 10.99, 450, 'active', 'Generic'),
('Fluoxetine', 'Antidepressant', 20.99, 180, 'inactive', 'Generic'),
('Clopidogrel', 'Antiplatelet', 45.99, 100, 'active', 'Generic'),
('Warfarin', 'Anticoagulant', 28.99, 120, 'active', 'Generic');

-- Insert sample items data
INSERT INTO items (name, category, price, status, quantity) VALUES
('Widget A', 'Electronics', 49.99, 'active', 100),
('Widget B', 'Electronics', 79.99, 'active', 50),
('Gadget X', 'Gadgets', 99.99, 'active', 25),
('Gadget Y', 'Gadgets', 149.99, 'active', 15),
('Tool Z', 'Tools', 199.99, 'active', 8),
('Book 1', 'Books', 19.99, 'active', 200),
('Book 2', 'Books', 24.99, 'active', 150),
('Pen Set', 'Office', 14.99, 'inactive', 500),
('Notebook', 'Office', 9.99, 'active', 1000),
('Keyboard', 'Electronics', 79.99, 'active', 60);

-- Insert sample users data
INSERT INTO users (name, email, status) VALUES
('John Doe', 'john@example.com', 'active'),
('Jane Smith', 'jane@example.com', 'active'),
('Bob Johnson', 'bob@example.com', 'active'),
('Alice Brown', 'alice@example.com', 'inactive'),
('Charlie Davis', 'charlie@example.com', 'active'),
('Eva Martinez', 'eva@example.com', 'active'),
('Frank Wilson', 'frank@example.com', 'active'),
('Grace Lee', 'grace@example.com', 'inactive'),
('Henry Taylor', 'henry@example.com', 'active'),
('Ivy Anderson', 'ivy@example.com', 'active');

-- Insert sample orders data
INSERT INTO orders (user_id, total, status) VALUES
(1, 149.97, 'completed'),
(2, 99.99, 'completed'),
(3, 199.98, 'pending'),
(1, 79.99, 'completed'),
(5, 299.97, 'completed'),
(2, 149.98, 'pending'),
(6, 449.97, 'completed'),
(7, 99.99, 'pending'),
(1, 349.96, 'completed'),
(8, 199.98, 'completed');

-- Create indexes for better query performance
CREATE INDEX idx_drugs_category ON drugs(category);
CREATE INDEX idx_drugs_status ON drugs(status);
CREATE INDEX idx_drugs_price ON drugs(price);
CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_items_status ON items(status);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- Create sample views
CREATE VIEW active_drugs AS
SELECT id, name, category, price, stock
FROM drugs
WHERE status = 'active';

CREATE VIEW drugs_by_category AS
SELECT category, COUNT(*) as drug_count, AVG(price) as avg_price
FROM drugs
GROUP BY category;

CREATE VIEW expensive_items AS
SELECT name, category, price
FROM items
WHERE price > 50
ORDER BY price DESC;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Finished initialization
\echo 'Database initialized successfully!'
\echo 'Tables created: drugs, items, users, orders'
\echo 'Sample data inserted'
\echo 'Views created: active_drugs, drugs_by_category, expensive_items'
