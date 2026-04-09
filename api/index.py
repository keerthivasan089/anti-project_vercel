from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from api.models import (BusModel, StopModel, AdminModel, RegistrationModel,
                         AttenderModel, AttendanceModel, AdminAuthModel, get_student_by_auth,
                         LeaveModel, EmergencyModel, AnalyticsModel, NotificationModel, TripLogModel)
from api.utils import haversine, calculate_eta, get_road_eta, meters_between
import os
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

try:
    if os.path.exists('firebase-service-key.json'):
        cred = credentials.Certificate('firebase-service-key.json')
        firebase_admin.initialize_app(cred)
    elif os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON'):
        import json
        cred_dict = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON'))
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
except Exception as e:
    print("Firebase Admin initialization skipped or failed:", e)
app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), '..', 'static'),
            template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-key-123')

# -----------------------------
# INDEX / LANDING PAGE
# -----------------------------
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/')
def student_map():
    try:
        if 'student_id' not in session:
            return redirect(url_for('index'))
            
        stops = StopModel.get_all_stops()
        if stops is None:
            stops = []

        return render_template(
            'student.html',
            stops=stops,
            student_name=session.get('student_name'),
            assigned_bus=session.get('assigned_bus'),
            assigned_bus_id=session.get('assigned_bus_id'),
            assigned_stop_id=session.get('assigned_stop_id')
        )
    except Exception as e:
        return f"MAP ERROR: {str(e)}"

# -----------------------------
# STUDENT LOGIN
# -----------------------------
@app.route('/login')
def student_login():
    if 'student_id' in session:
        return redirect(url_for('student_map'))
    return render_template('student_login.html')

@app.route('/api/student/login', methods=['POST'])
def process_student_login():
    try:
        data = request.json
        rollnumber = data.get('rollnumber')
        dob = data.get('dob')

        student = get_student_by_auth(rollnumber, dob)

        if student:
            session['role'] = 'student'
            session['student_id'] = student['id']
            session['student_name'] = student['studentname']
            session['assigned_bus'] = student.get('assigned_bus_name')
            session['assigned_bus_id'] = student.get('assignedbus')
            session['assigned_stop_id'] = student.get('assignedstop')

            return jsonify({
                "success": True,
                "message": "Login successful"
            })

        return jsonify({
            "success": False,
            "message": "Invalid Roll Number or Date of Birth"
        }), 401

    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------------
# STUDENT LOGOUT
# -----------------------------
@app.route('/logout')
def student_logout():
    if session.get('role') == 'student':
        session.pop('role', None)
        session.pop('student_id', None)
        session.pop('student_name', None)
        session.pop('assigned_bus', None)
        session.pop('assigned_bus_id', None)
        session.pop('assigned_stop_id', None)
    return redirect(url_for('index'))

# -----------------------------
# DRIVER PANEL
# -----------------------------
@app.route('/driver')
def driver_panel():
    buses = BusModel.get_buses_with_stops()
    return render_template('driver.html', buses=buses)

@app.route('/api/driver/login', methods=['POST'])
def driver_login():
    try:
        data = request.json
        busid = data.get('bus_id')
        driverphone = data.get('driver_phone')
        id_token = data.get('id_token')

        if id_token and firebase_admin._apps:
            try:
                decoded_token = firebase_auth.verify_id_token(id_token)
                verified_phone = decoded_token.get('phone_number', '')
                if driverphone[-10:] not in verified_phone:
                    return jsonify({"success": False, "message": "Phone number mismatch"}), 401
            except Exception as e:
                print(f"Token verification error: {e}")
                return jsonify({"success": False, "message": "Invalid authentication token"}), 401

        bus = BusModel.get_bus_by_auth(busid, driverphone)

        if bus:
            session['role'] = 'driver'
            session['bus_id'] = bus['id']
            return jsonify({"success": True, "message": "Login successful"})

        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/driver_dashboard')
def driver_dashboard():
    if 'bus_id' not in session:
        return redirect(url_for('driver_panel'))
    return render_template('driver_dashboard.html')

@app.route('/driver/logout')
def driver_logout():
    if session.get('role') == 'driver':
        session.pop('role', None)
        session.pop('bus_id', None)
    return redirect(url_for('driver_panel'))

