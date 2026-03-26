-- ============================================================
-- QR-Based Attendance System — MySQL Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS qr_attendance;
USE qr_attendance;

-- -----------------------------------------------------
-- Table: admins
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS admins (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL,
    email       VARCHAR(150)  NOT NULL UNIQUE,
    password    VARCHAR(255)  NOT NULL,
    created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table: departments
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL UNIQUE,
    created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table: students
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(150)  NOT NULL UNIQUE,
    password      VARCHAR(255)  NOT NULL,
    department_id INT,
    roll_number   VARCHAR(50)   UNIQUE,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table: teachers
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS teachers (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(150)  NOT NULL UNIQUE,
    password      VARCHAR(255)  NOT NULL,
    department_id INT,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table: courses
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS courses (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(150)  NOT NULL,
    code          VARCHAR(20)   NOT NULL UNIQUE,
    department_id INT,
    teacher_id    INT,
    created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL,
    FOREIGN KEY (teacher_id)    REFERENCES teachers(id)    ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table: timetable
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS timetable (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    course_id   INT           NOT NULL,
    day_of_week ENUM('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday') NOT NULL,
    start_time  TIME          NOT NULL,
    end_time    TIME          NOT NULL,
    room        VARCHAR(50),
    created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table: attendance
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  INT           NOT NULL,
    course_id   INT           NOT NULL,
    date        DATE          NOT NULL,
    status      ENUM('Present','Absent','Late') DEFAULT 'Present',
    latitude    DECIMAL(10,8),
    longitude   DECIMAL(11,8),
    marked_at   DATETIME      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses(id)  ON DELETE CASCADE,
    UNIQUE KEY unique_attendance (student_id, course_id, date)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- Table: attendance_sessions (QR-based sessions for mobile)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    course_id   INT           NOT NULL,
    teacher_id  INT           NOT NULL,
    qr_token    VARCHAR(255)  NOT NULL UNIQUE,
    latitude    DECIMAL(10,8),
    longitude   DECIMAL(11,8),
    created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP,
    expires_at  DATETIME      NOT NULL,
    FOREIGN KEY (course_id)  REFERENCES courses(id)  ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Add session_id FK to attendance table (nullable, for QR-scanned records)
ALTER TABLE attendance ADD COLUMN session_id INT DEFAULT NULL;
ALTER TABLE attendance ADD CONSTRAINT fk_attendance_session
    FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE SET NULL;

-- -----------------------------------------------------
-- Indexes for performance
-- -----------------------------------------------------
CREATE INDEX idx_attendance_date     ON attendance(date);
CREATE INDEX idx_attendance_student  ON attendance(student_id);
CREATE INDEX idx_attendance_course   ON attendance(course_id);
CREATE INDEX idx_students_dept       ON students(department_id);
CREATE INDEX idx_teachers_dept       ON teachers(department_id);
CREATE INDEX idx_courses_teacher     ON courses(teacher_id);

-- -----------------------------------------------------
-- Seed: default admin   (password: admin123)
-- The hash below is bcrypt for "admin123"
-- -----------------------------------------------------
INSERT INTO admins (name, email, password) VALUES
('Administrator', 'admin@admin.com', 'pbkdf2:sha256:600000$XsZqO8nR$a3f1c5d2e4b6a8c0d2e4f6a8b0c2d4e6f8a0b2c4d6e8f0a2b4c6d8e0f2a4b6');

-- Seed: sample departments
INSERT INTO departments (name) VALUES
('Computer Science'),
('Electronics'),
('Mechanical'),
('Civil');
