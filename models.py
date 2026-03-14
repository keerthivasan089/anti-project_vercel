import psycopg2
import psycopg2.extras
from config import Config
from flask import current_app
import time

# Dictionary to track the last manual (driver) update time per bus
# This allows us to suppress simulation updates for active drivers
REAL_TIME_LOCKS = {}

def get_db_connection():
    try:
        connection = psycopg2.connect(Config.DATABASE_URL)
        return connection
    except psycopg2.Error as err:
        print(f"❌ DB Error: {err}")
        return None

# ✅ FIXED BusModel (SINGLE CLASS)
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
            # Mark this bus as having a real driver update
            REAL_TIME_LOCKS[busid] = current_time
        else:
            # If this is a simulation, check if a real driver updated in the last 2 minutes
            last_real_update = REAL_TIME_LOCKS.get(busid, 0)
            if current_time - last_real_update < 120:
                cursor.close()
                conn.close()
                return True # Skip simulation if real driver is active

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
    def get_all_locations():  # ✅ FIXED table/column names
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
        
        # Serialize Decimal and Datetime types into standard Python types for JSON
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
        """Returns all buses and their designated stops to populate the driver dropdown."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Note: Since the DB schema doesn't strictly explicitly hard-link one single busstop to a bus 
        # outside of the students table, we'll just fetch all buses so the driver can select theirs.
        cursor.execute("SELECT id, busnumber FROM buses ORDER BY id")
        buses = cursor.fetchall()
        cursor.close()
        conn.close()
        return buses

# ✅ ADMIN MODEL FOR INSERTING DATA
class AdminModel:
    @staticmethod
    def add_student(rollnumber, name, dob, bus_id, stop_id):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("""
                INSERT INTO students (rollnumber, studentname, dob, assignedbus, assignedstop)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (rollnumber) DO UPDATE SET
                    studentname = EXCLUDED.studentname,
                    dob = EXCLUDED.dob,
                    assignedbus = EXCLUDED.assignedbus,
                    assignedstop = EXCLUDED.assignedstop
            """, (rollnumber, name, dob, bus_id, stop_id))
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
    def add_or_update_driver(busnumber, drivername, driverphone):
        conn = get_db_connection()
        if not conn: return False
        try:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            # Try to update first, if no rows updated, insert new bus
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
            # Due to cascading foreign keys, deleting a bus will nullify/delete related tracking
            cursor.execute("DELETE FROM buses WHERE id = %s", (bus_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Admin Delete Bus Error: {e}")
            return False
        finally:
            if conn: cursor.close(); conn.close()

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

# ✅ FIXED StopModel (SINGLE CLASS)
class StopModel:
    @staticmethod
    def get_all_stops():  # ✅ FIXED table name
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM busstops")
        stops = cursor.fetchall()

        # Serialize Decimals for JSON response (and template access)
        for stop in stops:
            if stop.get('latitude') is not None:
                stop['latitude'] = float(stop['latitude'])
            if stop.get('longitude') is not None:
                stop['longitude'] = float(stop['longitude'])

        cursor.close()
        conn.close()
        return stops

# ✅ STUDENT LOGIN FUNCTION (DEBUG VERSION)
def get_student_by_auth(rollnumber, dob):
    print(f"🔍 Searching student: {rollnumber} | {dob}")
    
    # Generate possible MySQL date formats based on the input
    possible_dobs = [dob] # The exact string entered
    
    from datetime import datetime
    
    # Normalize slashes to dashes for easier parsing
    normalized_dob = dob.replace('/', '-')
    
    try:
        # If they entered DD-MM-YYYY or DD/MM/YYYY
        parsed1 = datetime.strptime(normalized_dob, "%d-%m-%Y")
        possible_dobs.append(parsed1.strftime("%Y-%m-%d"))
    except ValueError:
        pass
        
    try:
        # If they entered MM-DD-YYYY or MM/DD/YYYY
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
        # We use an IN clause so any of the generated date formats will match
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
