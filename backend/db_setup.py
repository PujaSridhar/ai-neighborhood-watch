import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the database URL from the environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

def setup_database():
    """Connects to the database and creates the reports table if it doesn't exist."""
    conn = None
    try:
        print("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("Creating the 'reports' table if it does not exist...")
        # SQL command to create the table
        # We use SERIAL PRIMARY KEY to get an auto-incrementing ID.
        # created_at uses TIMESTAMPTZ for a timezone-aware timestamp.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                description TEXT NOT NULL,
                latitude DOUBLE PRECISION NOT NULL,
                longitude DOUBLE PRECISION NOT NULL,
                category VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # Commit the changes to the database
        conn.commit()
        print("Table 'reports' is ready.")

        # Close the cursor
        cur.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error while setting up PostgreSQL database: {error}")
    finally:
        if conn is not None:
            # Close the database connection
            conn.close()
            print("Database connection closed.")

if __name__ == '__main__':
    setup_database()

