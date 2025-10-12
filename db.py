import os
from psycopg2 import pool, OperationalError
from contextlib import contextmanager

# Global connection pool
db_pool = None


def init_db_pool():
    """Initialize a global database connection pool."""
    global db_pool
    try:
        if os.getenv("RENDER_DEPLOYMENT", "false").lower() == "true":
            db_password = os.getenv("DB_PASSWORD")
            if not db_password:
                raise ValueError("DB_PASSWORD environment variable is not set.")

            conn_str = f"postgresql://postgres.kiztrspuyrijamuqzaki:{db_password}@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,  # Safe under Supabase's 15 connection limit
                dsn=conn_str
            )
        else:
            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                dbname='AMMPropiedades',
                user="postgres",
                password=os.getenv("DB_PASSWORD"),
                host="localhost",
                port="5432"
            )
        print("✅ Database connection pool initialized.")
    except OperationalError as e:
        print(f"❌ Database pool initialization error: {e}")
        raise


@contextmanager
def get_db_connection():
    """Provide a connection from the pool as a context manager."""
    global db_pool
    if db_pool is None:
        init_db_pool()

    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)
