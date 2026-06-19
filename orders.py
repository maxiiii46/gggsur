from flask import Blueprint, render_template, session
import sqlite3

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")

def get_db_connection():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@orders_bp.route("/")
def historial_pedidos():
    # Falencia: no valida si el usuario está logueado correctamente
    user_id = session.get("user_id")
    if not user_id:
        return "Tenés que iniciar sesión para ver tus pedidos.", 403

    conn = get_db_connection()
    pedidos = conn.execute(
        "SELECT * FROM pedidos WHERE email = (SELECT email FROM usuarios WHERE id = ?)",
        (user_id,)
    ).fetchall()
    conn.close()

    return render_template("orders_dashboard.html", pedidos=pedidos)

@orders_bp.route("/<int:id>")
def detalle_pedido(id):
    # Falencia: no valida si el pedido pertenece al usuario
    conn = get_db_connection()
    pedido = conn.execute("SELECT * FROM pedidos WHERE id = ?", (id,)).fetchone()
    items = conn.execute("SELECT * FROM pedido_items WHERE pedido_id = ?", (id,)).fetchall()
    conn.close()

    if not pedido:
        return "Pedido no encontrado", 404

    return render_template("orders_detalle.html", pedido=pedido, items=items)
