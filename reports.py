from flask import Blueprint, render_template
import sqlite3

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

def get_db_connection():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@reports_bp.route("/")
def dashboard_reportes():
    conn = get_db_connection()
    total_ventas = conn.execute("SELECT SUM(total) AS total FROM pedidos").fetchone()["total"]
    producto_mas_vendido = conn.execute("""
        SELECT p.nombre, SUM(pi.cantidad) AS cantidad
        FROM pedido_items pi
        JOIN productos p ON p.id = pi.producto_id
        GROUP BY p.id
        ORDER BY cantidad DESC
        LIMIT 1
    """).fetchone()
    stock_total = conn.execute("SELECT SUM(stock) AS total_stock FROM productos").fetchone()["total_stock"]
    conn.close()
    return render_template("reports_dashboard.html",
                           total_ventas=total_ventas,
                           producto_mas_vendido=producto_mas_vendido,
                           stock_total=stock_total)
