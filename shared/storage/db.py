import os
from loguru import logger
import psycopg2
from psycopg2.extras import Json

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_NAME = os.getenv("DB_NAME", "ai_simulator")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def save_simulation_result(simulation_id: str, result: dict, user_id: str = None):
    try: 
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO simulation (id, result, user_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET result = EXCLUDED.result, user_id = EXCLUDED.user_id;
                    """,
                    (simulation_id, Json(result), user_id)
                )
                conn.commit()

    except Exception as e:
        logger.exception(
            f"Failed to save simulation"
            f"{simulation_id}: {e}"
        )    

def get_simulation_result(simulation_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT result FROM simulation WHERE id = %s",
                (simulation_id,)
            )   
            row = cur.fetchone()
            return row[0] if row else None

def delete_simulation(simulation_id: str, user_id: str = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = "DELETE FROM simulation WHERE id = %s"
            params = [simulation_id]
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
                
            cur.execute(query, params)
            deleted_count = cur.rowcount
            conn.commit()
            return deleted_count

def list_simulations(user_id: str = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            query = """
            SELECT
                id,
                result->>'goal' as goal,
                result->>'status' as status,
                created_at
            FROM simulation
            """    
            
            params = []
            if user_id:
                query += " WHERE user_id = %s"
                params.append(user_id)
            
            query += " ORDER BY created_at DESC LIMIT 20"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            return [{"id": r[0], "goal": r[1], "status": r[2], "created_at": str(r[3])} for r in rows]

# --- User Management ---

def create_user(user_id: str, email: str, password_hash: str, full_name: str, dob: str, personal_api_key: str = None):
    if not password_hash.startswith("$2"):
        raise ValueError("Password is not hashed properly")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, email, password_hash, full_name, dob, personal_api_key) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, email, password_hash, full_name, dob, personal_api_key)
            )
            conn.commit()

def get_user_by_email(email: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email, password_hash, full_name, dob, personal_api_key, usage_today FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            if row:
                return {
                    "id": row[0], 
                    "email": row[1], 
                    "password_hash": row[2], 
                    "full_name": row[3], 
                    "dob": str(row[4]), 
                    "personal_api_key": row[5],
                    "usage_today": row[6]
                }
            return None

def get_user_by_id(user_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email, full_name, dob, personal_api_key, usage_today FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if row:
                return {"id": row[0], "email": row[1], "full_name": row[2], "dob": str(row[3]), "personal_api_key": row[4], "usage_today": row[5]}
            return None

def update_user_profile(user_id: str, full_name: str, dob: str, personal_api_key: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET full_name = %s, dob = %s, personal_api_key = %s WHERE id = %s",
                (full_name, dob, personal_api_key, user_id)
            )
            conn.commit()

def increment_usage(user_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET usage_today = usage_today + 1 WHERE id = %s", (user_id,))
            conn.commit()

def check_and_reset_usage(user_id: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Reset if last reset was more than 24h ago
            cur.execute(
                """
                UPDATE users 
                SET usage_today = 0, last_usage_reset = CURRENT_TIMESTAMP 
                WHERE id = %s AND last_usage_reset < CURRENT_TIMESTAMP - INTERVAL '1 day'
                RETURNING usage_today;
                """,
                (user_id,)
            )
            conn.commit()