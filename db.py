import psycopg2
import psycopg2.extras
import json
import os
import hashlib

# ─── REPLACE THIS WITH YOUR NEON CONNECTION STRING ───────────────────────────
DATABASE_URL = "postgresql://neondb_owner:npg_YzwM7yVmifE4@ep-wandering-voice-amgka5wg-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    """Create tables if they don't exist, then seed products."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id               SERIAL PRIMARY KEY,
            name             TEXT NOT NULL,
            price            INTEGER NOT NULL,
            original_price   INTEGER NOT NULL,
            image            TEXT,
            category         TEXT,
            rating           NUMERIC(3,1),
            reviews          INTEGER,
            description      TEXT,
            specifications   JSONB DEFAULT '{}'
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            name          TEXT NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Orders table — stores pending/active orders
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id           SERIAL PRIMARY KEY,
            user_email   TEXT NOT NULL,
            user_name    TEXT NOT NULL,
            cart_items   JSONB NOT NULL,
            subtotal     INTEGER NOT NULL,
            discount     INTEGER NOT NULL DEFAULT 0,
            tax          INTEGER NOT NULL DEFAULT 0,
            total        INTEGER NOT NULL,
            status       TEXT NOT NULL DEFAULT 'pending',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Paid orders table — stores successfully paid/completed orders
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paid_orders (
            id              SERIAL PRIMARY KEY,
            order_id        INTEGER REFERENCES orders(id),
            user_email      TEXT NOT NULL,
            user_name       TEXT NOT NULL,
            cart_items      JSONB NOT NULL,
            subtotal        INTEGER NOT NULL,
            discount        INTEGER NOT NULL DEFAULT 0,
            tax             INTEGER NOT NULL DEFAULT 0,
            total           INTEGER NOT NULL,
            payment_method  TEXT NOT NULL DEFAULT 'online',
            transaction_ref TEXT,
            paid_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()

    # Only seed products if table is empty
    cur.execute("SELECT COUNT(*) FROM products;")
    count = cur.fetchone()[0]
    if count == 0:
        _seed(cur)
        conn.commit()

    cur.close()
    conn.close()


def _seed(cur):
    """Insert the original product list into Neon."""
    seed_products = [
        (1,"Galaxy S23",10,78500,"phone1.jpg","Mobile",4.5,285,"Premium flagship smartphone with cutting-edge technology",{"Display":"6.1 inch AMOLED, 120Hz","Processor":"Snapdragon 8 Gen 2","RAM":"8GB","Storage":"256GB","Camera":"50MP Main + 12MP Ultra + 10MP Telephoto","Battery":"4000 mAh, 25W Fast Charging","OS":"Android 13","Protection":"IP68 Water & Dust Resistant"}),
        (2,"iPhone 14",10,95000,"iphone 14.png","Mobile",4.7,512,"Latest Apple flagship with A15 Bionic chip",{"Display":"6.1 inch Super Retina XDR OLED","Processor":"Apple A15 Bionic","RAM":"6GB","Storage":"128GB","Camera":"12MP Dual Camera + 12MP Ultra Wide","Battery":"3200 mAh, 20W Fast Charging","OS":"iOS 16","Protection":"IP68 Water & Dust Resistant"}),
        (3,"Realme X",10,30000,"realmex.jpg","Mobile",4.2,145,"Budget-friendly smartphone with great performance",{"Display":"6.43 inch AMOLED, 90Hz","Processor":"Snapdragon 778G+","RAM":"6GB","Storage":"128GB","Camera":"64MP Main + 8MP Ultra Wide","Battery":"4500 mAh, 30W Fast Charging","OS":"Android 12","Protection":"IP54 Water Resistant"}),
        (4,"Redmi Note 4",10,23000,"redminote 4.jpg","Mobile",4.1,198,"Perfect for everyday use with excellent battery life",{"Display":"6.67 inch IPS LCD, 120Hz","Processor":"MediaTek Helio G95","RAM":"4GB","Storage":"64GB","Camera":"50MP Main + 8MP Ultra Wide","Battery":"5000 mAh, 33W Fast Charging","OS":"Android 12","Protection":"IP53 Water Resistant"}),
        (5,"OnePlus 11",10,60000,"oneplus11.png","Mobile",4.6,267,"Sleek design with powerful performance",{"Display":"6.7 inch AMOLED, 120Hz","Processor":"Snapdragon 8 Gen 2","RAM":"8GB","Storage":"256GB","Camera":"50MP Main + 48MP Ultra Wide","Battery":"5000 mAh, 100W Fast Charging","OS":"OxygenOS 13 (Android)","Protection":"IP69K Water & Dust Resistant"}),
        (6,"Google Pixel 7",10,72000,"nothing 7.jpg","Mobile",4.5,324,"Google's flagship with incredible camera AI",{"Display":"6.3 inch OLED, 90Hz","Processor":"Google Tensor","RAM":"8GB","Storage":"128GB","Camera":"50MP Main + 12MP Ultra Wide","Battery":"4355 mAh, 30W Fast Charging","OS":"Android 13","Protection":"IP68 Water & Dust Resistant"}),
        (7,"POCO X4",10,25000,"POCO X4.webp","Mobile",4.3,178,"Budget performance with great display",{"Display":"6.67 inch AMOLED, 120Hz","Processor":"Snapdragon 695","RAM":"6GB","Storage":"128GB","Camera":"48MP Main + 8MP Ultra Wide","Battery":"5000 mAh, 67W Fast Charging","OS":"Android 11","Protection":"IP53 Water Resistant"}),
        (8,"Moto G73",10,20000,"Moto G73.jpg","Mobile",4.0,89,"Reliable everyday phone with long battery life",{"Display":"6.5 inch IPS LCD, 90Hz","Processor":"MediaTek Helio G88","RAM":"4GB","Storage":"128GB","Camera":"50MP Main + 5MP Ultra Wide","Battery":"5000 mAh, 20W Fast Charging","OS":"Android 12","Protection":"IP52 Water Resistant"}),
        (9,"Samsung A53",10,48000,"Samsung A53.webp","Mobile",4.4,267,"Mid-range Samsung with AMOLED display",{"Display":"6.5 inch AMOLED, 120Hz","Processor":"Snapdragon 778G+","RAM":"6GB","Storage":"128GB","Camera":"64MP Main + 12MP Ultra Wide","Battery":"5000 mAh, 25W Fast Charging","OS":"Android 12","Protection":"IP67 Water & Dust Resistant"}),
        (10,"Vivo V23",10,58000,"Vivo V23.jpg","Mobile",4.3,201,"Camera-centric phone with beautiful design",{"Display":"6.44 inch AMOLED, 90Hz","Processor":"MediaTek Dimensity 920","RAM":"8GB","Storage":"128GB","Camera":"50MP Main + 8MP Ultra Wide","Battery":"4200 mAh, 44W Fast Charging","OS":"Android 12","Protection":"IP64 Water Resistant"}),
        (11,"Oppo A76",10,22000,"Oppo A76.webp","Mobile",4.2,112,"Lightweight and compact with good performance",{"Display":"6.56 inch IPS LCD, 90Hz","Processor":"Snapdragon 680","RAM":"4GB","Storage":"64GB","Camera":"50MP Main + 2MP Macro","Battery":"5000 mAh, 33W Fast Charging","OS":"Android 12","Protection":"IP54 Water Resistant"}),
        (12,"Nothing Phone 1",10,45000,"nothing 1.webp","Mobile",4.3,234,"Unique design with excellent software",{"Display":"6.55 inch OLED, 120Hz","Processor":"Snapdragon 778G+","RAM":"8GB","Storage":"128GB","Camera":"50MP Main + 50MP Ultra Wide","Battery":"4500 mAh, 33W Fast Charging","OS":"Nothing OS 1.1.3 (Android)","Protection":"IP54 Water Resistant"}),
        (13,"MacBook Pro 14",10,240000,"MacBook Pro 14.jpg","Electronics",4.8,450,"Powerful laptop for professionals with M2 Pro chip",{"Display":"14 inch Liquid Retina XDR","Processor":"Apple M2 Pro","RAM":"16GB","Storage":"512GB SSD","Graphics":"16-core GPU","Battery":"17 hours battery life","OS":"macOS Monterey","Ports":"3x Thunderbolt 4, HDMI, SD Card"}),
        (14,"iPad Air",10,100000,"iPad Air.jpg","Electronics",4.6,380,"Versatile tablet for work and entertainment",{"Display":"10.9 inch Liquid Retina IPS","Processor":"Apple M1 Chip","RAM":"8GB","Storage":"256GB","Camera":"12MP Wide + 12MP Ultra Wide","Battery":"Up to 10 hours","OS":"iPadOS 16","Features":"Face ID, Magic Keyboard Compatible"}),
        (15,"Sony WH-1000XM5",10,48000,"Sony WH-1000XM5.jpg","Electronics",4.7,520,"Premium noise-cancelling wireless headphones",{"Design":"Over-ear, Foldable","Noise Cancellation":"Industry-leading ANC","Battery":"30 hours battery life","Bluetooth":"5.3 Connectivity","Audio":"Hi-Res Audio Certified","Features":"Multipoint Connection, LDAC","Drivers":"30mm Driver Unit","Weight":"250 grams"}),
        (16,"Amazon Echo Pro",10,18000,"Amazon Echo Pro.jpg","Electronics",4.4,290,"Smart speaker with premium sound quality",{"Speaker":"3-inch woofer + 0.8-inch tweeter","Sound":"360° audio with dynamic bass","Microphone":"Far-field 4-mic array","Connectivity":"Dual-band Wi-Fi 6E","Features":"Alexa, Room Awareness, Adaptive Audio","Privacy":"Microphone & Camera OFF buttons","Dimensions":"103mm diameter, 129mm height","Power":"15W"}),
        (17,"Apple Watch Series 8",10,58000,"Apple Watch Series 8.jpg","Watches",4.7,410,"Advanced health and fitness tracking smartwatch",{"Display":"1.9 inch Retina LTPO OLED","Processor":"Apple S8","Storage":"32GB","Battery":"18 hours","Water Resistance":"50m Water Resistant","Health Features":"Temp Sensing, Cycle Tracking, ECG","Fitness":"100+ Workout Types","Compatibility":"iPhone 12 or later"}),
        (18,"Samsung Galaxy Watch 5",10,38000,"Samsung Galaxy Watch 5.webp","Watches",4.5,350,"Sleek smartwatch with AMOLED display",{"Display":"1.4/1.2 inch AMOLED","Processor":"Exynos W920","RAM":"1.5GB","Storage":"16GB","Battery":"Up to 40 hours","Water Resistance":"5ATM Water Resistant","Health":"BioActive Sensor, Sleep Tracking","Features":"NFC, Fitness Tracking, Music"}),
        (19,"Fitbit Sense 2",10,34999,"Fitbit Sense 2.jpg","Watches",4.3,275,"Health-focused wearable with advanced sensors",{"Display":"AMOLED Touchscreen","Battery":"Up to 6+ days","Health Tracking":"Heart Rate, SpO2, Skin Temperature","Stress Management":"EDA Sensor, Stress Detection","Sleep":"Advanced Sleep Tracking","Water Resistance":"50m Water Resistant","Compatibility":"iOS & Android","Features":"Bluetooth, Wi-Fi, NFC"}),
        (20,"Garmin Fenix 7",10,75000,"Garmin Fenix 7.jpg","Watches",4.6,320,"Professional sports watch for athletes",{"Display":"1.3 inch AMOLED","Battery":"Up to 14 days","GPS":"Multi-band GPS/GALILEO/GLONASS","Water Resistance":"100m Water Resistant","Sports":"170+ Sports Modes","Features":"Training Metrics, Recovery Coaching","Durability":"Fiber-reinforced Polymer Tech","Sensors":"10+ Onboard Sensors"}),
        (21,"Ergonomic Office Chair",10,25000,"Ergonomic Office Chair.jpg","Furniture",4.6,180,"Comfortable high-back office chair with lumbar support",{"Material":"Mesh Back + Cushioned Seat","Height Adjustment":"Gas Spring Lift","Armrests":"Adjustable 3D Armrests","Backrest":"Adjustable Recline & Lumbar","Base":"Heavy-duty Nylon 5-wheel Base","Weight Capacity":"120kg","Dimensions":"65 x 65 x 100-110 cm","Features":"Tilt Function, Breathing Mesh"}),
        (22,"Modern Study Table",10,18000,"Modern Study Table.jpg","Furniture",4.4,150,"Spacious computer desk for home office",{"Material":"engineered wood with PU finish","Dimensions":"120 x 60 x 75 cm","Drawers":"2 Side Drawers + 1 CPU Cabinet","Weight Capacity":"150kg","Color Options":"Walnut, White, Black","Assembly":"Self Assembly Required","Edge Protection":"ABS Edges","Features":"Cable Management, Spacious Surface"}),
        (23,"Leather Sofa",10,65000,"Leather Sofa.webp","Furniture",4.5,220,"Premium genuine leather sofa for living room",{"Material":"Genuine Leather","Type":"3-Seater","Dimensions":"225 x 90 x 85 cm","Seat Height":"40cm","Filling":"High Density Foam","Color":"Chocolate Brown","Comfort":"Premium Padding, Armrests","Durability":"5-year Warranty"}),
        (24,"Coffee Table",10,12500,"Coffee Table.webp","Furniture",4.3,110,"Modern glass and wood design coffee table",{"Material":"Tempered Glass + Wooden Frame","Dimensions":"100 x 50 x 45 cm","Glass Type":"Smoke Colored Tempered Glass","Wood":"Sheesham or Mango Wood","Storage":"Shelf below top surface","Weight Capacity":"80kg","Design":"Contemporary Minimalist","Assembly":"Easy Assembly Required"}),
        (25,"Premium Phone Case",10,1500,"Premium Phone Case.webp","Accessories",4.4,980,"Durable protective case with premium design",{"Compatibility":"Universal Fit (Multiple Sizes)","Material":"TPU + PC","Color":"Black, Blue, Red, Gold","Features":"Shockproof, Scratch Resistant","Protection":"Drop Test Certified 2-meter","Design":"Slim & Lightweight","Ports":"Precise Cutouts","Grip":"Non-Slip Textured Back"}),
        (26,"Fast Charging Adapter",10,1999,"Fast Charging Adapter.webp","Accessories",4.5,1250,"Universal fast charging adapter for all devices",{"Output":"65W USB-C + QC 3.0","Compatibility":"Phones, Tablets, Laptops","Ports":"Dual Port - Type-C + USB-A","Safety":"Multiple Protection Circuits","Input":"110-240V Universal","Cable":"1.5m Type-C Cable Included","Travel":"Foldable Prongs","Certification":"FCC, CE Certified"}),
        (27,"Power Bank 20000mAh",10,3500,"Power Bank 20000mAh.webp","Accessories",4.6,890,"High-capacity power bank with fast charging",{"Capacity":"20000mAh","Output":"65W USB-C + 2x USB-A","Input":"USB-C, Micro USB","Charging Speed":"Fast Charging Support","Full Charges":"5x iPhone or 2x Laptop","Display":"LED Percentage Display","Material":"Aluminum Casing","Weight":"450 grams"}),
        (28,"Tempered Glass Screen Protector",10,499,"Tempered Glass Screen Protector.webp","Accessories",4.3,750,"Ultra-clear tempered glass screen protection",{"Compatibility":"Universal Screen Sizes","Material":"Japan Asahi Tempered Glass","Hardness":"9H Rating","Thickness":"0.3mm Ultra-thin","Transparency":"99.9% Light Transmittance","Installation":"Easy Bubble-Free Application","Features":"Anti-fingerprint, Anti-glare","Quantity":"Pack of 2"}),
    ]
    cur.executemany("""
        INSERT INTO products (id,name,price,original_price,image,category,rating,reviews,description,specifications)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING;
    """, [(p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],json.dumps(p[9])) for p in seed_products])


