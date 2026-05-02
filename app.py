import time
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from db import (
    init_db, get_all_products, get_product_by_id,
    add_product, update_product, delete_product,
    create_user, verify_user,
    create_order, get_order_by_id, get_orders_by_user, get_all_orders, update_order_status,
    create_paid_order, get_paid_orders_by_user, get_all_paid_orders
)

app = Flask(__name__)
app.secret_key = "your-secret-key-here-change-in-production"

ADMIN_PASSWORD = "12345678"

with app.app_context():
    init_db()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

def format_price(price):
    return f"₹{price:,}"

@app.route("/store")
def home():
    products = get_all_products()

    return render_template(
        "home.html",
        products=products,
        format_price=format_price
    )

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        role = request.form.get("role")
        if role == "admin":
            password = request.form.get("password")
            if password == ADMIN_PASSWORD:
                session["admin_logged_in"] = True
                return redirect(url_for("admin"))
            else:
                return render_template("index.html", error="Invalid admin password.")
        else:
            email = request.form.get("email")
            password = request.form.get("password")
            if email and password:
                user = verify_user(email, password)
                if user:
                    session["user_logged_in"] = True
                    session["user_email"] = email
                    session["user_name"] = user["name"]
                    session.modified = True
                    return redirect(url_for("home"))
                else:
                    return render_template("index.html", error="Invalid email or password.")
            else:
                return render_template("index.html", error="Email and password are required.")
    return render_template("index.html")

@app.route("/search")
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return redirect(url_for("home"))

    all_products = get_all_products()
    search_results = [
        p for p in all_products
        if query in p.get("name", "").lower()
        or query in p.get("category", "").lower()
        or query in p.get("description", "").lower()
    ]

    def relevance_score(product):
        score = 0
        if query in product.get("name", "").lower(): score += 100
        if query in product.get("category", "").lower(): score += 50
        if query in product.get("description", "").lower(): score += 25
        return -score

    search_results.sort(key=relevance_score)
    return render_template("search_results.html", query=query,
                           results=search_results, result_count=len(search_results))

@app.route("/product/<int:product_id>")
def product_details(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return render_template("404.html", message="Product not found"), 404
    return render_template("product_details.html", product=product, format_price=format_price)

@app.route("/category/<category_name>")
def category(category_name):
    all_products = get_all_products()
    category_products = [p for p in all_products if p["category"].lower() == category_name.lower()]
    if not category_products:
        return render_template("404.html", message=f"Category '{category_name}' not found"), 404
    return render_template("category.html", category_name=category_name,
                           products=category_products, format_price=format_price)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if email and password:
            user = verify_user(email, password)
            if user:
                session["user_logged_in"] = True
                session["user_email"] = email
                session["user_name"] = user["name"]
                session.modified = True
                return jsonify({"message": f"Welcome back, {user['name']}!", "status": "success"})
            else:
                return jsonify({"message": "Invalid email or password.", "status": "error"}), 401
        else:
            return jsonify({"message": "Email and password are required", "status": "error"}), 400
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            return render_template("signup.html", error="All fields are required.")
        if len(password) < 6:
            return render_template("signup.html", error="Password must be at least 6 characters.", name=name, email=email)
        if password != confirm:
            return render_template("signup.html", error="Passwords do not match.", name=name, email=email)

        success = create_user(name, email, password)
        if success:
            return render_template("signup.html", success="Account created! You can now log in.")
        else:
            return render_template("signup.html", error="An account with this email already exists.", name=name)

    return render_template("signup.html")

@app.route("/user-logout", methods=["POST"])
def user_logout():
    session["user_logged_in"] = False
    session.pop("user_email", None)
    session.modified = True
    return redirect(url_for("home"))

@app.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return jsonify({"message": "Product not found", "status": "error"}), 404

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]
    product_id_str = str(product_id)

    if product_id_str in cart:
        cart[product_id_str]["quantity"] += 1
    else:
        cart[product_id_str] = {
            "id": product["id"], "name": product["name"],
            "price": product["price"], "image": product["image"], "quantity": 1
        }

    session.modified = True
    cart_count = sum(item["quantity"] for item in cart.values())
    return jsonify({"message": f"{product['name']} added to cart!", "status": "success", "cart_count": cart_count})

