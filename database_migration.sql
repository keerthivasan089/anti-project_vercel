-- ============================================
-- MIGRATION: High-Impact Features
-- Run this on your PostgreSQL database
-- ============================================

-- 1. Add phone column to students table
ALTER TABLE students ADD COLUMN IF NOT EXISTS phone VARCHAR(20);

-- 2. Create attenders table
CREATE TABLE IF NOT EXISTS attenders (
    id SERIAL PRIMARY KEY,
    attendername VARCHAR(100) NOT NULL,
    attenderphone VARCHAR(20) UNIQUE NOT NULL,
    assignedbus INT,
    FOREIGN KEY (assignedbus) REFERENCES buses(id) ON DELETE SET NULL
);

-- 3. Create attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    bus_id INT NOT NULL,
    attender_id INT NOT NULL,
    attendance_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(10) NOT NULL CHECK (status IN ('present', 'absent')),
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (bus_id) REFERENCES buses(id) ON DELETE CASCADE,
    FOREIGN KEY (attender_id) REFERENCES attenders(id) ON DELETE CASCADE,
    UNIQUE(student_id, attendance_date)
);

-- 4. Seed demo attenders (one per bus)
INSERT INTO attenders (attendername, attenderphone, assignedbus) VALUES
('Thalli Attender', '8012345671', 1),
('Shoolagiri Attender', '8012345672', 2),
('Berigai Attender', '8012345673', 3),
('Bagalur Attender', '8012345674', 4),
('Mathigiri Attender', '8012345675', 5),
('SIPCOT Attender', '8012345676', 6),
('HosurBS Attender', '8012345677', 7),
('HosurRS Attender', '8012345678', 8),
('College Attender', '8012345679', 9)
ON CONFLICT (attenderphone) DO NOTHING;