# ── PRODUCT helpers ───────────────────────────────────────────────────────────

def row_to_dict(row):
    if not row: return None
    return {
        "id": row[0], "name": row[1], "price": row[2], "original_price": row[3],
        "image": row[4], "category": row[5],
        "rating": float(row[6]), "reviews": row[7], "description": row[8],
        "specifications": row[9] if row[9] else {}
    }

def get_all_products():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,name,price,original_price,image,category,rating,reviews,description,specifications FROM products ORDER BY id;")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [row_to_dict(r) for r in rows]

def get_product_by_id(product_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id,name,price,original_price,image,category,rating,reviews,description,specifications FROM products WHERE id=%s;", (product_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row_to_dict(row) if row else None

def add_product(name, price, original_price, image, category, rating, reviews, description, specifications):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO products (name,price,original_price,image,category,rating,reviews,description,specifications)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;
    """, (name, price, original_price, image, category, rating, reviews, description, json.dumps(specifications)))
    new_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return new_id

def update_product(product_id, name, price, original_price, image, category, rating, reviews, description, specifications):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE products
        SET name=%s, price=%s, original_price=%s, image=%s, category=%s,
            rating=%s, reviews=%s, description=%s, specifications=%s
        WHERE id=%s;
    """, (name, price, original_price, image, category, rating, reviews, description, json.dumps(specifications), product_id))
    conn.commit(); cur.close(); conn.close()

