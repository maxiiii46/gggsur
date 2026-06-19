from models import Product, db

def process_order(product_id, quantity):
    product = Product.query.get(product_id)
    product.stock -= quantity
    db.session.commit()