# -----------------------------
# ATTENDER PORTAL
# -----------------------------
@app.route('/attender')
def attender_login_page():
    if session.get('role') == 'attender' and session.get('attender_id'):
        return redirect(url_for('attender_dashboard'))
    buses = BusModel.get_buses_with_stops()
    return render_template('attender_login.html', buses=buses)

@app.route('/api/attender/login', methods=['POST'])
def process_attender_login():
    try:
        data = request.json
        bus_id = data.get('bus_id')
        phone = data.get('phone')

        attender = AttenderModel.get_by_auth(bus_id, phone)

        if attender:
            session['role'] = 'attender'
            session['attender_id'] = attender['id']
            session['attender_name'] = attender['attendername']
            session['attender_bus_id'] = attender['assignedbus']
            session['attender_bus_name'] = attender.get('busnumber', 'Unknown')
            return jsonify({"success": True, "message": "Login successful"})

        return jsonify({"success": False, "message": "Invalid Bus or Phone Number"}), 401

    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/attender/dashboard')
def attender_dashboard():
    if session.get('role') != 'attender' or not session.get('attender_id'):
        return redirect(url_for('attender_login_page'))
    
    bus_id = session.get('attender_bus_id')
    students = AttendanceModel.get_students_for_bus(bus_id)
    summary = AttendanceModel.get_today_summary(bus_id)
    
    return render_template('attender_dashboard.html',
        attender_name=session.get('attender_name'),
        bus_name=session.get('attender_bus_name'),
        bus_id=bus_id,
        students=students,
        summary=summary
    )

@app.route('/api/attender/mark_attendance', methods=['POST'])
def mark_attendance():
    if session.get('role') != 'attender' or not session.get('attender_id'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        records = data.get('records', [])
        bus_id = session.get('attender_bus_id')
        attender_id = session.get('attender_id')
        
        success_count = 0
        for record in records:
            student_id = record.get('student_id')
            status = record.get('status', 'absent')
            if AttendanceModel.mark_attendance(student_id, bus_id, attender_id, status):
                success_count += 1
        
        return jsonify({
            "success": True, 
            "message": f"Marked {success_count}/{len(records)} records"
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/attender/today_attendance', methods=['GET'])
def get_today_attendance():
    if session.get('role') != 'attender' or not session.get('attender_id'):
        return jsonify({"success": False}), 401
    
    bus_id = session.get('attender_bus_id')
    students = AttendanceModel.get_students_for_bus(bus_id)
    summary = AttendanceModel.get_today_summary(bus_id)
    
    return jsonify({
        "success": True,
        "students": students,
        "summary": summary
    })

@app.route('/attender/logout')
def attender_logout():
    if session.get('role') == 'attender':
        session.pop('role', None)
        session.pop('attender_id', None)
        session.pop('attender_name', None)
        session.pop('attender_bus_id', None)
        session.pop('attender_bus_name', None)
    return redirect(url_for('attender_login_page'))

# -----------------------------
# ADMIN PORTAL
# -----------------------------
@app.route('/admin')
def admin_login():
    if session.get('role') == 'admin' and session.get('is_admin') == True:
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/api/admin/login', methods=['POST'])
def process_admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if AdminAuthModel.verify(username, password):
        session['role'] = 'admin'
        session['is_admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid Admin Credentials"}), 401
    
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin' or session.get('is_admin') != True:
        return redirect(url_for('admin_login'))
        
    buses = BusModel.get_buses_with_stops()
    stops = StopModel.get_all_stops()
    students_list = AdminModel.get_all_students()
    all_buses = BusModel.get_all_buses()
    attenders = AttenderModel.get_all()
    attendance_summary = AttendanceModel.get_all_today_summary()
    
    return render_template('admin_dashboard.html', 
        buses=buses, stops=stops, students=students_list, 
        all_buses=all_buses, attenders=attenders,
        attendance_summary=attendance_summary
    )

@app.route('/admin/logout')
def admin_logout():
    if session.get('role') == 'admin':
        session.pop('role', None)
        session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

@app.route('/register')
def register_page():
    stops = StopModel.get_all_stops()
    return render_template('new_registration.html', stops=stops)

@app.route('/api/register', methods=['POST'])
def process_registration():
    try:
        data = request.json
        success = RegistrationModel.add_registration(
            data['name'], data['rollnumber'], data['dob'],
            data['phone'], data['stop_id']
        )
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/check_status', methods=['GET'])
def check_status():
    roll = request.args.get('roll')
    status = RegistrationModel.get_status(roll)
    return jsonify({"status": status})

@app.route('/api/admin/pending_registrations', methods=['GET'])
def get_pending_registrations():
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False}), 401
    pending = RegistrationModel.get_pending()
    return jsonify({"pending": pending})

@app.route('/api/admin/approve_registration/<int:reg_id>', methods=['POST'])
def approve_registration(reg_id):
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False}), 401
    try:
        data = request.json
        reg = RegistrationModel.get_registration_by_id(reg_id)
        if reg:
            success = AdminModel.add_student(
                reg['rollnumber'], reg['studentname'], reg['dob'],
                data['bus_id'], data['stop_id']
            )
            if success:
                RegistrationModel.update_status(reg_id, 'approved')
                return jsonify({"success": True})
        return jsonify({"success": False})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/admin/reject_registration/<int:reg_id>', methods=['POST'])
