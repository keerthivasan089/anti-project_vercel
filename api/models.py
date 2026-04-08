import psycopg2
import psycopg2.extras
from api.config import Config
from flask import current_app
import time
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Dictionary to track the last manual (driver) update time per bus
REAL_TIME_LOCKS = {}

def get_db_connection():
    try:
        if not Config.DATABASE_URL:
            print("❌ DATABASE_URL not set")
            return None
        connection = psycopg2.connect(Config.DATABASE_URL)
        return connection
    except psycopg2.Error as err:
        print(f"❌ DB Error: {err}")
        return None

# =============================================
# BUS MODEL
# =============================================
class BusModel:
    @staticmethod
    def get_all_buses():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM buses")
        buses = cursor.fetchall()
        cursor.close()
        conn.close()
        return buses

    @staticmethod
    def get_bus_by_auth(bus_id, driverphone): 
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM buses 
            WHERE id = %s AND driverphone = %s
        """, (bus_id, driverphone))
        bus = cursor.fetchone()
        cursor.close()
        conn.close()
        return bus

    @staticmethod
    def update_location(busid, lat, lng, is_simulation=False):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        current_time = time.time()
        
        if not is_simulation:
            REAL_TIME_LOCKS[busid] = current_time
        else:
            last_real_update = REAL_TIME_LOCKS.get(busid, 0)
            if current_time - last_real_update < 120:
                cursor.close()
                conn.close()
                return True

        cursor.execute("SELECT id FROM locationupdates WHERE busid = %s", (busid,))
        record = cursor.fetchone()
        
        if record:
            cursor.execute("""
                UPDATE locationupdates 
                SET latitude = %s, longitude = %s, updatedat = CURRENT_TIMESTAMP
                WHERE busid = %s
            """, (lat, lng, busid))
        else:
            cursor.execute("""
                INSERT INTO locationupdates (busid, latitude, longitude) 
                VALUES (%s, %s, %s)
            """, (busid, lat, lng))
            
        conn.commit()
        cursor.close()
        conn.close()
        return True

    @staticmethod
    def get_all_locations():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT b.id, b.busnumber, b.drivername, b.isActive, 
                   l.latitude, l.longitude, l.updatedat
            FROM buses b
            JOIN locationupdates l ON b.id = l.busid
        """)
        locations = cursor.fetchall()
        
        for loc in locations:
            if loc.get('latitude') is not None:
                loc['latitude'] = float(loc['latitude'])
            if loc.get('longitude') is not None:
                loc['longitude'] = float(loc['longitude'])
            if loc.get('updatedat') is not None:
                loc['updatedat'] = loc['updatedat'].isoformat()
                
        cursor.close()
        conn.close()
        return locations

    @staticmethod
    def get_buses_with_stops():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT id, busnumber FROM buses ORDER BY id")
        buses = cursor.fetchall()
        cursor.close()
        conn.close()
        return buses

