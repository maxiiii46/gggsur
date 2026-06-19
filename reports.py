from flask import Flask
from models import Order

app = Flask(__name__)

@app.route('/reports')
def reports():
    total_orders = Order.query.count()
    return f"Total de pedidos: {total_orders}"
