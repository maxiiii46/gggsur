from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from twilio.rest import Client
import os

# Debajo de tus otros imports
from auth_utils import es_admin, obtener_pregunta_seguridad, validar_respuesta_y_cambiar_clave

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_secreta_cambiame")

DB = "database.db"

# Costos de envío por zona (FIX RF12)
COSTOS_ENVIO = {
    "caba": 1500.0,
    "gba": 2500.0,
    "interior": 4500.0,
}

# ──────────────────────────────────────────────
# BASE DE DATOS
# ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    print("Iniciando verificación de base de datos...")
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Tabla de Productos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                imagen TEXT,
                stock INTEGER DEFAULT 0
            )
        """)

        # Tabla de Pedidos (FIX RF06 + RF12: agregadas columnas de envío y pago)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_cliente TEXT NOT NULL,
                email TEXT NOT NULL,
                total REAL NOT NULL,
                direccion TEXT,
                zona_envio TEXT,
                costo_envio REAL DEFAULT 0,
                metodo_pago TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabla de Items de Pedido
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pedido_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                producto_id INTEGER,
                cantidad INTEGER,
                precio_unitario REAL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
        """)

        # Tabla de Usuarios (FIX INC-02: agregada columna 'rol')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL DEFAULT 'usuario'
            )
        """)

        # Crear un admin de ejemplo si no existe ninguno
        admin_existente = cursor.execute(
            "SELECT id FROM usuarios WHERE rol = 'admin' LIMIT 1"
        ).fetchone()
        if not admin_existente:
            cursor.execute(
                "INSERT OR IGNORE INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
                ("Administrador", "admin@mitienda.com",
                 generate_password_hash("admin123"), "admin")
            )

        # Insertar productos de ejemplo si la tabla está vacía
        cursor.execute("DELETE FROM productos")

        productos_ejemplo = [
            ("Remera básica", "100% algodón", 4500.0, "remera.jpg", 10),
            ("Pantalón cargo", "Con bolsillos", 8900.0, "pantalon.jpg", 5),
            ("Zapatillas urbanas", "Suela reforzada", 15000.0, "zapatillas.jpg", 8),
            ("Bici Estrella 1", "Rodado 29, aluminio", 450000.0, "bici1.jpg", 3),
            ("Bici Estrella 2", "Rodado 26, urbana", 380000.0, "bici2.jpg", 5),
            ("Casco Seguridad", "Certificado IRPC", 25000.0, "casco.jpg", 12),
            ("Inflador Mano", "Doble válvula", 8500.0, "inflador.jpg", 20),
            ("Luces LED Pack", "Delantera y trasera", 12000.0, "luces.jpg", 15),
            ("Cadena Acero", "Anti-robo cementada", 18000.0, "cadena.jpg", 10)
        ]
        cursor.executemany(
            "INSERT INTO productos (nombre, descripcion, precio, imagen, stock) VALUES (?, ?, ?, ?, ?)",
            productos_ejemplo
        )
        print("¡9 productos cargados exitosamente!")

        conn.commit()
        conn.close()
        print("Base de datos y tablas verificadas correctamente.")
    except Exception as e:
        print(f"ERROR al inicializar la base de datos: {e}")


# ──────────────────────────────────────────────
# NOTIFICACIONES (EMAIL + WHATSAPP)
# ──────────────────────────────────────────────
def enviar_email(destinatario, asunto, mensaje):
    remitente = "tuemail@gmail.com"
    password = "tu_password_app"
    msg = MIMEText(mensaje, "plain", "utf-8")
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remitente, password)
            server.sendmail(remitente, [destinatario], msg.as_string())
    except Exception as e:
        print(f"Error enviando email: {e}")


def enviar_whatsapp(destinatario, mensaje):
    account_sid = "TU_ACCOUNT_SID"
    auth_token = "TU_AUTH_TOKEN"
    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            from_="whatsapp:+14155238886",
            body=mensaje,
            to=f"whatsapp:{destinatario}"
        )
    except Exception as e:
        print(f"Error enviando WhatsApp: {e}")


# ──────────────────────────────────────────────
# HELPERS DEL CARRITO
# ──────────────────────────────────────────────
def get_carrito():
    return session.get("carrito", {})


def guardar_carrito(carrito):
    session["carrito"] = carrito


def total_carrito():
    carrito = get_carrito()
    if not carrito:
        return 0
    conn = get_db()
    total = 0
    for pid, cantidad in carrito.items():
        row = conn.execute("SELECT precio FROM productos WHERE id = ?", (pid,)).fetchone()
        if row:
            total += row["precio"] * cantidad
    conn.close()
    return total


# FIX INC-04: descuento de stock atómico y seguro ante concurrencia
def descontar_stock_seguro(conn, producto_id, cantidad):
    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE")
    row = cursor.execute(
        "SELECT stock FROM productos WHERE id = ?", (producto_id,)
    ).fetchone()

    if not row or row["stock"] < cantidad:
        conn.rollback()
        return False

    cursor.execute(
        "UPDATE productos SET stock = stock - ? WHERE id = ? AND stock >= ?",
        (cantidad, producto_id, cantidad)
    )
    return True


# ──────────────────────────────────────────────
# RUTAS — TIENDA
# ──────────────────────────────────────────────
@app.route("/")
def index():
    conn = get_db()
    productos = conn.execute("SELECT * FROM productos WHERE stock > 0").fetchall()
    conn.close()
    return render_template("index.html", productos=productos)


@app.route("/producto/<int:id>")
def producto(id):
    conn = get_db()
    p = conn.execute("SELECT * FROM productos WHERE id = ?", (id,)).fetchone()
    conn.close()
    if not p:
        return "Producto no encontrado", 404
    return render_template("producto.html", producto=p)


# ──────────────────────────────────────────────
# RUTAS — CARRITO
# ──────────────────────────────────────────────
@app.route("/carrito")
def carrito():
    carrito = get_carrito()
    items = []
    conn = get_db()
    for pid, cantidad in carrito.items():
        p = conn.execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
        if p:
            items.append({
                "id": p["id"],
                "nombre": p["nombre"],
                "precio": p["precio"],
                "cantidad": cantidad,
                "subtotal": p["precio"] * cantidad,
            })
    conn.close()
    return render_template("carrito.html", items=items, total=total_carrito())


@app.route("/carrito/agregar/<int:id>", methods=["POST"])
def agregar_al_carrito(id):
    carrito = get_carrito()
    cantidad = int(request.form.get("cantidad", 1))
    clave = str(id)
    carrito[clave] = carrito.get(clave, 0) + cantidad
    guardar_carrito(carrito)
    return redirect(url_for("carrito"))


@app.route("/carrito/quitar/<int:id>")
def quitar_del_carrito(id):
    carrito = get_carrito()
    carrito.pop(str(id), None)
    guardar_carrito(carrito)
    return redirect(url_for("carrito"))


@app.route("/carrito/vaciar")
def vaciar_carrito():
    session.pop("carrito", None)
    return redirect(url_for("carrito"))


# ──────────────────────────────────────────────
# RUTAS — CHECKOUT (FIX RF06 + RF12 + INC-04 + bug nombre truncado)
# ──────────────────────────────────────────────
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    carrito = get_carrito()
    if not carrito:
        return redirect(url_for("carrito"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        direccion = request.form.get("direccion", "").strip()
        zona = request.form.get("zona", "").strip().lower()
        metodo_pago = request.form.get("metodo_pago", "").strip()

        if not nombre or len(nombre) < 2:
            return render_template("checkout.html", error="Ingresá tu nombre completo.",
                                    total=total_carrito(), zonas=COSTOS_ENVIO)
        if not email:
            return render_template("checkout.html", error="Completá todos los campos.",
                                    total=total_carrito(), zonas=COSTOS_ENVIO)
        if not direccion:
            return render_template("checkout.html", error="Ingresá tu dirección de envío.",
                                    total=total_carrito(), zonas=COSTOS_ENVIO)
        if zona not in COSTOS_ENVIO:
            return render_template("checkout.html", error="Seleccioná una zona de envío válida.",
                                    total=total_carrito(), zonas=COSTOS_ENVIO)
        if not metodo_pago:
            return render_template("checkout.html", error="Seleccioná un método de pago.",
                                    total=total_carrito(), zonas=COSTOS_ENVIO)

        costo_envio = COSTOS_ENVIO[zona]
        subtotal = total_carrito()
        total = subtotal + costo_envio

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pedidos (nombre_cliente, email, total, direccion, zona_envio, "
            "costo_envio, metodo_pago) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nombre, email, total, direccion, zona, costo_envio, metodo_pago)
        )
        pedido_id = cursor.lastrowid

        items_sin_stock = []
        for pid, cantidad in carrito.items():
            p = conn.execute("SELECT precio FROM productos WHERE id = ?", (pid,)).fetchone()
            if not p:
                continue
            ok = descontar_stock_seguro(conn, int(pid), cantidad)
            if not ok:
                items_sin_stock.append(pid)
                continue
            cursor.execute(
                "INSERT INTO pedido_items (pedido_id, producto_id, cantidad, precio_unitario) "
                "VALUES (?, ?, ?, ?)",
                (pedido_id, int(pid), cantidad, p["precio"])
            )

        if items_sin_stock:
            conn.rollback()
            conn.close()
            return render_template(
                "checkout.html",
                error="Uno de los productos ya no tiene stock disponible. Volvé al carrito.",
                total=total_carrito(), zonas=COSTOS_ENVIO
            )

        conn.commit()
        conn.close()
        session.pop("carrito", None)

        mensaje = f"Hola {nombre}, gracias por tu compra.\nTu pedido #{pedido_id} fue confirmado por ${total:.2f}."
        # enviar_email(email, "Confirmación de compra - MiTienda", mensaje)

        return render_template("checkout.html", confirmado=True, nombre=nombre,
                                pedido_id=pedido_id, total=total, costo_envio=costo_envio)

    return render_template("checkout.html", total=total_carrito(), zonas=COSTOS_ENVIO)


# ──────────────────────────────────────────────
# RUTAS — USUARIOS (FIX INC-02: user_id y rol en sesión)
# ──────────────────────────────────────────────
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
                (nombre, email, password, "usuario")
            )
            conn.commit()
        except sqlite3.IntegrityError:
            return render_template("registro.html", error="El email ya está registrado.")
        finally:
            conn.close()
        return redirect(url_for("login"))
    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["usuario"] = user["nombre"]
            session["user_id"] = user["id"]
            session["rol"] = user["rol"]
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Email o contraseña incorrectos.")
    return render_template("login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    if not es_admin(session.get("user_id")):
        return "Acceso denegado. No sos admin, gato.", 403
    return render_template("admin.html")


# ──────────────────────────────────────────────
# BLOQUE DE ARRANQUE (MODO PRO)
# ──────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    app.run(debug=True)