# =============================================
# ADMIN MODEL
# =============================================
class AdminModel:
    @staticmethod
    def add_student(rollnumber, name, dob, bus_id, stop_id, student_id=None, phone=None):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if student_id:
                cursor.execute("""
                    UPDATE students SET 
                        rollnumber = %s,
                        studentname = %s,
                        dob = %s,
                        assignedbus = %s,
                        assignedstop = %s,
                        phone = %s
                    WHERE id = %s
                """, (rollnumber, name, dob, bus_id, stop_id, phone, student_id))
            else:
                cursor.execute("""
                    INSERT INTO students (rollnumber, studentname, dob, assignedbus, assignedstop, phone)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (rollnumber) DO UPDATE SET
                        studentname = EXCLUDED.studentname,
                        dob = EXCLUDED.dob,
                        assignedbus = EXCLUDED.assignedbus,
                        assignedstop = EXCLUDED.assignedstop,
                        phone = EXCLUDED.phone
                """, (rollnumber, name, dob, bus_id, stop_id, phone))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Admin Add Student Error: {e}")
            return False
        finally:
            if conn:
                cursor.close()
                conn.close()

    @staticmethod
    def add_or_update_driver(busnumber, drivername, driverphone, bus_id=None):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if bus_id:
                cursor.execute("""
                    UPDATE buses SET busnumber = %s, drivername = %s, driverphone = %s, isActive = TRUE 
                    WHERE id = %s
                """, (busnumber, drivername, driverphone, bus_id))
            else:
                cursor.execute("""
                    UPDATE buses SET drivername = %s, driverphone = %s, isActive = TRUE 
                    WHERE busnumber = %s
                """, (drivername, driverphone, busnumber))
                
                if cursor.rowcount == 0:
                     cursor.execute("""
                        INSERT INTO buses (busnumber, drivername, driverphone, isActive)
                        VALUES (%s, %s, %s, TRUE)
                    """, (busnumber, drivername, driverphone))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Admin Add Driver Error: {e}")
            return False
        finally:
             if conn:
                cursor.close()
                conn.close()

    @staticmethod
    def get_all_students():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT s.*, b.busnumber as assigned_bus_name, st.stopname as assigned_stop_name 
            FROM students s 
            LEFT JOIN buses b ON s.assignedbus = b.id
            LEFT JOIN busstops st ON s.assignedstop = st.id
            ORDER BY s.id DESC
        """)
        students = cursor.fetchall()
        
        for st in students:
            if st.get('dob'):
                st['dob'] = st['dob'].isoformat() if hasattr(st['dob'], 'isoformat') else str(st['dob'])
                
        cursor.close()
        conn.close()
        return students

    @staticmethod
    def delete_student(student_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Admin Delete Student Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def delete_bus(bus_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("DELETE FROM buses WHERE id = %s", (bus_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Admin Delete Bus Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

# =============================================
# ATTENDER MODEL
# =============================================
class AttenderModel:
    @staticmethod
    def get_by_auth(bus_id, attenderphone):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT a.*, b.busnumber 
            FROM attenders a
            LEFT JOIN buses b ON a.assignedbus = b.id
            WHERE a.assignedbus = %s AND a.attenderphone = %s
        """, (bus_id, attenderphone))
        attender = cursor.fetchone()
        cursor.close()
        conn.close()
        return attender

    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT a.*, b.busnumber as assigned_bus_name
            FROM attenders a
            LEFT JOIN buses b ON a.assignedbus = b.id
            ORDER BY a.id
        """)
        attenders = cursor.fetchall()
        cursor.close()
        conn.close()
        return attenders

    @staticmethod
    def add_or_update(attendername, attenderphone, assignedbus, attender_id=None):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            if attender_id:
                cursor.execute("""
                    UPDATE attenders SET attendername = %s, attenderphone = %s, assignedbus = %s
                    WHERE id = %s
                """, (attendername, attenderphone, assignedbus, attender_id))
            else:
                cursor.execute("""
                    INSERT INTO attenders (attendername, attenderphone, assignedbus)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (attenderphone) DO UPDATE SET
                        attendername = EXCLUDED.attendername,
                        assignedbus = EXCLUDED.assignedbus
                """, (attendername, attenderphone, assignedbus))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Attender Add/Update Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def delete(attender_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("DELETE FROM attenders WHERE id = %s", (attender_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Attender Delete Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

# =============================================
# ATTENDANCE MODEL
# =============================================
class AttendanceModel:
    @staticmethod
    def get_students_for_bus(bus_id):
        """Get all students assigned to a bus, with today's attendance status."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT s.id, s.rollnumber, s.studentname, s.phone,
                   st.stopname as assigned_stop_name,
                   a.status as today_status
            FROM students s
            LEFT JOIN busstops st ON s.assignedstop = st.id
            LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = CURRENT_DATE
            WHERE s.assignedbus = %s
            ORDER BY s.studentname
        """, (bus_id,))
        students = cursor.fetchall()
        cursor.close()
        conn.close()
        return students

    @staticmethod
    def mark_attendance(student_id, bus_id, attender_id, status):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                INSERT INTO attendance (student_id, bus_id, attender_id, attendance_date, status)
                VALUES (%s, %s, %s, CURRENT_DATE, %s)
                ON CONFLICT (student_id, attendance_date) DO UPDATE SET
                    status = EXCLUDED.status,
                    attender_id = EXCLUDED.attender_id,
                    marked_at = CURRENT_TIMESTAMP
            """, (student_id, bus_id, attender_id, status))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Mark Attendance Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def get_today_summary(bus_id):
        """Get today's attendance summary for a bus."""
        conn = get_db_connection()
        if not conn: return {"total": 0, "present": 0, "absent": 0}
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present,
                COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id AND a.attendance_date = CURRENT_DATE
            WHERE s.assignedbus = %s
        """, (bus_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result or {"total": 0, "present": 0, "absent": 0}

    @staticmethod
    def get_all_today_summary():
        """Get overall attendance summary for admin dashboard."""
        conn = get_db_connection()
        if not conn: return {"total_students": 0, "marked": 0, "present": 0, "absent": 0}
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM students) as total_students,
                COUNT(a.id) as marked,
                COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present,
                COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent
            FROM attendance a
            WHERE a.attendance_date = CURRENT_DATE
        """)
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result or {"total_students": 0, "marked": 0, "present": 0, "absent": 0}

    @staticmethod
    def get_attendance_by_date(bus_id, date_str):
        """Get attendance for a specific date (for admin history view)."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT s.rollnumber, s.studentname, a.status, a.marked_at
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            WHERE a.bus_id = %s AND a.attendance_date = %s
            ORDER BY s.studentname
        """, (bus_id, date_str))
        records = cursor.fetchall()
        for r in records:
            if r.get('marked_at'):
                r['marked_at'] = r['marked_at'].isoformat()
        cursor.close()
        conn.close()
        return records

