-- MediLink Database Schema
CREATE DATABASE IF NOT EXISTS medilink CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE medilink;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('patient', 'chemist', 'admin') DEFAULT 'patient',
    phone VARCHAR(20),
    address TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chemists (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    shop_name VARCHAR(200) NOT NULL,
    license_no VARCHAR(100),
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    address TEXT,
    phone VARCHAR(20),
    is_active TINYINT(1) DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chemist_id INT NOT NULL,
    name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200),
    category VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,
    stock INT DEFAULT 0,
    unit VARCHAR(50) DEFAULT 'strip',
    description TEXT,
    is_available TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chemist_id) REFERENCES chemists(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    notes TEXT,
    is_verified TINYINT(1) DEFAULT 0,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS medical_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    raw_text TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS health_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    report_id INT,
    blood_pressure VARCHAR(20),
    sugar VARCHAR(50),
    hemoglobin VARCHAR(20),
    cholesterol VARCHAR(50),
    heart_rate VARCHAR(20),
    weight VARCHAR(20),
    height VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (report_id) REFERENCES medical_reports(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    chemist_id INT NOT NULL,
    prescription_id INT,
    status ENUM('pending','processing','ready','delivered','cancelled') DEFAULT 'pending',
    total_amount DECIMAL(10,2) DEFAULT 0.00,
    notes TEXT,
    is_emergency TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES users(id),
    FOREIGN KEY (chemist_id) REFERENCES chemists(id),
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    medicine_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);

-- Default Admin Account (password: admin123)
INSERT IGNORE INTO users (name, email, password, role, phone) VALUES
('Admin User', 'admin@medilink.com', 'pbkdf2:sha256:260000$admin123hashed', 'admin', '9999999999');
