# driftrack/seed.py
"""Load demo sellers, listings, sales and reviews so the app looks alive.

Run:  python seed.py     (safe to re-run: it does nothing if demo data exists)
Demo login:  demo / demo123
"""
import os
import random
import time

import app

PALETTES = [("#ff4d8d", "#ffb347"), ("#7c5cff", "#22d3ee"), ("#00d4a6", "#b6ff5c"),
            ("#ff7a59", "#ffd166"), ("#4f8cff", "#c084fc"), ("#f43f5e", "#a855f7")]
SELLERS = [("demo", "Vintage hunter. Fast shipper.", "Austin"),
           ("mara_thrifts", "Closet clear-out, all smoke-free.", "Portland"),
           ("kofi_kicks", "Sneakers and streetwear.", "Atlanta"),
           ("june_and_co", "Kids and home finds.", "Denver"),
           ("retro_rae", "70s to 90s only.", "Chicago")]
ITEMS = [
    ("Levi's 501 straight jeans", "Levi's", "Women", "28", "Good", 34, "JEANS"),
    ("Oversized denim jacket", "Wrangler", "Vintage", "L", "Good", 48, "DENIM"),
    ("Air Max 90 trainers", "Nike", "Shoes", "9", "Like new", 72, "KICKS"),
    ("Quilted crossbody bag", "Coach", "Bags", "", "Like new", 95, "BAG"),
    ("Wool blend overcoat", "Zara", "Men", "M", "Good", 55, "COAT"),
    ("Floral midi dress", "Reformation", "Women", "S", "New with tags", 88, "DRESS"),
    ("Kids rain jacket", "Patagonia", "Kids", "5T", "Good", 26, "RAIN"),
    ("Ceramic table lamp", "West Elm", "Home", "", "Like new", 40, "LAMP"),
    ("Silk neck scarf", "Hermes style", "Accessories", "", "Good", 22, "SCARF"),
    ("Chunky knit cardigan", "Madewell", "Women", "M", "Like new", 38, "KNIT"),
    ("Leather Chelsea boots", "Dr. Martens", "Shoes", "10", "Good", 80, "BOOTS"),
    ("90s windbreaker", "Adidas", "Vintage", "XL", "Fair", 30, "RETRO"),
    ("Canvas tote bag", "Baggu", "Bags", "", "New with tags", 18, "TOTE"),
    ("Graphic band tee", "Unbranded", "Men", "L", "Good", 16, "TEE"),
    ("High-rise yoga leggings", "Lululemon", "Women", "6", "Like new", 45, "ACTIVE"),
    ("Toddler sneaker bundle", "Carter's", "Kids", "8", "Good", 20, "BUNDLE"),
    ("Corduroy bucket hat", "Carhartt", "Accessories", "", "Like new", 24, "HAT"),
    ("Linen throw blanket", "H&M Home", "Home", "", "New with tags", 28, "THROW"),
    ("Pleated tennis skirt", "Aritzia", "Women", "XS", "Like new", 32, "SKIRT"),
    ("Suede bomber jacket", "AllSaints", "Men", "M", "Good", 110, "SUEDE"),
    ("Platform sandals", "Steve Madden", "Shoes", "8", "Good", 29, "SANDAL"),
    ("70s paisley blouse", "Unbranded", "Vintage", "M", "Good", 27, "PAISLEY"),
    ("Gold hoop earrings", "Mejuri", "Accessories", "", "Like new", 36, "HOOPS"),
    ("Mini leather backpack", "Fossil", "Bags", "", "Good", 52, "PACK"),
]
REVIEWS = ["Exactly as described, shipped next day!", "Lovely seller, great packaging.",
           "Fits perfectly. Would buy again.", "Quick delivery and fair price.",
           "Item was cleaner than I expected. Thank you!"]


def card_svg(label, idx):
    a, b = PALETTES[idx % len(PALETTES)]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 720">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>
<rect width="600" height="720" fill="url(#g)"/>
<circle cx="{120 + idx * 37 % 360}" cy="210" r="170" fill="#fff" opacity=".13"/>
<circle cx="{470 - idx * 29 % 300}" cy="560" r="230" fill="#000" opacity=".12"/>
<path d="M300 150c-26 0-46 20-46 44 0 12 10 20 22 20s20-8 20-18" fill="none" stroke="#fff"
 stroke-width="12" stroke-linecap="round"/>
<path d="M300 214v36L110 370c-22 14-12 46 14 46h352c26 0 36-32 14-46L300 250" fill="none"
 stroke="#fff" stroke-width="12" stroke-linejoin="round" stroke-linecap="round"/>
