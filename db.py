import os
from psycopg2 import pool, OperationalError
from contextlib import contextmanager


db_pool = None

def init_db_pool():
    """Inicializa el pool global de conexiones."""
    global db_pool
    try:
        if os.getenv("RENDER_DEPLOYMENT", "false").lower() == "true":
            db_password = os.getenv("DB_PASSWORD")
            if not db_password:
                raise ValueError("DB_PASSWORD environment variable is not set.")

            conn_str = f"postgresql://postgres.kiztrspuyrijamuqzaki:{db_password}@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,  # <= Mantener por debajo del límite de Supabase (15)
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
    except OperationalError as e:
        print(f"Database pool init error: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error initializing DB pool: {e}")
        raise

def get_conn():
    """Obtiene una conexión del pool (reintenta si se perdió la conexión)."""
    global db_pool
    if db_pool is None:
        init_db_pool()
    try:
        return db_pool.getconn()
    except OperationalError:
        print("⚠️ Connection lost, reinitializing pool...")
        init_db_pool()
        return db_pool.getconn()


def put_conn(conn):
    """Devuelve una conexión al pool de forma segura."""
    global db_pool
    if db_pool and conn:
        try:
            db_pool.putconn(conn)
        except Exception as e:
            print(f"⚠️ Error returning connection to pool: {e}")
            # Si algo salió mal, se reinicia el pool completo
            db_pool.closeall()
            db_pool = None


@contextmanager
def get_db_connection():
    """
    Context manager para obtener una conexión del pool de forma segura.
    Uso:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    conn = None
    try:
        conn = get_conn()
        yield conn
    finally:
        if conn:
            put_conn(conn)