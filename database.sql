-- PostgreSQL version of the database schema

-- BUSES TABLE (Fixed column names)
CREATE TABLE IF NOT EXISTS buses (
    id SERIAL PRIMARY KEY,
    busnumber VARCHAR(20) NOT NULL UNIQUE,
    drivername VARCHAR(100),
    driverphone VARCHAR(20) UNIQUE,
    isActive BOOLEAN DEFAULT FALSE
);

-- LOCATION UPDATES
CREATE TABLE IF NOT EXISTS locationupdates (
    id SERIAL PRIMARY KEY,
    busid INT,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    updatedat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (busid) REFERENCES buses(id) ON DELETE CASCADE
);

-- BUS STOPS (Fixed column names)
CREATE TABLE IF NOT EXISTS busstops (
    id SERIAL PRIMARY KEY,
    stopname VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8)
);

-- ROUTES
CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    routename VARCHAR(100) NOT NULL
);

-- ROUTE POINTS
CREATE TABLE IF NOT EXISTS routepoints (
    id SERIAL PRIMARY KEY,
    routeid INT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    sequenceorder INT,
    FOREIGN KEY (routeid) REFERENCES routes(id) ON DELETE CASCADE
);

-- STUDENTS TABLE (NEW)
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    rollnumber VARCHAR(20) UNIQUE NOT NULL,
    studentname VARCHAR(100) NOT NULL,
    dob DATE NOT NULL,
    assignedbus INT,
    assignedstop INT,
    FOREIGN KEY (assignedbus) REFERENCES buses(id),
    FOREIGN KEY (assignedstop) REFERENCES busstops(id)
);

-- NEW REGISTRATIONS TABLE (PENDING SUPS)
CREATE TABLE IF NOT EXISTS new_registrations (
    id SERIAL PRIMARY KEY,
    studentname VARCHAR(100) NOT NULL,
    rollnumber VARCHAR(20) UNIQUE NOT NULL,
    dob DATE NOT NULL,
    phone VARCHAR(20),
    preferred_stop INT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (preferred_stop) REFERENCES busstops(id)
);

-- 9 DEDICATED BUSES FOR 9 STOPS
INSERT INTO buses (id, busnumber, drivername, driverphone, isActive) VALUES 
(1, 'Bus-Thalli', 'Thalli Driver', '9012345671', TRUE),
(2, 'Bus-Shoolagiri', 'Shoolagiri Driver', '9012345672', TRUE),
(3, 'Bus-Berigai', 'Berigai Driver', '9012345673', TRUE),
(4, 'Bus-Bagalur', 'Bagalur Driver', '9012345674', TRUE),
(5, 'Bus-Mathigiri', 'Mathigiri Driver', '9012345675', TRUE),
(6, 'Bus-SIPCOT', 'SIPCOT Driver', '9012345676', TRUE),
(7, 'Bus-HosurBS', 'Hosur Driver', '9012345677', TRUE),
(8, 'Bus-HosurRS', 'Railway Driver', '9012345678', TRUE),
(9, 'Bus-College', 'College Driver', '9012345679', TRUE)
ON CONFLICT (id) DO NOTHING;

-- 9 REALISTIC STOPS (Fixed column name)
INSERT INTO busstops (stopname, latitude, longitude) VALUES
('Thalli', 12.588317, 77.652120),
('Shoolagiri', 12.666957, 78.014787),
('Berigai', 12.806014, 77.969881),
('Bagalur', 12.830309, 77.862998),
('Mathigiri', 12.7560, 77.8365),
('SIPCOT', 12.7384, 77.8439),
('Hosur Bus Stand', 12.735158, 77.827399),
('Hosur Railway Station', 12.718342, 77.822977),
('Adhiyamaan College of Engineering', 12.717849, 77.869604)
ON CONFLICT DO NOTHING;

-- DEMO STUDENTS
-- YOUR SPECIFIC STUDENTS (Replace existing students INSERT)
INSERT INTO students (rollnumber, studentname, dob, assignedbus, assignedstop) VALUES
('2403617610421056', 'KEERTHIVASAN', '2003-08-09', 1, 1),  -- Bus-Thalli
('2403617610421055', 'KISHORE', '2007-03-25', 2, 2),        -- Bus-Shoolagiri
('2403617610422054', 'KAVIYA', '2004-08-23', 3, 3),         -- Bus-Berigai
('2403617610421058', 'LOGUNATH', '2007-03-22', 7, 7),       -- Bus-HosurBS
('2403617610421033', 'GOS PATRICK AROKIA RAJ', '2005-11-10', 4, 4),
('2403617610421015', 'BOJAPRASATH', '2007-02-08', 5, 5)
ON CONFLICT (rollnumber) DO NOTHING;

-- INITIAL BUS LOCATIONS (Spread across routes)
INSERT INTO locationupdates (busid, latitude, longitude) VALUES 
(1, 12.717849, 77.869604), -- Bus-Thalli at College
(2, 12.666957, 78.014787), -- Bus-Shoolagiri at stop
(3, 12.806014, 77.969881), -- Bus-Berigai at stop
(4, 12.830309, 77.862998), -- Bus-Bagalur at stop
(5, 12.7560, 77.8365),     -- Bus-Mathigiri at stop
(6, 12.7384, 77.8439),     -- Bus-SIPCOT at stop
(7, 12.735158, 77.827399), -- Bus-HosurBS at stop
(8, 12.718342, 77.822977), -- Bus-HosurRS at stop
(9, 12.717849, 77.869604)  -- Bus-College at college
ON CONFLICT DO NOTHING;
