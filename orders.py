from flask import Flask, render_template
from models import Order

app = Flask(__name__)

@app.route('/orders')
def orders():
    orders = Order.query.all()
    return render_template('orders.html', orders=orders)
