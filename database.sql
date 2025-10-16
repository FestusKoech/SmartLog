-- database.sql
-- Database schema for School Laptop Tracking System

CREATE DATABASE IF NOT EXISTS Gate_logs CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE school_logs;

-- -----------------------------
-- STAFF
-- -----------------------------
CREATE TABLE IF NOT EXISTS staff (
  id INT AUTO_INCREMENT PRIMARY KEY,
  staffID VARCHAR(50) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  phone VARCHAR(30),
  role ENUM('admin','staff') DEFAULT 'staff',
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------
-- STUDENTS
-- -----------------------------
CREATE TABLE IF NOT EXISTS students (
  id INT AUTO_INCREMENT PRIMARY KEY,
  studentID VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  phone VARCHAR(30),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------
-- LAPTOPS
-- -----------------------------
CREATE TABLE IF NOT EXISTS laptops (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  studentID VARCHAR(50) NOT NULL,
  phone VARCHAR(30),
  serial_number VARCHAR(100) NOT NULL UNIQUE,
  make VARCHAR(50),
  model VARCHAR(50),
  signed_in BOOLEAN DEFAULT 0,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ts_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_studentID FOREIGN KEY (studentID) REFERENCES students(studentID) ON DELETE CASCADE ON UPDATE CASCADE
);

-- -----------------------------
-- LOGS
-- -----------------------------
CREATE TABLE IF NOT EXISTS logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  device_id VARCHAR(100) NOT NULL,
  action ENUM('signin','signout') NOT NULL,
  gate_id VARCHAR(50),
  meta VARCHAR(255),
  ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Example Indexes for performance
CREATE INDEX idx_logs_device_action ON logs (device_id, action);
CREATE INDEX idx_laptops_serial ON laptops (serial_number);
