import os
import psycopg2
from psycopg2 import OperationalError

def get_db_connection():
    try:
        if os.getenv("RENDER_DEPLOYMENT", "false").lower() == "true":
            db_password = os.getenv("DB_PASSWORD")
            if not db_password:
                raise ValueError("DB_PASSWORD environment variable is not set.")

            conn_str = f"postgresql://postgres.kiztrspuyrijamuqzaki:{db_password}@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
            return psycopg2.connect(conn_str)
        else:
            return psycopg2.connect(
                dbname='AMMPropiedades',
                user="postgres",
                password=os.getenv("DB_PASSWORD"),
                host="localhost",
                port="5432"
            )

    except OperationalError as e:
        print(f"Database connection error: {e}")
        raise