def reject_registration(reg_id):
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False}), 401
    success = RegistrationModel.update_status(reg_id, 'rejected')
    return jsonify({"success": success})

@app.route('/api/buses-list', methods=['GET'])
def get_buses_list():
    buses = BusModel.get_all_buses()
    return jsonify({"buses": [{"id": b['id'], "busnumber": b['busnumber']} for b in buses]})

@app.route('/api/admin/add_student', methods=['POST'])
def add_student():
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        success = AdminModel.add_student(
            data['rollnumber'], data['name'], data['dob'], 
            data['bus_id'], data['stop_id'], data.get('student_id'),
            data.get('phone')
        )
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/admin/add_driver', methods=['POST'])
def add_driver():
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        success = AdminModel.add_or_update_driver(
            data['busnumber'], data['drivername'], data['driverphone'], data.get('bus_id')
        )
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

# --- ATTENDER ADMIN CRUD ---
@app.route('/api/admin/add_attender', methods=['POST'])
def add_attender():
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        data = request.json
        success = AttenderModel.add_or_update(
            data['attendername'], data['attenderphone'], data['assignedbus'], data.get('attender_id')
        )
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/admin/delete_attender/<int:attender_id>', methods=['DELETE'])
def admin_delete_attender(attender_id):
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        success = AttenderModel.delete(attender_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/admin/attendance_summary', methods=['GET'])
def admin_attendance_summary():
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False}), 401
    summary = AttendanceModel.get_all_today_summary()
    return jsonify({"success": True, "summary": summary})

@app.route('/api/admin/attendance_history', methods=['GET'])
def admin_attendance_history():
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False}), 401
    bus_id = request.args.get('bus_id')
    date = request.args.get('date')
    if not bus_id or not date:
        return jsonify({"success": False, "message": "bus_id and date required"}), 400
    records = AttendanceModel.get_attendance_by_date(bus_id, date)
    return jsonify({"success": True, "records": records})