def delete_product(product_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s;", (product_id,))
    conn.commit(); cur.close(); conn.close()


# ── USER AUTH helpers ─────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(name, email, password):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s);",
            (name, email, hash_password(password))
        )
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()

def get_user_by_email(email):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, email, password_hash FROM users WHERE email = %s;",
        (email,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "email": row[2], "password_hash": row[3]}
    return None

def verify_user(email, password):
    user = get_user_by_email(email)
    if user and user["password_hash"] == hash_password(password):
        return user
    return None


# ── ORDER helpers ─────────────────────────────────────────────────────────────

def create_order(user_email, user_name, cart_items, subtotal, discount, tax, total):
    """Create a pending order and return its ID."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO orders (user_email, user_name, cart_items, subtotal, discount, tax, total, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending') RETURNING id;
    """, (user_email, user_name, json.dumps(cart_items), subtotal, discount, tax, total))
    order_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return order_id

def get_order_by_id(order_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_email, user_name, cart_items, subtotal, discount, tax, total, status, created_at
        FROM orders WHERE id = %s;
    """, (order_id,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        return None
    return {
        "id": row[0], "user_email": row[1], "user_name": row[2],
        "cart_items": row[3], "subtotal": row[4], "discount": row[5],
        "tax": row[6], "total": row[7], "status": row[8], "created_at": row[9]
    }

def get_orders_by_user(user_email):
    """Get all orders for a specific user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_email, user_name, cart_items, subtotal, discount, tax, total, status, created_at
        FROM orders WHERE user_email = %s ORDER BY created_at DESC;
    """, (user_email,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{
        "id": r[0], "user_email": r[1], "user_name": r[2],
        "cart_items": r[3], "subtotal": r[4], "discount": r[5],
        "tax": r[6], "total": r[7], "status": r[8], "created_at": r[9]
    } for r in rows]

def get_all_orders():
    """Admin: get all orders."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, user_email, user_name, cart_items, subtotal, discount, tax, total, status, created_at
        FROM orders ORDER BY created_at DESC;
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{
        "id": r[0], "user_email": r[1], "user_name": r[2],
        "cart_items": r[3], "subtotal": r[4], "discount": r[5],
        "tax": r[6], "total": r[7], "status": r[8], "created_at": r[9]
    } for r in rows]

