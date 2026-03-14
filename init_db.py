import psycopg2
from config import Config

def init_database():
    print("Connecting to PostgreSQL...")
    try:
        # Connect to the database
        conn = psycopg2.connect(Config.DATABASE_URL)
        cursor = conn.cursor()
        
        # Read the SQL file
        print("Reading database.sql...")
        with open('database.sql', 'r') as file:
            sql_script = file.read()
            
        # Execute the SQL script manually by splitting
        print("Executing SQL statements...")
        statements = [s.strip() for s in sql_script.split(';') if s.strip()]
        for stmt in statements:
            try:
                cursor.execute(stmt)
                print(f"Executed: {stmt.split(' ')[0]} ...")
            except Exception as loop_err:
                print(f"Warning on statement {stmt.split(' ')[0]}: {loop_err}")
                
        conn.commit()
        cursor.close()
        conn.close()
        print("\nDatabase initialization completed successfully!")
        print("You can now run: python api/index.py")
        
    except psycopg2.Error as err:
        print(f"\nError: {err}")
        print("Please ensure PostgreSQL server is running and your DATABASE_URL in config.py is correct.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    init_database()
