# auth_utils.py
import sqlite3
import os

# Función para conectar a la base de datos (usando ruta absoluta para evitar errores en Render)
def get_db_connection():
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def es_admin(usuario_id):
    """Verifica si el ID de usuario tiene rol 'admin'"""
    if not usuario_id:
        return False
    conn = get_db_connection()
    user = conn.execute("SELECT rol FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    conn.close()
    return user is not None and user['rol'] == 'admin'

def obtener_pregunta_seguridad(email):
    """Busca la pregunta de seguridad configurada para un email"""
    conn = get_db_connection()
    user = conn.execute("SELECT pregunta_seguridad FROM usuarios WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user['pregunta_seguridad'] if user else None

def validar_respuesta_y_cambiar_clave(email, respuesta, nueva_clave_hash):
    """Valida la respuesta y si es correcta, actualiza la contraseña"""
    conn = get_db_connection()
    user = conn.execute("SELECT respuesta_seguridad FROM usuarios WHERE email = ?", (email,)).fetchone()
    
    if user and user['respuesta_seguridad'].lower() == respuesta.lower():
        conn.execute("UPDATE usuarios SET password = ? WHERE email = ?", (nueva_clave_hash, email))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False