def update_order_status(order_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s;", (status, order_id))
    conn.commit(); cur.close(); conn.close()


# ── PAID ORDER helpers ────────────────────────────────────────────────────────

def create_paid_order(order_id, user_email, user_name, cart_items, subtotal, discount, tax, total, payment_method="online", transaction_ref=None):
    """Move a completed order into paid_orders and mark the original as 'paid'."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO paid_orders (order_id, user_email, user_name, cart_items, subtotal, discount, tax, total, payment_method, transaction_ref)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
    """, (order_id, user_email, user_name, json.dumps(cart_items), subtotal, discount, tax, total, payment_method, transaction_ref))
    paid_id = cur.fetchone()[0]
    # Mark original order as paid
    cur.execute("UPDATE orders SET status = 'paid' WHERE id = %s;", (order_id,))
    conn.commit(); cur.close(); conn.close()
    return paid_id

def get_paid_orders_by_user(user_email):
    """Get all paid orders for a specific user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_id, user_email, user_name, cart_items, subtotal, discount, tax, total, payment_method, transaction_ref, paid_at
        FROM paid_orders WHERE user_email = %s ORDER BY paid_at DESC;
    """, (user_email,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{
        "id": r[0], "order_id": r[1], "user_email": r[2], "user_name": r[3],
        "cart_items": r[4], "subtotal": r[5], "discount": r[6],
        "tax": r[7], "total": r[8], "payment_method": r[9],
        "transaction_ref": r[10], "paid_at": r[11]
    } for r in rows]

def get_all_paid_orders():
    """Admin: get all paid orders."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, order_id, user_email, user_name, cart_items, subtotal, discount, tax, total, payment_method, transaction_ref, paid_at
        FROM paid_orders ORDER BY paid_at DESC;
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{
        "id": r[0], "order_id": r[1], "user_email": r[2], "user_name": r[3],
        "cart_items": r[4], "subtotal": r[5], "discount": r[6],
        "tax": r[7], "total": r[8], "payment_method": r[9],
        "transaction_ref": r[10], "paid_at": r[11]
    } for r in rows]