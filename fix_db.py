from models import get_db_connection

def apply_schema():
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to DB")
        return
    
    cursor = conn.cursor()
    try:
        print("Creating table new_registrations...")
        cursor.execute("""
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
        """)
        conn.commit()
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    apply_schema()