@app.route("/cart")
def view_cart():
    cart = session.get("cart", {})
    cart_items = []
    total_price = 0
    for product_id_str, item in cart.items():
        item_total = item["price"] * item["quantity"]
        total_price += item_total
        cart_items.append({
            "id": item["id"], "name": item["name"], "price": item["price"],
            "image": item["image"], "quantity": item["quantity"], "total": item_total
        })
    cart_count = sum(item["quantity"] for item in cart.values())
    return render_template("cart.html", cart_items=cart_items, total_price=total_price,
                           cart_count=cart_count, format_price=format_price)

@app.route("/remove-from-cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    product_id_str = str(product_id)
    if product_id_str in cart:
        del cart[product_id_str]
        session.modified = True
    cart_count = sum(item["quantity"] for item in cart.values())
    return jsonify({"message": "Item removed from cart", "status": "success", "cart_count": cart_count})

@app.route("/update-cart/<int:product_id>/<int:quantity>", methods=["POST"])
def update_cart(product_id, quantity):
    cart = session.get("cart", {})
    product_id_str = str(product_id)
    if quantity <= 0:
        if product_id_str in cart:
            del cart[product_id_str]
    elif product_id_str in cart:
        cart[product_id_str]["quantity"] = quantity
    session.modified = True
    total_price = sum(item["price"] * item["quantity"] for item in cart.values())
    cart_count = sum(item["quantity"] for item in cart.values())
    return jsonify({
        "message": "Cart updated", "status": "success", "cart_count": cart_count,
        "item_total": cart[product_id_str]["price"] * quantity if product_id_str in cart else 0,
        "total_price": total_price
    })

@app.route("/clear-cart", methods=["POST"])
def clear_cart():
    session["cart"] = {}
    session.modified = True
    return jsonify({"message": "Cart cleared", "status": "success", "cart_count": 0})

@app.route("/get-cart-count")
def get_cart_count():
    cart = session.get("cart", {})
    cart_count = sum(item["quantity"] for item in cart.values())
    return jsonify({"cart_count": cart_count})

@app.route("/checkout-page")
def checkout_page():
    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("view_cart"))
    subtotal = sum(item["price"] * item["quantity"] for item in cart.values())
    discount = int(subtotal * 0.15)
    tax = int((subtotal - discount) * 0.18)
    final_total = subtotal - discount + tax
    return render_template("checkout.html", final_total=final_total, format_price=format_price)

# ── FIXED: handles both fetch (JSON) and normal form POST ────────────────────
@app.route("/process-payment", methods=["POST"])
def process_payment():
    try:
        cart = session.get("cart", {})
        if not cart:
            # Detect if request is AJAX/fetch
            if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"status": "error", "message": "Cart is empty"}), 400
            return redirect(url_for("view_cart"))

        cart_items = list(cart.values())
        subtotal = sum(item["price"] * item["quantity"] for item in cart_items)
        discount = int(subtotal * 0.15)
        tax = int((subtotal - discount) * 0.18)
        total = subtotal - discount + tax

        user_email = session.get("user_email", "guest@example.com")
        user_name = session.get("user_name", "Guest")

        # Support both JSON body and form data
        if request.is_json:
            data = request.get_json() or {}
            payment_method = data.get("payment_method", "online")
        else:
            payment_method = request.form.get("payment_method", "online")

        order_id = create_order(
            user_email=user_email,
            user_name=user_name,
            cart_items=cart_items,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total
        )

        transaction_ref = f"TXN-{order_id}-{int(time.time())}"

        create_paid_order(
            order_id=order_id,
            user_email=user_email,
            user_name=user_name,
            cart_items=cart_items,
            subtotal=subtotal,
            discount=discount,
            tax=tax,
            total=total,
            payment_method=payment_method,
            transaction_ref=transaction_ref
        )

        session["cart"] = {}
        session.modified = True

        # If AJAX/fetch request — return JSON with redirect URL
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "status": "success",
                "message": "Order placed successfully!",
                "order_id": order_id,
                "transaction_ref": transaction_ref,
                "redirect": url_for("home", order_placed="true")
            })

        # Normal form POST — do a redirect
        return redirect(url_for("home", order_placed="true"))

    except Exception as e:
        app.logger.error(f"Payment processing error: {e}")
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "error", "message": f"Could not place order. {str(e)}"}), 500
        return redirect(url_for("checkout_page"))

