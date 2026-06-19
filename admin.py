from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

def get_db_connection():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Middleware simple para verificar rol
def require_admin():
    if "rol" not in session or session["rol"] not in ["admin", "root"]:
        return False
    return True

@admin_bp.route("/")
def dashboard():
    if not require_admin():
        return redirect(url_for("login"))
    conn = get_db_connection()
    productos = conn.execute("SELECT * FROM productos").fetchall()
    pedidos = conn.execute("SELECT * FROM pedidos").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", productos=productos, pedidos=pedidos)

@admin_bp.route("/producto/nuevo", methods=["GET", "POST"])
def nuevo_producto():
    if not require_admin():
        return redirect(url_for("login"))
    if request.method == "POST":
        nombre = request.form["nombre"]
        precio = request.form["precio"]
        stock = request.form["stock"]
        conn = get_db_connection()
        conn.execute("INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)",
                     (nombre, precio, stock))
        conn.commit()
        conn.close()
        return redirect(url_for("admin.dashboard"))
    return render_template("admin_producto_form.html")

@admin_bp.route("/producto/eliminar/<int:id>")
def eliminar_producto(id):
    if not require_admin():
        return redirect(url_for("login"))
    conn = get_db_connection()
    conn.execute("DELETE FROM productos WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/pedido/<int:id>")
def detalle_pedido(id):
    if not require_admin():
        return redirect(url_for("login"))
    conn = get_db_connection()
    pedido = conn.execute("SELECT * FROM pedidos WHERE id = ?", (id,)).fetchone()
    items = conn.execute("SELECT * FROM pedido_items WHERE pedido_id = ?", (id,)).fetchall()
    conn.close()
    return render_template("admin_pedido_detalle.html", pedido=pedido, items=items)
