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

-- ============================================
-- MIGRATION 2: Advanced Features
-- ============================================

-- 5. Leave Requests
CREATE TABLE IF NOT EXISTS leave_requests (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    bus_id INT NOT NULL,
    leave_date DATE NOT NULL DEFAULT CURRENT_DATE,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (bus_id) REFERENCES buses(id) ON DELETE CASCADE,
    UNIQUE(student_id, leave_date)
);

-- 6. Emergency Alerts
CREATE TABLE IF NOT EXISTS emergency_alerts (
    id SERIAL PRIMARY KEY,
    bus_id INT NOT NULL,
    reporter_type VARCHAR(10) NOT NULL CHECK (reporter_type IN ('student', 'driver')),
    reporter_id INT NOT NULL,
    reporter_name VARCHAR(100),
    problem_type VARCHAR(50) DEFAULT 'general',
    description TEXT,
    voice_note_b64 TEXT,
    voice_note_type VARCHAR(20) DEFAULT 'audio/webm',
    upvote_count INT DEFAULT 1,
    status VARCHAR(10) DEFAULT 'active' CHECK (status IN ('active', 'resolved')),
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bus_id) REFERENCES buses(id) ON DELETE CASCADE
);

-- 7. Emergency Upvotes (prevent spam)
CREATE TABLE IF NOT EXISTS emergency_upvotes (
    id SERIAL PRIMARY KEY,
    alert_id INT NOT NULL,
    student_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alert_id, student_id),
    FOREIGN KEY (alert_id) REFERENCES emergency_alerts(id) ON DELETE CASCADE
);

-- 8. Notification Log
CREATE TABLE IF NOT EXISTS notification_log (
    id SERIAL PRIMARY KEY,
    recipient_phone VARCHAR(20),
    message_type VARCHAR(30),
    message TEXT,
    status VARCHAR(20) DEFAULT 'sent',
    provider VARCHAR(20) DEFAULT 'twilio',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Bus Trip Log for Geofencing
CREATE TABLE IF NOT EXISTS trip_log (
    id SERIAL PRIMARY KEY,
    bus_id INT NOT NULL,
    trip_date DATE NOT NULL DEFAULT CURRENT_DATE,
    departure_at TIMESTAMP,
    arrival_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed')),
    FOREIGN KEY (bus_id) REFERENCES buses(id) ON DELETE CASCADE,
    UNIQUE(bus_id, trip_date)
);
