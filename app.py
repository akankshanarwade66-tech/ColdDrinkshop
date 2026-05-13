from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from models import LoginHistory
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'drinks.db')
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Drink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), default='https://via.placeholder.com/150')


class LoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    username = db.Column(db.String(150))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    drink_name = db.Column(db.String(100))
    qty = db.Column(db.Integer)
    price = db.Column(db.Float)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(300))
    payment_mode = db.Column(db.String(50), default="COD")  # payment mode
    status = db.Column(db.String(50), default="Pending")    # order status
    order_time = db.Column(db.DateTime, default=datetime.utcnow)

# --- Helper to load user ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---

@app.route('/')
def index():
    category = request.args.get('category', 'all')
    search = request.args.get('search', '')

    query = Drink.query
    if category != 'all':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Drink.name.contains(search))

    drinks = query.all()
    categories = ['all', 'Soft Drinks', 'Juices', 'Coffee', 'Tea', 'Smoothies']

    return render_template('index.html', drinks=drinks, categories=categories, current_cat=category, search=search)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            password=generate_password_hash(password, method='scrypt')
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            # Record login history
            new_login = LoginHistory(
                user_id=user.id,
                username=user.username,
                login_time=datetime.utcnow()
            )
            db.session.add(new_login)
            db.session.commit()

            if user.is_admin:
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('index'))

        else:
            flash('Invalid credentials.')

    return render_template('login.html')

@login_required
@app.route('/confirm_order/<int:order_id>')
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "Confirmed"
    db.session.commit()
    flash("Order confirmed successfully!")
    return redirect(url_for('admin'))

@app.route('/my_orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(username=current_user.username).all()
    return render_template("my_orders.html", orders=orders)

@app.route('/user_cancel_order/<int:order_id>')
@login_required
def user_cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.username != current_user.username:
        flash("You cannot cancel this order.")
        return redirect(url_for('my_orders'))
    if order.status == "Pending":
        order.status = "Cancelled"
        db.session.commit()
        flash("Your order has been cancelled.")
    return redirect(url_for('my_orders'))

@login_required
@app.route('/cancel_order/<int:order_id>')
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "Cancelled"
    db.session.commit()
    flash("Order cancelled. Product not available.")
    return redirect(url_for('admin'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- Cart Logic (Using Session) ---
@app.route('/add_to_cart/<int:drink_id>')
@login_required
def add_to_cart(drink_id):
    if 'cart' not in session:
        session['cart'] = []
    drink = Drink.query.get_or_404(drink_id)

    # Check if item exists
    for item in session['cart']:
        if item['id'] == drink_id:
            item['qty'] += 1
            break
    else:
        session['cart'].append({'id': drink.id, 'name': drink.name, 'price': drink.price, 'qty': 1})
    session.modified = True
    flash("item added to cart!")
    return redirect(request.referrer)

@app.route('/cart')
@login_required
def cart():
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('index'))
    total = sum(item['price'] * item['qty'] for item in session['cart'])
    return render_template('cart.html', cart=session['cart'], total=total)


@app.route('/remove_from_cart/<int:drink_id>')
@login_required
def remove_from_cart(drink_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != drink_id]
        session.modified = True
    return redirect(url_for('cart'))
@app.route('/increase_qty/<int:drink_id>')
def increase_qty(drink_id):
    cart = session.get('cart', [])
    for item in cart:
        if item['id'] == drink_id:
            item['qty'] += 1
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/decrease_qty/<int:drink_id>')
def decrease_qty(drink_id):
    cart = session.get('cart', [])
    for item in cart:
        if item['id'] == drink_id:
            if item['qty'] > 1:
                item['qty'] -= 1
            else:
                cart.remove(item)

            break
    session['cart'] = cart
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('index'))
    total = sum(item['price'] * item['qty'] for item in session['cart'])
    if request.method == 'POST':
        phone = request.form.get('phone')
        address = request.form.get('address')
        # --- save each item in cart to Order table ---
        for item in session['cart']:
            order = Order(
                username=current_user.username,
                drink_name=item['name'],
                qty=item['qty'],
                price=item['price'] * item['qty'],
                phone=phone,
                address=address,
                status="Pending",  # ye field ab model me hai
                payment_mode="COD"  # ye field bhi model me hai
            )
            db.session.add(order)
        db.session.commit()
        session.pop('cart', None)  # cart clear
        order_msg = "🎉 Order Confirmed! Your order will be delivered soon."
        return render_template('checkout.html', success=True, msg=order_msg, total=total, phone=phone, address=address)
    return render_template('checkout.html', success=False, total=total)

@app.route('/admin')
@login_required
def admin():
    if not getattr(current_user, 'is_admin', False):
        flash("Access denied! Only admin can view this page.")
        return redirect(url_for('index'))
    products = Drink.query.all()  # products list
    orders = Order.query.order_by(Order.order_time.desc()).all() # latest orders
    total_orders = Order.query.count()
    confirmed_orders = Order.query.filter_by(status="Confirmed").count()
    pending_orders = Order.query.filter_by(status="Pending").count()
    total_revenue = db.session.query(db.func.sum(Order.price)).scalar() or 0

    # Prepare admin popup message if there are pending orders
    admin_popup = None
    if pending_orders > 0:
        admin_popup = f"🔔 You have {pending_orders} new order(s) to process!"
    sales_data = db.session.query(
        func.date(Order.order_time),
        func.sum(Order.price)
    ).group_by(func.date(Order.order_time)).all()

    dates = [str(d[0]) for d in sales_data]
    sales = [float(d[1]) for d in sales_data]

    return render_template(
        'admin.html',
        products=products,
        orders=orders,
        pending_orders=pending_orders,
        admin_popup=admin_popup,
        total_revenue=total_revenue,
        confirmed_orders=confirmed_orders,
        dates=dates,
        sales=sales,
        total_orders=total_orders

    )

@app.route('/admin/logins')
@login_required
def admin_logins():
    if not getattr(current_user, 'is_admin', False):
        flash("Access denied! Only admin can view this page.")
        return redirect(url_for('index'))

    history = LoginHistory.query.order_by(LoginHistory.login_time.desc()).all()
    return render_template('login_history.html', history=history)
@app.route('/admin/add_product', methods=['GET','POST'])
@login_required
def add_product():
    if not getattr(current_user, 'is_admin', False):
        flash("Access denied!")
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        price = request.form.get('price')
        image = request.form.get('image')

        new_drink = Drink(
            name=name,
            category=category,
            price=price,
            image=image
        )

        db.session.add(new_drink)
        db.session.commit()
        flash("Product Added Successfully!")
        return redirect(url_for('admin'))
    return render_template('add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET','POST'])