# ── USER ORDER HISTORY ────────────────────────────────────────────────────────

@app.route("/my-orders")
def my_orders():
    if not session.get("user_logged_in"):
        return redirect(url_for("login"))
    user_email = session.get("user_email")
    paid_orders = get_paid_orders_by_user(user_email)
    return render_template("my_orders.html", paid_orders=paid_orders, format_price=format_price)

# ── ADMIN ROUTES ──────────────────────────────────────────────────────────────

@app.route("/admin-login")
def admin_login():
    error = request.args.get("error")
    return render_template("admin_login.html", error=error)

@app.route("/admin-login-submit", methods=["POST"])
def admin_login_submit():
    password = request.form.get("password")
    if password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return redirect(url_for("admin"))
    return render_template("admin_login.html", error="Invalid password. Please try again.")

@app.route("/admin")
@admin_required
def admin():
    products = get_all_products()
    return render_template("admin.html", products=products)

@app.route("/admin/add-product", methods=["POST"])
@admin_required
def admin_add_product():
    try:
        spec_keys = request.form.getlist('spec_keys[]')
        spec_values = request.form.getlist('spec_values[]')
        specifications = {k: v for k, v in zip(spec_keys, spec_values) if k and v}

        add_product(
            name=request.form.get("name"),
            price=int(request.form.get("price")),
            original_price=int(request.form.get("original_price")),
            image=request.form.get("image"),
            category=request.form.get("category"),
            rating=float(request.form.get("rating")),
            reviews=int(request.form.get("reviews")),
            description=request.form.get("description"),
            specifications=specifications
        )
        return redirect(url_for("admin"))
    except Exception as e:
        products = get_all_products()
        return render_template("admin.html", products=products, error=str(e))

@app.route("/admin/edit/<int:product_id>")
@admin_required
def admin_edit_product(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return render_template("edit_product.html", error="Product not found"), 404
    return render_template("edit_product.html", product=product)

@app.route("/admin/update-product/<int:product_id>", methods=["POST"])
@admin_required
def admin_update_product(product_id):
    try:
        spec_keys = request.form.getlist('spec_keys[]')
        spec_values = request.form.getlist('spec_values[]')
        specifications = {k: v for k, v in zip(spec_keys, spec_values) if k and v}

        update_product(
            product_id=product_id,
            name=request.form.get("name"),
            price=int(request.form.get("price")),
            original_price=int(request.form.get("original_price")),
            image=request.form.get("image"),
            category=request.form.get("category"),
            rating=float(request.form.get("rating")),
            reviews=int(request.form.get("reviews")),
            description=request.form.get("description"),
            specifications=specifications
        )
        return redirect(url_for("admin"))
    except Exception as e:
        product = get_product_by_id(product_id)
        return render_template("edit_product.html", product=product, error=str(e))

@app.route("/admin/delete-product/<int:product_id>", methods=["POST"])
@admin_required
def admin_delete_product(product_id):
    delete_product(product_id)
    return redirect(url_for("admin"))

@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = get_all_orders()
    return render_template("admin_orders.html", orders=orders, format_price=format_price)

@app.route("/admin/paid-orders")
@admin_required
def admin_paid_orders():
    paid_orders = get_all_paid_orders()
    return render_template("admin_paid_orders.html", paid_orders=paid_orders, format_price=format_price)

@app.route("/admin/update-order-status/<int:order_id>", methods=["POST"])
@admin_required
def admin_update_order_status(order_id):
    status = request.form.get("status")
    update_order_status(order_id, status)
    return redirect(url_for("admin_orders"))

@app.route("/admin-logout", methods=["POST"])
def admin_logout():
    session["admin_logged_in"] = False
    session.modified = True
    return redirect(url_for("home"))


# ✅ This must be OUTSIDE all functions
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)