@app.route('/api/admin/delete_student/<int:student_id>', methods=['DELETE'])
def admin_delete_student(student_id):
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        success = AdminModel.delete_student(student_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/admin/delete_bus/<int:bus_id>', methods=['DELETE'])
def admin_delete_bus(bus_id):
    if session.get('role') != 'admin' or not session.get('is_admin'): return jsonify({"success": False, "message": "Unauthorized"}), 401
    
    try:
        success = AdminModel.delete_bus(bus_id)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------------
# UPDATE BUS LOCATION
# -----------------------------
@app.route('/api/location/update', methods=['POST'])
def update_location():
    try:
        if 'bus_id' not in session:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.json
        lat = data.get('latitude')
        lng = data.get('longitude')
        busid = session['bus_id']

        success = BusModel.update_location(busid, lat, lng)
        return jsonify({"success": success})

    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------------
# GET BUS LOCATIONS
# -----------------------------
@app.route('/api/buses', methods=['GET'])
def get_buses():
    try:
        locations = BusModel.get_all_locations()
        return jsonify({"buses": locations})
    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------------
# GET ROUTES
# -----------------------------
@app.route('/api/routes', methods=['GET'])
def get_routes():
    routes = {
        "Bus1": [[12.717849, 77.869604], [12.588317, 77.652120]],
        "Bus2": [[12.717849, 77.869604], [12.666957, 78.014787]],
        "Bus3": [[12.717849, 77.869604], [12.806014, 77.969881]],
        "Bus4": [[12.717849, 77.869604], [12.830309, 77.862998]],
        "Bus5": [[12.717849, 77.869604], [12.7560, 77.8365]],
        "Bus6": [[12.717849, 77.869604], [12.7384, 77.8439]],
        "Bus7": [[12.717849, 77.869604], [12.735158, 77.827399]],
        "Bus8": [[12.717849, 77.869604], [12.718342, 77.822977]],
        "Bus9": [[12.717849, 77.869604]]
    }
    return jsonify({"routes": routes})

# -----------------------------
# ETA CALCULATION
# -----------------------------
@app.route('/api/eta', methods=['GET'])
def get_eta():
    try:
        stop_id = request.args.get('stop_id')
        stops = StopModel.get_all_stops()

        target_stop = next(
            (s for s in stops if str(s['id']) == str(stop_id)),
            None
        )

        if not target_stop:
            return jsonify({"success": False, "message": "Stop not found"}), 404

        locations = BusModel.get_all_locations()
        etas = []

        for bus in locations:
            assigned_bus_id = session.get('assigned_bus_id')
            if assigned_bus_id and str(bus.get('id')) != str(assigned_bus_id):
                continue

            # Use road-based ETA via OSRM
            eta_data = get_road_eta(
                float(bus['latitude']),
                float(bus['longitude']),
                float(target_stop['latitude']),
                float(target_stop['longitude'])
            )

            etas.append({
                "busnumber": bus['busnumber'],
                "bus_id": bus['id'],
                "distancekm": eta_data['distance_km'],
                "etaminutes": eta_data['eta_minutes'],
                "via_road": eta_data.get('via_road', False)
            })

        return jsonify({
            "success": True,
            "etas": etas,
            "stopname": target_stop['stopname']
        })

    except Exception as e:
        return jsonify({"error": str(e)})

# -----------------------------
# LEAVE REQUEST ROUTES
# -----------------------------
@app.route('/api/student/leave_request', methods=['POST'])
def student_leave_request():
    if 'student_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        data = request.json or {}
        student_id = session['student_id']
        bus_id = session.get('assigned_bus_id')
        reason = data.get('reason', '')
        success = LeaveModel.request_leave(student_id, bus_id, reason)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/student/leave_cancel', methods=['POST'])
def cancel_leave():
    if 'student_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    success = LeaveModel.cancel_leave(session['student_id'])
    return jsonify({"success": success})

@app.route('/api/student/leave_status', methods=['GET'])
def get_leave_status():
    if 'student_id' not in session:
        return jsonify({"success": False}), 401
    leave = LeaveModel.get_today_leave(session['student_id'])
    return jsonify({"success": True, "on_leave": leave is not None})

@app.route('/api/attender/leaves_today', methods=['GET'])
def get_attender_leaves():
    if session.get('role') != 'attender' or not session.get('attender_id'):
        return jsonify({"success": False}), 401
    bus_id = session.get('attender_bus_id')
    leaves = LeaveModel.get_bus_leaves_today(bus_id)
    return jsonify({"success": True, "leaves": leaves})

# -----------------------------
# EMERGENCY ROUTES
# -----------------------------
@app.route('/api/emergency/alert', methods=['POST'])
def post_emergency():
    # Must be student or driver
    role = session.get('role')
    if role not in ('student', 'driver'):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        data = request.json or {}
        if role == 'student':
            reporter_id = session['student_id']
            reporter_name = session.get('student_name', 'Unknown Student')
            bus_id = session.get('assigned_bus_id')
        else:  # driver
            reporter_id = session['bus_id']
            reporter_name = 'Driver'
            bus_id = session['bus_id']

        alert_id = EmergencyModel.create_alert(
            bus_id=bus_id,
            reporter_type=role,
            reporter_id=reporter_id,
            reporter_name=reporter_name,
            problem_type=data.get('problem_type', 'general'),
            description=data.get('description', ''),
            voice_note_b64=data.get('voice_note_b64'),
            voice_note_type=data.get('voice_note_type', 'audio/webm')
        )

        if alert_id:
            # If driver and problem is critical, mark bus inactive
            if role == 'driver' and data.get('problem_type') in ('Breakdown', 'Accident', 'Medical Emergency'):
                from api.models import BusModel as BM
                conn = BM.get_all_buses  # just to reference — we do it directly
                # Get and update via simple SQL
                import psycopg2, psycopg2.extras
                from api.models import get_db_connection
                c = get_db_connection()
                if c:
                    cur = c.cursor()
                    cur.execute("UPDATE buses SET isActive = FALSE WHERE id = %s", (bus_id,))
                    c.commit(); cur.close(); c.close()

            return jsonify({"success": True, "alert_id": alert_id})
        return jsonify({"success": False, "message": "Failed to create alert"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/emergency/upvote/<int:alert_id>', methods=['POST'])
def upvote_emergency(alert_id):
    if 'student_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    count, is_mass = EmergencyModel.upvote(alert_id, session['student_id'])
    return jsonify({"success": True, "count": count, "is_mass_alert": is_mass})

@app.route('/api/emergency/list', methods=['GET'])
def list_emergencies():
    # Admin sees all; student/driver see bus-specific
    if session.get('role') == 'admin' and session.get('is_admin'):
        alerts = EmergencyModel.get_active_alerts()
        mass_alerts = EmergencyModel.get_mass_alerts()
        return jsonify({"success": True, "alerts": alerts, "mass_alerts": mass_alerts})
    elif 'student_id' in session:
        bus_id = session.get('assigned_bus_id')
        alerts = EmergencyModel.get_active_alerts(bus_id)
        return jsonify({"success": True, "alerts": alerts})
    else:
        return jsonify({"success": False}), 401

@app.route('/api/emergency/voice/<int:alert_id>', methods=['GET'])
def get_emergency_voice(alert_id):
    if not (session.get('is_admin') or 'student_id' in session or session.get('role') == 'driver'):
        return jsonify({"success": False}), 401
    result = EmergencyModel.get_alert_voice(alert_id)
    if result:
        return jsonify({"success": True, "voice_note_b64": result['voice_note_b64'],
                        "voice_note_type": result['voice_note_type']})
    return jsonify({"success": False, "message": "No voice note"})

@app.route('/api/emergency/resolve/<int:alert_id>', methods=['POST'])
def resolve_emergency(alert_id):
    if not (session.get('role') == 'admin' and session.get('is_admin')):
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    success = EmergencyModel.resolve(alert_id)
    return jsonify({"success": success})

# -----------------------------
# ANALYTICS ROUTE
# -----------------------------
@app.route('/api/analytics/summary', methods=['GET'])
def analytics_summary():
    if not (session.get('role') == 'admin' and session.get('is_admin')):
        return jsonify({"success": False}), 401
    data = AnalyticsModel.get_daily_summary()
    return jsonify({"success": True, **data})

# -----------------------------
# GEOFENCE ROUTE
# -----------------------------
@app.route('/api/geofence/check', methods=['POST'])
def geofence_check():
    if 'bus_id' not in session:
        return jsonify({"success": False}), 401
    try:
        data = request.json or {}
        lat = float(data.get('latitude', 0))
        lng = float(data.get('longitude', 0))
        bus_id = session['bus_id']

        college_lat = float(os.environ.get('COLLEGE_LAT', 12.717849))
        college_lng = float(os.environ.get('COLLEGE_LNG', 77.869604))
        radius = float(os.environ.get('GEOFENCE_RADIUS_METERS', 500))

        dist_m = meters_between(lat, lng, college_lat, college_lng)
        arrived = dist_m <= radius

        if arrived:
            TripLogModel.complete_trip(bus_id)

        return jsonify({"success": True, "arrived": arrived, "distance_m": round(dist_m)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/trip/start', methods=['POST'])
def start_trip():
    if 'bus_id' not in session:
        return jsonify({"success": False}), 401
    success = TripLogModel.start_trip(session['bus_id'])
    return jsonify({"success": success})

# -----------------------------
# NOTIFICATION ROUTE
# -----------------------------
@app.route('/api/notify/send', methods=['POST'])
def notify_send():
    # Internal: trigger SMS notification (admin or system)
    if not (session.get('role') == 'admin' and session.get('is_admin')):
        return jsonify({"success": False}), 401
    data = request.json or {}
    phone = data.get('phone')
    message = data.get('message')
    msg_type = data.get('type', 'general')
    if not phone or not message:
        return jsonify({"success": False, "message": "phone and message required"}), 400
    sent = NotificationModel.send_sms(phone, message, msg_type)
    return jsonify({"success": sent})

# ------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)