# 🛒 Tienda Virtual - Enterprise Infrastructure & Production Deployment

Aplicación web de comercio electrónico basada en **Flask**, rediseñada y optimizada bajo prácticas de **DevOps y System Administration** para garantizar despliegues automatizados, persistencia de datos y alta disponibilidad mediante contenedores.

---

## 🛠️ Stack Tecnológico de Infraestructura

* **Containerización:** Docker & Docker Compose para aislamiento de microservicios.
* **Orquestación de Base de Datos:** Migración de SQLite local a **PostgreSQL 15** para entornos de producción.
* **Persistencia de Datos (Storage):** Volúmenes de Docker gestionados para asegurar la persistencia del estado de la base de datos y evitar pérdida de información en el ciclo de vida del contenedor.
* **Networking:** Red privada interna tipo `bridge` para aislar el motor de base de datos del exterior, permitiendo únicamente el tráfico originado por la aplicación Flask.
* **Security & Config:** Inyección de credenciales sensibles y `secret_key` mediante variables de entorno (`.env`), evitando el hardcoding en el código fuente.

---

## 📂 Arquitectura del Proyecto (Estructura DevOps)

```text
tienda-04-26/
│
├── app.py                  # Servidor Flask e inicialización de la app
├── Dockerfile              # Configuración Multi-stage para optimización de imagen
├── docker-compose.yml      # Orquestador de servicios (App + DB + Volumes + Networks)
├── .env.example            # Plantilla de variables de entorno seguras
├── requirements.txt        # Dependencias de la aplicación[cite: 1]
├── models/
│   └── db.py               # Capa de abstracción y conexión a Base de Datos Relacional[cite: 1]
├── templates/              # Vistas HTML de la interfaz de usuario[cite: 1]
└── static/                 # Recursos estáticos (CSS, JS, imágenes de catálogo)[cite: 1]