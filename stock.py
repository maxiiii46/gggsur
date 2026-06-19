from flask import Blueprint, render_template, request
import sqlite3

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")

def get_db_connection():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@stock_bp.route("/")
def stock_dashboard():
    conn = get_db_connection()
    productos = conn.execute("SELECT * FROM productos").fetchall()
    conn.close()
    return render_template("stock_dashboard.html", productos=productos)

@stock_bp.route("/actualizar/<int:id>", methods=["GET", "POST"])
def actualizar_stock(id):
    conn = get_db_connection()
    if request.method == "POST":
        nuevo_stock = request.form.get("stock")
        # Falencia: no valida si el valor es numérico ni positivo
        conn.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, id))
        conn.commit()
        conn.close()
        return "Stock actualizado (aunque puede ser inválido)."
    producto = conn.execute("SELECT * FROM productos WHERE id = ?", (id,)).fetchone()
    conn.close()
    return render_template("stock_form.html", producto=producto)