<text x="300" y="560" text-anchor="middle" font-family="Arial Black,Arial,sans-serif"
 font-size="78" font-weight="900" fill="#fff" letter-spacing="4">{label}</text>
</svg>"""


def run():
    app.init_db()
    conn = app.db()
    if conn.execute("SELECT 1 FROM users WHERE is_demo=1").fetchone():
        print("  Demo data already loaded - nothing to do.")
        return
    rng = random.Random(8750)
    now = time.time()
    os.makedirs(app.UPLOADS, exist_ok=True)
    ids = [app.create_user(name, "demo123", bio=bio, city=city, is_demo=1,
                           created=now - 90 * 86400) for name, bio, city in SELLERS]
    listing_ids = []
    for i, (title, brand, cat, size, cond, price, label) in enumerate(ITEMS):
        name = f"seed_{i:02d}.svg"
        with open(os.path.join(app.UPLOADS, name), "w", encoding="utf-8") as fh:
            fh.write(card_svg(label, i))
        seller = ids[0] if i % 3 == 0 else ids[1 + i % 4]
        desc = app.local_description({"title": title, "brand": brand, "size": size,
                                      "condition": cond})
        cur = conn.execute(
            "INSERT INTO listings(seller_id,title,description,price,category,size,brand,"
            "condition,image,views,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (seller, title, desc, price, cat, size, brand, cond, "/uploads/" + name,
             rng.randint(8, 240), now - rng.uniform(0.2, 20) * 86400))
        listing_ids.append((cur.lastrowid, seller, price))
    for lid, seller, _ in listing_ids:  # likes
        for fan in rng.sample(ids, rng.randint(0, 4)):
            if fan != seller:
                conn.execute("INSERT OR IGNORE INTO favorites VALUES(?,?,?)",
                             (fan, lid, now - rng.uniform(0, 6) * 86400))
    # sales history for the demo seller so the dashboard chart has a story to tell
    sold_titles = ["Ribbed tank top", "Vintage Levi's shorts", "Leather belt", "Mom jeans",
                   "Puffer vest", "Band hoodie", "Slip dress", "Running shoes", "Beanie",
                   "Plaid flannel", "Cargo pants", "Trench coat"]
    for i, title in enumerate(sold_titles):
        when = now - rng.uniform(0.1, 13.5) * 86400
        price = float(rng.randint(14, 70))
        name = f"seed_sold_{i:02d}.svg"
        with open(os.path.join(app.UPLOADS, name), "w", encoding="utf-8") as fh:
            fh.write(card_svg("SOLD", i + 3))
        cur = conn.execute(
            "INSERT INTO listings(seller_id,title,description,price,category,condition,image,"
            "status,views,created) VALUES(?,?,?,?,?,?,?,'sold',?,?)",
            (ids[0], title, "", price, "Women", "Good", "/uploads/" + name,
             rng.randint(30, 300), when - 3 * 86400))
        buyer = rng.choice(ids[1:])
        status = "complete" if i % 4 else ("paid" if i % 8 else "shipped")
        order = conn.execute(
            "INSERT INTO orders(listing_id,buyer_id,seller_id,price,fee,status,created) "
            "VALUES(?,?,?,?,?,?,?)",
            (cur.lastrowid, buyer, ids[0], price,
             round(price * app.FEE_PCT + app.FEE_FLAT, 2), status, when))
        if status == "complete":
            conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (price, ids[0]))
            conn.execute("INSERT INTO reviews(order_id,seller_id,buyer_id,rating,text,created) "
                         "VALUES(?,?,?,?,?,?)", (order.lastrowid, ids[0], buyer,
                                                 rng.choice([4, 5, 5, 5]), rng.choice(REVIEWS),
                                                 when + 86400))
    demo_active = [x for x in listing_ids if x[1] == ids[0]]
    for lid, _, price in demo_active[:3]:  # pending offers waiting for the demo seller
        conn.execute("INSERT INTO offers(listing_id,buyer_id,amount,created) VALUES(?,?,?,?)",
                     (lid, rng.choice(ids[1:]), round(price * 0.8), now - rng.uniform(0, 2) * 3600))
    lid = demo_active[0][0]
    conn.execute("INSERT INTO messages(listing_id,from_id,to_id,body,created) VALUES(?,?,?,?,?)",
                 (lid, ids[1], ids[0], "Hi! Would you ship this today if I buy now?", now - 1800))
    conn.commit()
    print(f"  Demo data loaded: {len(SELLERS)} sellers, {len(ITEMS)} listings. "
          "Login: demo / demo123")


if __name__ == "__main__":
    run()