# =============================================
# ADMIN AUTH (Password Hashing)
# =============================================
class AdminAuthModel:
    # Default hash for 'admin123' — generated with werkzeug
    DEFAULT_HASH = generate_password_hash('admin123')
    
    @staticmethod
    def verify(username, password):
        """Verify admin credentials. Uses env var ADMIN_PASSWORD_HASH if set, otherwise defaults."""
        if username != 'admin':
            return False
        
        stored_hash = os.environ.get('ADMIN_PASSWORD_HASH', AdminAuthModel.DEFAULT_HASH)
        return check_password_hash(stored_hash, password)

# =============================================
# REGISTRATION MODEL
# =============================================
class RegistrationModel:
    @staticmethod
    def add_registration(name, roll_no, dob, phone, stop_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                INSERT INTO new_registrations (studentname, rollnumber, dob, phone, preferred_stop)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, roll_no, dob, phone, stop_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Registration Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def get_status(roll_number):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT status FROM new_registrations WHERE rollnumber = %s", (roll_number,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result['status'] if result else None

    @staticmethod
    def get_pending():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT r.*, s.stopname as preferred_stop_name 
            FROM new_registrations r 
            LEFT JOIN busstops s ON r.preferred_stop = s.id 
            WHERE r.status = 'pending'
        """)
        results = cursor.fetchall()
        for r in results:
            if r.get('dob'): r['dob'] = str(r['dob'])
            if r.get('created_at'): r['created_at'] = str(r['created_at'])
        cursor.close()
        conn.close()
        return results

    @staticmethod
    def update_status(reg_id, status):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("UPDATE new_registrations SET status = %s WHERE id = %s", (status, reg_id))
            conn.commit()
            return True
        except Exception as e:
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def get_registration_by_id(reg_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM new_registrations WHERE id = %s", (reg_id,))
        record = cursor.fetchone()
        if record and record.get('dob'): record['dob'] = str(record['dob'])
        cursor.close()
        conn.close()
        return record

# =============================================
# STOP MODEL
# =============================================
class StopModel:
    @staticmethod
    def get_all_stops():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM busstops")
        stops = cursor.fetchall()

        for stop in stops:
            if stop.get('latitude') is not None:
                stop['latitude'] = float(stop['latitude'])
            if stop.get('longitude') is not None:
                stop['longitude'] = float(stop['longitude'])

        cursor.close()
        conn.close()
        return stops

# =============================================
# STUDENT LOGIN
# =============================================
def get_student_by_auth(rollnumber, dob):
    print(f"🔍 Searching student: {rollnumber} | {dob}")
    
    possible_dobs = [dob]
    
    from datetime import datetime
    
    normalized_dob = dob.replace('/', '-')
    
    try:
        parsed1 = datetime.strptime(normalized_dob, "%d-%m-%Y")
        possible_dobs.append(parsed1.strftime("%Y-%m-%d"))
    except ValueError:
        pass
        
    try:
        parsed2 = datetime.strptime(normalized_dob, "%m-%d-%Y")
        possible_dobs.append(parsed2.strftime("%Y-%m-%d"))
    except ValueError:
        pass

    print(f"📅 Checking all these possible DOB formats: {possible_dobs}")

    conn = get_db_connection()
    if not conn:
        print("❌ NO DB CONNECTION")
        return None
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        placeholders = ', '.join(['%s'] * len(possible_dobs))
        query = f"""
            SELECT s.*, b.busnumber as assigned_bus_name, st.stopname as assigned_stop_name 
            FROM students s 
            LEFT JOIN buses b ON s.assignedbus = b.id
            LEFT JOIN busstops st ON s.assignedstop = st.id
            WHERE s.rollnumber = %s AND s.dob IN ({placeholders})
        """
        params = [rollnumber] + possible_dobs
        cursor.execute(query, tuple(params))
        
        student = cursor.fetchone()
        if student:
            print(f"✅ FOUND: {student['studentname']} - Bus: {student.get('assigned_bus_name')}")
        else:
            print("❌ Student NOT FOUND")
        return student
    except Exception as e:
        print(f"❌ QUERY ERROR: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# =============================================
# LEAVE MODEL
# =============================================
class LeaveModel:
    @staticmethod
    def request_leave(student_id, bus_id, reason=None):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                INSERT INTO leave_requests (student_id, bus_id, leave_date, reason)
                VALUES (%s, %s, CURRENT_DATE, %s)
                ON CONFLICT (student_id, leave_date) DO UPDATE SET reason = EXCLUDED.reason
            """, (student_id, bus_id, reason))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Leave Request Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def get_today_leave(student_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM leave_requests
            WHERE student_id = %s AND leave_date = CURRENT_DATE
        """, (student_id,))
        result = cursor.fetchone()
        cursor.close(); conn.close()
        return result

    @staticmethod
    def get_bus_leaves_today(bus_id):
        """Get all students on leave today for a given bus (for attender dashboard)."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT l.student_id, s.studentname, s.rollnumber, l.reason
            FROM leave_requests l
            JOIN students s ON l.student_id = s.id
            WHERE l.bus_id = %s AND l.leave_date = CURRENT_DATE
        """, (bus_id,))
        results = cursor.fetchall()
        cursor.close(); conn.close()
        return results

    @staticmethod
    def cancel_leave(student_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                DELETE FROM leave_requests
                WHERE student_id = %s AND leave_date = CURRENT_DATE
            """, (student_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Cancel Leave Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()


# =============================================
# EMERGENCY MODEL
# =============================================
class EmergencyModel:
    MASS_ALERT_THRESHOLD = 5  # Number of upvotes to trigger admin mass alert

    @staticmethod
    def create_alert(bus_id, reporter_type, reporter_id, reporter_name,
                     problem_type, description, voice_note_b64=None, voice_note_type='audio/webm'):
        conn = get_db_connection()
        if not conn: return None
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                INSERT INTO emergency_alerts
                    (bus_id, reporter_type, reporter_id, reporter_name,
                     problem_type, description, voice_note_b64, voice_note_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (bus_id, reporter_type, reporter_id, reporter_name,
                  problem_type, description, voice_note_b64, voice_note_type))
            row = cursor.fetchone()
            conn.commit()
            return row['id'] if row else None
        except Exception as e:
            print(f"❌ Emergency Create Error: {e}")
            return None
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def upvote(alert_id, student_id):
        """Returns (new_count, is_mass_alert)."""
        conn = get_db_connection()
        if not conn: return 0, False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # Try to insert upvote (unique constraint prevents duplicates)
            cursor.execute("""
                INSERT INTO emergency_upvotes (alert_id, student_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (alert_id, student_id))
            # Increment count on the alert
            cursor.execute("""
                UPDATE emergency_alerts
                SET upvote_count = upvote_count + 1
                WHERE id = %s
                RETURNING upvote_count
            """, (alert_id,))
            row = cursor.fetchone()
            conn.commit()
            count = row['upvote_count'] if row else 0
            return count, count >= EmergencyModel.MASS_ALERT_THRESHOLD
        except Exception as e:
            print(f"❌ Upvote Error: {e}")
            return 0, False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def get_active_alerts(bus_id=None):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if bus_id:
            cursor.execute("""
                SELECT ea.*, b.busnumber
                FROM emergency_alerts ea
                JOIN buses b ON ea.bus_id = b.id
                WHERE ea.status = 'active' AND ea.bus_id = %s
                ORDER BY ea.created_at DESC
            """, (bus_id,))
        else:
            cursor.execute("""
                SELECT ea.*, b.busnumber
                FROM emergency_alerts ea
                JOIN buses b ON ea.bus_id = b.id
                WHERE ea.status = 'active'
                ORDER BY ea.upvote_count DESC, ea.created_at DESC
            """)
        results = cursor.fetchall()
        for r in results:
            if r.get('created_at'):
                r['created_at'] = r['created_at'].isoformat()
            if r.get('resolved_at'):
                r['resolved_at'] = r['resolved_at'].isoformat()
            # Don't return voice note b64 in list view (too heavy)
            r.pop('voice_note_b64', None)
        cursor.close(); conn.close()
        return results

    @staticmethod
    def get_alert_voice(alert_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT voice_note_b64, voice_note_type FROM emergency_alerts WHERE id = %s
        """, (alert_id,))
        result = cursor.fetchone()
        cursor.close(); conn.close()
        return result

    @staticmethod
    def resolve(alert_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                UPDATE emergency_alerts
                SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (alert_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ Resolve Alert Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def has_upvoted(alert_id, student_id):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT id FROM emergency_upvotes WHERE alert_id = %s AND student_id = %s
        """, (alert_id, student_id))
        result = cursor.fetchone()
        cursor.close(); conn.close()
        return result is not None

    @staticmethod
    def get_mass_alerts():
        """Get alerts that have crossed the threshold count (for admin banner)."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT ea.id, ea.bus_id, ea.upvote_count, ea.problem_type, b.busnumber
            FROM emergency_alerts ea
            JOIN buses b ON ea.bus_id = b.id
            WHERE ea.status = 'active' AND ea.upvote_count >= %s
            ORDER BY ea.upvote_count DESC
        """, (EmergencyModel.MASS_ALERT_THRESHOLD,))
        results = cursor.fetchall()
        cursor.close(); conn.close()
        return results


# =============================================
# ANALYTICS MODEL
# =============================================
class AnalyticsModel:
    @staticmethod
    def get_daily_summary():
        """Returns Chart.js-ready data for admin analytics."""
        conn = get_db_connection()
        if not conn: return {}
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Per-bus attendance today
        cursor.execute("""
            SELECT b.busnumber,
                   COUNT(s.id) as total,
                   COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present,
                   COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent,
                   COUNT(CASE WHEN lr.id IS NOT NULL THEN 1 END) as on_leave
            FROM buses b
            LEFT JOIN students s ON s.assignedbus = b.id
            LEFT JOIN attendance a ON a.student_id = s.id AND a.attendance_date = CURRENT_DATE
            LEFT JOIN leave_requests lr ON lr.student_id = s.id AND lr.leave_date = CURRENT_DATE
            GROUP BY b.id, b.busnumber
            ORDER BY b.id
        """)
        per_bus = cursor.fetchall()

        # 7-day trend
        cursor.execute("""
            SELECT attendance_date,
                   COUNT(CASE WHEN status = 'present' THEN 1 END) as present,
                   COUNT(CASE WHEN status = 'absent' THEN 1 END) as absent
            FROM attendance
            WHERE attendance_date >= CURRENT_DATE - INTERVAL '6 days'
            GROUP BY attendance_date
            ORDER BY attendance_date
        """)
        trend = cursor.fetchall()
        for t in trend:
            if t.get('attendance_date'):
                t['attendance_date'] = t['attendance_date'].isoformat()

        # Overall today
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM students) as total_students,
                COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present,
                COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent,
                (SELECT COUNT(*) FROM emergency_alerts WHERE status = 'active') as active_alerts,
                (SELECT COUNT(*) FROM leave_requests WHERE leave_date = CURRENT_DATE) as on_leave,
                (SELECT COUNT(*) FROM buses WHERE isActive = TRUE) as active_buses
            FROM attendance a
            WHERE a.attendance_date = CURRENT_DATE
        """)
        overall = cursor.fetchone()

        cursor.close(); conn.close()
        return {
            'per_bus': per_bus,
            'trend': trend,
            'overall': overall or {}
        }


# =============================================
# NOTIFICATION MODEL (Twilio-ready)
# =============================================
class NotificationModel:
    @staticmethod
    def send_sms(to_phone, message, msg_type='general'):
        """Send SMS via Twilio. Falls back to logging if credentials not set."""
        import os, requests as req
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        from_number = os.environ.get('TWILIO_FROM_NUMBER', '')

        # Log to DB regardless
        NotificationModel._log(to_phone, msg_type, message, 'pending')

        if not account_sid or not auth_token or not from_number:
            print(f"📵 Twilio not configured. SMS would be: [{to_phone}] {message}")
            NotificationModel._update_log_status(to_phone, message, 'skipped_no_credentials')
            return False

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            r = req.post(url, auth=(account_sid, auth_token),
                         data={'From': from_number, 'To': f'+91{to_phone}', 'Body': message})
            if r.status_code == 201:
                NotificationModel._update_log_status(to_phone, message, 'sent')
                return True
            else:
                print(f"❌ Twilio Error: {r.text}")
                return False
        except Exception as e:
            print(f"❌ SMS Error: {e}")
            return False

    @staticmethod
    def _log(phone, msg_type, message, status):
        conn = get_db_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notification_log (recipient_phone, message_type, message, status)
                VALUES (%s, %s, %s, %s)
            """, (phone, msg_type, message, status))
            conn.commit()
        except Exception:
            pass
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def _update_log_status(phone, message, status):
        conn = get_db_connection()
        if not conn: return
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE notification_log SET status = %s
                WHERE recipient_phone = %s AND message = %s AND status = 'pending'
                ORDER BY sent_at DESC LIMIT 1
            """, (status, phone, message))
            conn.commit()
        except Exception:
            pass
        finally:
            if conn: cursor.close(); conn.close()


# =============================================
# TRIP LOG MODEL (Geofencing)
# =============================================
class TripLogModel:
    COLLEGE_LAT = 12.717849
    COLLEGE_LNG = 77.869604
    GEOFENCE_RADIUS_METERS = 500

    @staticmethod
    def start_trip(bus_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                INSERT INTO trip_log (bus_id, departure_at, status)
                VALUES (%s, CURRENT_TIMESTAMP, 'in_progress')
                ON CONFLICT (bus_id, trip_date) DO UPDATE
                    SET departure_at = CURRENT_TIMESTAMP, status = 'in_progress'
            """, (bus_id,))
            # Also mark bus as active
            cursor.execute("UPDATE buses SET isActive = TRUE WHERE id = %s", (bus_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Trip Start Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def complete_trip(bus_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                UPDATE trip_log
                SET status = 'completed', arrival_at = CURRENT_TIMESTAMP
                WHERE bus_id = %s AND trip_date = CURRENT_DATE
            """, (bus_id,))
            # Optionally mark bus inactive after arrival
            # cursor.execute("UPDATE buses SET isActive = FALSE WHERE id = %s", (bus_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Trip Complete Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

    @staticmethod
    def get_today_status(bus_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("""
            SELECT * FROM trip_log WHERE bus_id = %s AND trip_date = CURRENT_DATE
        """, (bus_id,))
        result = cursor.fetchone()
        if result:
            for k in ['departure_at', 'arrival_at']:
                if result.get(k):
                    result[k] = result[k].isoformat()
        cursor.close(); conn.close()
        return result