@login_required
def edit_product(product_id):
    if not getattr(current_user, 'is_admin', False):
        flash("Access denied!")
        return redirect(url_for('index'))

    product = Drink.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.category = request.form.get('category')
        product.price = request.form.get('price')
        product.image = request.form.get('image')
        db.session.commit()
        flash("Product updated successfully!")
        return redirect(url_for('admin'))
    return render_template('edit_product.html', product=product)

@app.route('/admin/delete_product/<int:product_id>')
@login_required
def delete_product(product_id):
    if not getattr(current_user, 'is_admin', False):
        flash("Access denied!")
        return redirect(url_for('index'))
    product = Drink.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!")
    return redirect(url_for('admin'))

@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash("Password updated successfully. Please login.", "success")
            return redirect(url_for('login'))
        else:
            flash("Username not found!", "danger")
    return render_template('forgot_password.html')

def init_db():
    with app.app_context():
        if Drink.query.count() == 0:
            drinks = [
                Drink(name="Coca Cola", category="Soft Drinks", price=90, image="images/coca.jpg"),
                Drink(name="Sprite", category="Soft Drinks", price=70, image="images/sprite.jpg"),
                Drink(name="Orange Juice", category="Juices", price=100, image="images/orangejuice.jpg"),
                Drink(name="Apple Juice", category="Juices", price=150, image="images/applejuice.jpg"),
                Drink(name="Espresso", category="Coffee", price=200, image="images/espresso.jpg"),
                Drink(name="Latte", category="Coffee", price=250, image="images/latte.jpg"),
                Drink(name="Green Tea macha ", category="Tea", price=300, image="images/greentea.jpg"),
                Drink(name="Berry Smoothie", category="Smoothies", price=260, image="images/berry.jpg"),
                Drink(name="Mango Lassi", category="Juices", price=120, image="images/mango.jpg"),
                Drink(name="Iced Coffee", category="Coffee", price=199, image="images/icedcoffee.jpg"),
            ]
            db.session.add_all(drinks)
            db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # create admin if not exists
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                password=generate_password_hash("admin123"),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    init_db()
    app.run(debug=True)