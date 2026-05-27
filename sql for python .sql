
CREATE DATABASE IF NOT EXISTS dairy_production_db 
CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dairy_production_db;


CREATE TABLE customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    external_id VARCHAR(20) UNIQUE COMMENT 'Идентификатор из JSON например id ',
    name VARCHAR(150) NOT NULL,
    inn VARCHAR(12) UNIQUE,
    address VARCHAR(255),
    phone VARCHAR(20),
    is_buyer BOOLEAN DEFAULT FALSE,
    is_seller BOOLEAN DEFAULT FALSE
);


CREATE TABLE materials (
    material_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    unit VARCHAR(10) DEFAULT 'кг',
    cost_per_unit DECIMAL(10,2) NOT NULL CHECK (cost_per_unit >= 0)
);


CREATE TABLE specifications (
    spec_id INT PRIMARY KEY AUTO_INCREMENT,
    spec_name VARCHAR(150) NOT NULL UNIQUE
);


CREATE TABLE spec_materials (
    spec_id INT NOT NULL,
    material_id INT NOT NULL,
    consumption_rate DECIMAL(10,4) NOT NULL CHECK (consumption_rate > 0),
    PRIMARY KEY (spec_id, material_id),
    FOREIGN KEY (spec_id) REFERENCES specifications(spec_id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materials(material_id) ON DELETE RESTRICT
);


CREATE TABLE products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    unit VARCHAR(10) DEFAULT 'шт',
    spec_id INT,
    FOREIGN KEY (spec_id) REFERENCES specifications(spec_id) ON DELETE SET NULL
);


CREATE TABLE orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    order_number VARCHAR(20) UNIQUE,
    order_date DATE NOT NULL,
    customer_id INT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT
);


CREATE TABLE order_items (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity DECIMAL(10,2) NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
    line_total DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
);
-- Запрос
SELECT
    o.order_id,
    o.order_number,
    o.order_date,
    c.name AS customer_name,


    SUM(oi.quantity * oi.unit_price) AS products_total,

    COALESCE(SUM(
                     oi.quantity * sm.consumption_rate * m.cost_per_unit
             ), 0) AS materials_total,

    SUM(oi.quantity * oi.unit_price) +
    COALESCE(SUM(oi.quantity * sm.consumption_rate * m.cost_per_unit), 0) AS grand_total

FROM orders o
         JOIN customers c ON o.customer_id = c.customer_id
         JOIN order_items oi ON o.order_id = oi.order_id
         JOIN products p ON oi.product_id = p.product_id

         LEFT JOIN specifications spec ON p.spec_id = spec.spec_id
         LEFT JOIN spec_materials sm ON spec.spec_id = sm.spec_id
         LEFT JOIN materials m ON sm.material_id = m.material_id

WHERE o.order_id = 2  -- или o.order_number = '2'

GROUP BY o.order_id, o.order_number, o.order_date, c.name
ORDER BY o.order_id;