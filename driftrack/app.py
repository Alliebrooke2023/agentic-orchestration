# driftrack/app.py
"""DriftRack - a pre-loved fashion marketplace. Python stdlib only, no installs.

Run:  python app.py            (http://127.0.0.1:8750)
      python app.py --seed     (load demo data first, then run)
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import mailer
import payments

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
DATA = os.environ.get("DRIFTRACK_DATA", os.path.join(ROOT, "data"))
UPLOADS = os.path.join(DATA, "uploads")
DB_PATH = os.path.join(DATA, "driftrack.db")
HOST = os.environ.get("DRIFTRACK_HOST", "127.0.0.1")
PORT = int(os.environ.get("DRIFTRACK_PORT", "8750"))
PUBLIC_URL = os.environ.get("DRIFTRACK_PUBLIC_URL", "").rstrip("/")
SECURE_COOKIES = os.environ.get("DRIFTRACK_SECURE_COOKIES") == "1"
TRUST_PROXY = os.environ.get("DRIFTRACK_TRUST_PROXY") == "1"
VALID_ORDER = "status IN ('paid','shipped','complete')"
PAY_WINDOW = 35 * 60  # seconds a listing stays reserved while the buyer is on Stripe
LIMITS = {"login": (5, 900), "register": (10, 3600), "forgot": (5, 3600), "report": (20, 3600)}
CSP = ("default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
       "script-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; "
       "base-uri 'none'")

CATEGORIES = ["Women", "Men", "Kids", "Shoes", "Bags", "Accessories", "Home", "Vintage"]
CONDITIONS = ["New with tags", "Like new", "Good", "Fair"]
FEE_PCT, FEE_FLAT = 0.05, 0.70  # buyer protection fee
MAX_BODY = 6 * 1024 * 1024
DEFAULT_ADS = [
    "FLASH DROP - 30% off all denim this weekend",
    "FREE SHIPPING on bundles of 3 or more",
    "NEW SELLERS - your first 5 listings get a boost",
    "VINTAGE WEEK - tag it #retro and get featured",
    "MAKE AN OFFER - sellers answer in under an hour",
]

_local = threading.local()
_write_lock = threading.Lock()
_rate_lock = threading.Lock()
RATE = {}


def rate_hit(kind, key, record=True):
    """Sliding-window limiter. Raises 429 once the limit for (kind, key) is reached."""
    limit, window = LIMITS[kind]
    now = time.time()
    with _rate_lock:
        hits = [t for t in RATE.get((kind, key), []) if t > now - window]
        if len(hits) >= limit:
            RATE[(kind, key)] = hits
            wait = int(hits[0] + window - now) // 60 + 1
            raise ApiError(429, f"Too many attempts. Try again in {wait} min.")
        if record:
            hits.append(now)
        RATE[(kind, key)] = hits


def rate_clear(kind, key):
    with _rate_lock:
        RATE.pop((kind, key), None)


def db():
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(UPLOADS, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL COLLATE NOCASE,
  pw TEXT NOT NULL, salt TEXT NOT NULL, bio TEXT DEFAULT '', city TEXT DEFAULT '',
  balance REAL DEFAULT 0, is_owner INTEGER DEFAULT 0, is_demo INTEGER DEFAULT 0,
  created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(
  token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS listings(
  id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL, title TEXT NOT NULL,
  description TEXT DEFAULT '', price REAL NOT NULL, category TEXT NOT NULL,
  size TEXT DEFAULT '', brand TEXT DEFAULT '', condition TEXT NOT NULL,
  image TEXT DEFAULT '', status TEXT DEFAULT 'active', views INTEGER DEFAULT 0,
  created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS favorites(
  user_id INTEGER, listing_id INTEGER, created REAL, PRIMARY KEY(user_id, listing_id));
CREATE TABLE IF NOT EXISTS offers(
  id INTEGER PRIMARY KEY, listing_id INTEGER, buyer_id INTEGER, amount REAL,
  status TEXT DEFAULT 'pending', created REAL);
CREATE TABLE IF NOT EXISTS orders(
  id INTEGER PRIMARY KEY, listing_id INTEGER, buyer_id INTEGER, seller_id INTEGER,
  price REAL, fee REAL, status TEXT DEFAULT 'paid', created REAL);
CREATE TABLE IF NOT EXISTS reviews(
  id INTEGER PRIMARY KEY, order_id INTEGER UNIQUE, seller_id INTEGER,
  buyer_id INTEGER, rating INTEGER, text TEXT, created REAL);
CREATE TABLE IF NOT EXISTS messages(
  id INTEGER PRIMARY KEY, listing_id INTEGER, from_id INTEGER, to_id INTEGER,
  body TEXT, created REAL);
CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY, text TEXT NOT NULL, created REAL);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY, listing_id INTEGER, reporter_id INTEGER, reason TEXT,
  status TEXT DEFAULT 'open', created REAL);
CREATE TABLE IF NOT EXISTS resets(
  token_hash TEXT PRIMARY KEY, user_id INTEGER, created REAL, used INTEGER DEFAULT 0);
"""
MIGRATIONS = [("users", "email", "TEXT DEFAULT ''"), ("users", "banned", "INTEGER DEFAULT 0"),
              ("orders", "stripe_session", "TEXT DEFAULT ''")]


def init_db():
    conn = db()
    conn.executescript(SCHEMA)
    for table, col, decl in MIGRATIONS:  # upgrade databases made by older builds
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    conn.execute("DELETE FROM sessions WHERE created<?", (time.time() - 30 * 86400,))
    if conn.execute("SELECT COUNT(*) FROM ads").fetchone()[0] == 0:
        conn.executemany("INSERT INTO ads(text,created) VALUES(?,?)",
                         [(t, time.time()) for t in DEFAULT_ADS])
    conn.commit()


def hash_pw(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()


def create_user(username, password, **extra):
    salt = secrets.token_hex(16)
    cur = db().execute(
        "INSERT INTO users(username,pw,salt,bio,city,is_owner,is_demo,created) VALUES(?,?,?,?,?,?,?,?)",
        (username, hash_pw(password, salt), salt, extra.get("bio", ""), extra.get("city", ""),
         extra.get("is_owner", 0), extra.get("is_demo", 0), extra.get("created", time.time())))
    return cur.lastrowid


class ApiError(Exception):
    def __init__(self, status, msg):
        super().__init__(msg)
        self.status, self.msg = status, msg


def need(cond, msg, status=400):
    if not cond:
        raise ApiError(status, msg)


def clean(value, limit):
    return str(value or "").strip()[:limit]


def to_price(value):
    try:
        p = round(float(value), 2)
    except (TypeError, ValueError):
        raise ApiError(400, "Price must be a number")
    need(0.5 <= p <= 100000, "Price must be between 0.50 and 100,000")
    return p


def save_image(data_url):
    """Accept a base64 data URL (png/jpeg/webp), verify magic bytes, store on disk."""
    if not data_url:
        return ""
    m = re.match(r"^data:image/(png|jpeg|webp);base64,(.+)$", data_url, re.S)
    need(m, "Image must be PNG, JPEG or WEBP")
    try:
        raw = base64.b64decode(m.group(2), validate=True)
    except Exception:
        raise ApiError(400, "Image data is corrupt")
    need(len(raw) <= 4 * 1024 * 1024, "Image too large (4 MB max)")
    kinds = {b"\x89PNG": "png", b"\xff\xd8\xff": "jpg", b"RIFF": "webp"}
    ext = next((e for magic, e in kinds.items() if raw.startswith(magic)), None)
    need(ext, "Image content does not match its type")
    name = secrets.token_hex(12) + "." + ext
    os.makedirs(UPLOADS, exist_ok=True)
    with open(os.path.join(UPLOADS, name), "wb") as fh:
        fh.write(raw)
    return "/uploads/" + name


LISTING_SQL = """
SELECT l.*, u.username AS seller,
  (SELECT COUNT(*) FROM favorites f WHERE f.listing_id=l.id) AS likes,
  (SELECT COUNT(*) FROM favorites f WHERE f.listing_id=l.id AND f.user_id=?) AS liked
FROM listings l JOIN users u ON u.id=l.seller_id
"""


def seller_rating(user_id):
    row = db().execute("SELECT AVG(rating) a, COUNT(*) n FROM reviews WHERE seller_id=?",
                       (user_id,)).fetchone()
    return {"avg": round(row["a"], 2) if row["a"] else None, "count": row["n"]}


def rows(sql, args=()):
    return [dict(r) for r in db().execute(sql, args).fetchall()]


# ---------------------------------------------------------------- AI helper
def ai_models():
    raw = os.environ.get(
        "DRIFTRACK_AI_MODELS",
        "deepseek/deepseek-chat,meta-llama/llama-3.3-70b-instruct:free,openrouter/auto")
    return [m.strip() for m in raw.split(",") if m.strip()]


def local_description(d):
    brand = (d.get("brand") + " ") if d.get("brand") else ""
    size = f" Size {d['size']}." if d.get("size") else ""
    tone = {"New with tags": "Brand new, tags still on - never worn.",
            "Like new": "Worn once or twice, looks fresh out of the bag.",
            "Good": "Gently loved with plenty of life left.",
            "Fair": "Well loved, priced to move - shows some wear."}.get(d.get("condition"), "")
    return (f"{brand}{d.get('title', 'Item')}.{size} {tone} "
            "Ships fast from a smoke-free home. Bundle with my other pieces for a better price - "
            "offers welcome!").strip()


def ai_describe(d):
    """Try each OpenRouter model in order; switch when one is out of credit/limited/down."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        return {"text": local_description(d), "model": "local-template", "tried": []}
    prompt = ("Write a friendly 2-3 sentence marketplace listing description. No emojis, no "
              "hashtags, no invented facts. Item: " + json.dumps(
                  {k: d.get(k, "") for k in ("title", "brand", "category", "size", "condition")}))
    tried = []
    for model in ai_models():
        body = json.dumps({"model": model, "max_tokens": 200,
                           "messages": [{"role": "user", "content": prompt}]}).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=body,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                     "X-Title": "DriftRack"})
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                out = json.loads(resp.read())
            text = (out["choices"][0]["message"]["content"] or "").strip()
            if text:
                return {"text": text[:1200], "model": model, "tried": tried}
            tried.append({"model": model, "error": "empty reply"})
        except urllib.error.HTTPError as exc:  # 402 no credit, 429 limit, 5xx down -> next
            tried.append({"model": model, "error": f"HTTP {exc.code}"})
        except Exception as exc:  # network, timeout, bad payload -> next model
            tried.append({"model": model, "error": type(exc).__name__})
    return {"text": local_description(d), "model": "local-template", "tried": tried}


# ---------------------------------------------------------------- handlers
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")


def clean_email(value):
    email = clean(value, 254).lower()
    need(not email or EMAIL_RE.match(email), "That email address doesn't look right")
    return email


def check_password(password):
    need(6 <= len(password) <= 200, "Password needs 6 to 200 characters")
    return password


def h_register(ctx):
    rate_hit("register", ctx.ip)
    username = clean(ctx.body.get("username"), 24)
    password = check_password(str(ctx.body.get("password") or ""))
    email = clean_email(ctx.body.get("email"))
    need(re.fullmatch(r"[A-Za-z0-9_]{3,24}", username), "Username: 3-24 letters, numbers or _")
    with _write_lock:
        need(not db().execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone(),
             "That username is taken", 409)
        owner = 0 if db().execute("SELECT 1 FROM users WHERE is_owner=1").fetchone() else 1
        uid = create_user(username, password, is_owner=owner)
        db().execute("UPDATE users SET email=? WHERE id=?", (email, uid))
        db().commit()
    ctx.login(uid)
    return h_me(ctx)


def h_login(ctx):
    username = clean(ctx.body.get("username"), 24)
    key = ctx.ip + "|" + username.lower()
    rate_hit("login", key, record=False)
    row = db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    ok = row and hmac.compare_digest(row["pw"], hash_pw(str(ctx.body.get("password") or "")[:200],
                                                        row["salt"]))
    if not ok:
        rate_hit("login", key)
        raise ApiError(401, "Wrong username or password")
    need(not row["banned"], "This account is suspended. Contact the marketplace owner.", 403)
    rate_clear("login", key)
    ctx.login(row["id"])
    return h_me(ctx)


def h_logout(ctx):
    if ctx.token:
        db().execute("DELETE FROM sessions WHERE token=?", (ctx.token,))
        db().commit()
    ctx.set_cookie = "dr_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
    return {"ok": True}


def h_me(ctx):
    if not ctx.user:
        return {"user": None}
    u = ctx.user
    return {"user": {"id": u["id"], "username": u["username"], "balance": round(u["balance"], 2),
                     "is_owner": bool(u["is_owner"]), "bio": u["bio"], "city": u["city"],
                     "email": u["email"]}}


def h_meta(ctx):
    return {"categories": CATEGORIES, "conditions": CONDITIONS,
            "fee": {"pct": FEE_PCT, "flat": FEE_FLAT},
            "ai": bool(os.environ.get("OPENROUTER_API_KEY")),
            "payments": "stripe" if payments.enabled() else "simulated",
            "email": mailer.enabled()}


def h_health(ctx):
    db().execute("SELECT 1").fetchone()
    return {"ok": True, "time": int(time.time())}


def base_url(ctx):
    return PUBLIC_URL or "http://" + ctx.host


def reset_link(ctx, uid):
    token = secrets.token_urlsafe(32)
    db().execute("INSERT INTO resets(token_hash,user_id,created) VALUES(?,?,?)",
                 (hashlib.sha256(token.encode()).hexdigest(), uid, time.time()))
    db().commit()
    return f"{base_url(ctx)}/#/reset/{token}"


def h_forgot(ctx):
    rate_hit("forgot", ctx.ip)
    row = db().execute("SELECT id, email, banned FROM users WHERE username=?",
                       (clean(ctx.body.get("username"), 24),)).fetchone()
    # Emails only go to PUBLIC_URL links so a forged Host header can't redirect them.
    if row and row["email"] and not row["banned"] and mailer.enabled() and PUBLIC_URL:
        mailer.send(row["email"], "Reset your DriftRack password",
                    "Someone asked to reset your DriftRack password.\n\n"
                    f"Open this link within 1 hour:\n{reset_link(ctx, row['id'])}\n\n"
                    "If it wasn't you, ignore this email.")
    return {"ok": True, "email": mailer.enabled() and bool(PUBLIC_URL)}


def h_reset(ctx):
    token = str(ctx.body.get("token") or "")
    password = check_password(str(ctx.body.get("password") or ""))
    with _write_lock:
        row = db().execute("SELECT * FROM resets WHERE token_hash=?",
                           (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        need(row and not row["used"] and row["created"] > time.time() - 3600,
             "This reset link is invalid or has expired")
        salt = secrets.token_hex(16)
        db().execute("UPDATE users SET pw=?, salt=? WHERE id=?",
                     (hash_pw(password, salt), salt, row["user_id"]))
        db().execute("UPDATE resets SET used=1 WHERE user_id=?", (row["user_id"],))
        db().execute("DELETE FROM sessions WHERE user_id=?", (row["user_id"],))
        db().commit()
    return {"ok": True}


def h_change_password(ctx):
    ctx.auth()
    old = str(ctx.body.get("old") or "")[:200]
    need(hmac.compare_digest(ctx.user["pw"], hash_pw(old, ctx.user["salt"])),
         "Current password is wrong", 403)
    password = check_password(str(ctx.body.get("new") or ""))
    salt = secrets.token_hex(16)
    db().execute("UPDATE users SET pw=?, salt=? WHERE id=?", (hash_pw(password, salt), salt, ctx.uid))
    db().execute("DELETE FROM sessions WHERE user_id=? AND token!=?", (ctx.uid, ctx.token))
    db().commit()
    return {"ok": True}


def h_listings(ctx):
    q = ctx.query
    release_expired()
    status = q.get("status", "active")
    where, args = ["l.status=?"], [status if status in ("active", "sold") else "active"]
    if q.get("q"):
        where.append("(l.title LIKE ? OR l.brand LIKE ? OR l.description LIKE ?)")
        args += ["%" + q["q"][:60] + "%"] * 3
    for field in ("category", "condition"):
        if q.get(field):
            where.append(f"l.{field}=?")
            args.append(q[field])
    if q.get("seller"):
        where.append("u.username=?")
        args.append(q["seller"])
    for key, op in (("min", ">="), ("max", "<=")):
        if q.get(key):
            try:
                args.append(float(q[key]))
                where.append(f"l.price{op}?")
            except ValueError:
                pass
    order = {"new": "l.created DESC", "low": "l.price ASC", "high": "l.price DESC",
             "hot": "likes DESC, l.views DESC"}.get(q.get("sort", "new"), "l.created DESC")
    sql = LISTING_SQL + " WHERE " + " AND ".join(where) + f" ORDER BY {order} LIMIT 120"
    return {"listings": rows(sql, [ctx.uid] + args)}


def get_listing(ctx, lid):
    row = db().execute(LISTING_SQL + " WHERE l.id=?", (ctx.uid, lid)).fetchone()
    need(row, "Listing not found", 404)
    return dict(row)


def h_listing(ctx, lid):
    release_expired()
    item = get_listing(ctx, lid)
    if item["status"] in ("hidden", "removed"):
        need(ctx.uid == item["seller_id"] or (ctx.user and ctx.user["is_owner"]),
             "Listing not found", 404)
    if ctx.uid != item["seller_id"]:
        db().execute("UPDATE listings SET views=views+1 WHERE id=?", (lid,))
        db().commit()
    item["seller_rating"] = seller_rating(item["seller_id"])
    item["my_offer"] = None
    if ctx.uid:
        offer = db().execute("SELECT * FROM offers WHERE listing_id=? AND buyer_id=? "
                             "ORDER BY id DESC LIMIT 1", (lid, ctx.uid)).fetchone()
        item["my_offer"] = dict(offer) if offer else None
    item["more"] = rows(LISTING_SQL + " WHERE l.seller_id=? AND l.id!=? AND l.status='active' "
                        "ORDER BY l.created DESC LIMIT 4", (ctx.uid, item["seller_id"], lid))
    return {"listing": item}


def listing_fields(body, partial=False):
    out = {}
    if not partial or "title" in body:
        out["title"] = clean(body.get("title"), 80)
        need(len(out["title"]) >= 3, "Title needs at least 3 characters")
    if not partial or "price" in body:
        out["price"] = to_price(body.get("price"))
    if not partial or "category" in body:
        out["category"] = body.get("category")
        need(out["category"] in CATEGORIES, "Pick a category")
    if not partial or "condition" in body:
        out["condition"] = body.get("condition")
        need(out["condition"] in CONDITIONS, "Pick a condition")
    for key, limit in (("description", 1500), ("size", 20), ("brand", 40)):
        if not partial or key in body:
            out[key] = clean(body.get(key), limit)
    return out


def h_create_listing(ctx):
    ctx.auth()
    f = listing_fields(ctx.body)
    image = save_image(ctx.body.get("image"))
    cur = db().execute(
        "INSERT INTO listings(seller_id,title,description,price,category,size,brand,condition,"
        "image,created) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (ctx.uid, f["title"], f["description"], f["price"], f["category"], f["size"], f["brand"],
         f["condition"], image, time.time()))
    db().commit()
    return {"id": cur.lastrowid}


def h_update_listing(ctx, lid):
    ctx.auth()
    item = get_listing(ctx, lid)
    need(item["seller_id"] == ctx.uid, "Not your listing", 403)
    need(item["status"] not in ("sold", "reserved"), "Sold or reserved listings cannot be changed")
    need(item["status"] != "removed", "This listing was removed by the marketplace owner")
    f = listing_fields(ctx.body, partial=True)
    if ctx.body.get("status") in ("active", "hidden"):
        f["status"] = ctx.body["status"]
    if ctx.body.get("image"):
        f["image"] = save_image(ctx.body["image"])
    if f:
        sets = ",".join(f"{k}=?" for k in f)
        db().execute(f"UPDATE listings SET {sets} WHERE id=?", list(f.values()) + [lid])
        db().commit()
    return {"ok": True}


def h_delete_listing(ctx, lid):
    ctx.auth()
    item = get_listing(ctx, lid)
    need(item["seller_id"] == ctx.uid, "Not your listing", 403)
    need(item["status"] not in ("sold", "reserved"), "Sold listings are kept for order history")
    for table in ("favorites", "offers", "messages"):
        db().execute(f"DELETE FROM {table} WHERE listing_id=?", (lid,))
    db().execute("DELETE FROM listings WHERE id=?", (lid,))
    db().commit()
    return {"ok": True}


def h_favorite(ctx, lid):
    ctx.auth()
    get_listing(ctx, lid)
    hit = db().execute("DELETE FROM favorites WHERE user_id=? AND listing_id=?", (ctx.uid, lid))
    if hit.rowcount == 0:
        db().execute("INSERT INTO favorites VALUES(?,?,?)", (ctx.uid, lid, time.time()))
    db().commit()
    return {"liked": hit.rowcount == 0}


def h_favorites(ctx):
    ctx.auth()
    return {"listings": rows(LISTING_SQL + " JOIN favorites f ON f.listing_id=l.id AND "
                             "f.user_id=? ORDER BY f.created DESC", (ctx.uid, ctx.uid))}


def h_offer(ctx, lid):
    ctx.auth()
    item = get_listing(ctx, lid)
    need(item["status"] == "active", "This item is no longer available")
    need(item["seller_id"] != ctx.uid, "You cannot make an offer on your own item")
    amount = to_price(ctx.body.get("amount"))
    need(amount < item["price"], "Offer must be below the asking price")
    need(amount >= item["price"] * 0.4, "Offer is too low (min 40% of price)")
    db().execute("UPDATE offers SET status='replaced' WHERE listing_id=? AND buyer_id=? AND "
                 "status='pending'", (lid, ctx.uid))
    db().execute("INSERT INTO offers(listing_id,buyer_id,amount,created) VALUES(?,?,?,?)",
                 (lid, ctx.uid, amount, time.time()))
    db().commit()
    return {"ok": True}


def h_offers(ctx):
    ctx.auth()
    base = ("SELECT o.*, l.title, l.price, l.image, l.status AS listing_status, "
            "b.username AS buyer, s.username AS seller FROM offers o "
            "JOIN listings l ON l.id=o.listing_id JOIN users b ON b.id=o.buyer_id "
            "JOIN users s ON s.id=l.seller_id WHERE o.status!='replaced' AND ")
    return {"incoming": rows(base + "l.seller_id=? ORDER BY o.id DESC LIMIT 60", (ctx.uid,)),
            "outgoing": rows(base + "o.buyer_id=? ORDER BY o.id DESC LIMIT 60", (ctx.uid,))}


def h_offer_action(ctx, oid):
    ctx.auth()
    offer = db().execute("SELECT o.*, l.seller_id FROM offers o JOIN listings l "
                         "ON l.id=o.listing_id WHERE o.id=?", (oid,)).fetchone()
    need(offer, "Offer not found", 404)
    need(offer["seller_id"] == ctx.uid, "Only the seller can answer an offer", 403)
    need(offer["status"] == "pending", "Offer was already answered")
    action = ctx.body.get("action")
    need(action in ("accept", "decline"), "Action must be accept or decline")
    db().execute("UPDATE offers SET status=? WHERE id=?",
                 ("accepted" if action == "accept" else "declined", oid))
    db().commit()
    return {"ok": True}


_last_release = [0.0]


def release_expired(force=False):
    """Put listings back on the rack when a Stripe checkout was abandoned (max once a minute)."""
    now = time.time()
    if not force and now - _last_release[0] < 60:
        return
    _last_release[0] = now
    stale = db().execute("SELECT * FROM orders WHERE status='awaiting_payment' AND created<?",
                         (time.time() - PAY_WINDOW,)).fetchall()
    for order in stale:
        try:
            paid = payments.is_paid(order["stripe_session"]) if order["stripe_session"] else False
        except payments.PaymentError:
            continue  # Stripe unreachable: decide on a later request
        finish_payment(order, paid)


def finish_payment(order, paid):
    with _write_lock:
        cur = db().execute("UPDATE orders SET status=? WHERE id=? AND status='awaiting_payment'",
                           ("paid" if paid else "expired", order["id"]))
        if cur.rowcount:
            db().execute("UPDATE listings SET status=? WHERE id=? AND status='reserved'",
                         ("sold" if paid else "active", order["listing_id"]))
            if paid:
                db().execute("UPDATE offers SET status='closed' WHERE listing_id=? AND "
                             "status='pending'", (order["listing_id"],))
        db().commit()


def h_buy(ctx, lid):
    ctx.auth()
    release_expired()
    with _write_lock:
        item = get_listing(ctx, lid)
        need(item["status"] == "active", "Sorry - this item was just sold", 409)
        need(item["seller_id"] != ctx.uid, "You cannot buy your own item")
        deal = db().execute("SELECT amount FROM offers WHERE listing_id=? AND buyer_id=? AND "
                            "status='accepted' ORDER BY id DESC", (lid, ctx.uid)).fetchone()
        price = deal["amount"] if deal else item["price"]
        fee = round(price * FEE_PCT + FEE_FLAT, 2)
        stripe = payments.enabled()
        cur = db().execute("INSERT INTO orders(listing_id,buyer_id,seller_id,price,fee,status,"
                           "created) VALUES(?,?,?,?,?,?,?)",
                           (lid, ctx.uid, item["seller_id"], price, fee,
                            "awaiting_payment" if stripe else "paid", time.time()))
        oid = cur.lastrowid
        db().execute("UPDATE listings SET status=? WHERE id=?",
                     ("reserved" if stripe else "sold", lid))
        if not stripe:
            db().execute("UPDATE offers SET status='closed' WHERE listing_id=? AND "
                         "status='pending'", (lid,))
        db().commit()
    out = {"order_id": oid, "price": price, "fee": fee, "total": round(price + fee, 2)}
    if stripe:
        base = base_url(ctx)
        try:
            sid, url = payments.create_checkout(oid, item["title"], price, fee,
                                                f"{base}/#/paid/{oid}", f"{base}/#/cancel/{oid}")
        except payments.PaymentError as exc:
            finish_payment({"id": oid, "listing_id": lid}, False)
            raise ApiError(502, "Payment could not start: " + str(exc))
        db().execute("UPDATE orders SET stripe_session=? WHERE id=?", (sid, oid))
        db().commit()
        out["checkout_url"] = url
    return out


def h_pay_status(ctx, oid, action):
    ctx.auth()
    order = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    need(order and order["buyer_id"] == ctx.uid, "Order not found", 404)
    if order["status"] == "awaiting_payment":
        if action == "cancel":
            finish_payment(order, False)
        else:
            try:
                paid = payments.is_paid(order["stripe_session"])
            except payments.PaymentError as exc:
                raise ApiError(502, "Could not reach the payment provider: " + str(exc))
            if paid:
                finish_payment(order, True)
    status = db().execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()[0]
    return {"status": status, "listing_id": order["listing_id"]}


def h_orders(ctx):
    ctx.auth()
    base = ("SELECT o.*, l.title, l.image, b.username AS buyer, s.username AS seller, "
            "(SELECT rating FROM reviews r WHERE r.order_id=o.id) AS rating FROM orders o "
            "JOIN listings l ON l.id=o.listing_id JOIN users b ON b.id=o.buyer_id "
            "JOIN users s ON s.id=o.seller_id WHERE ")
    return {"bought": rows(base + "o.buyer_id=? ORDER BY o.id DESC", (ctx.uid,)),
            "sold": rows(base + "o.seller_id=? AND o." + VALID_ORDER + " ORDER BY o.id DESC",
                         (ctx.uid,))}


def h_order_action(ctx, oid, action):
    ctx.auth()
    with _write_lock:
        order = db().execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        need(order, "Order not found", 404)
        if action == "ship":
            need(order["seller_id"] == ctx.uid, "Only the seller can ship", 403)
            need(order["status"] == "paid", "Order is not waiting to ship")
            db().execute("UPDATE orders SET status='shipped' WHERE id=?", (oid,))
        elif action == "received":
            need(order["buyer_id"] == ctx.uid, "Only the buyer can confirm", 403)
            need(order["status"] == "shipped", "Order has not shipped yet")
            db().execute("UPDATE orders SET status='complete' WHERE id=?", (oid,))
            db().execute("UPDATE users SET balance=balance+? WHERE id=?",
                         (order["price"], order["seller_id"]))
        elif action == "review":
            need(order["buyer_id"] == ctx.uid, "Only the buyer can review", 403)
            need(order["status"] == "complete", "Confirm delivery before reviewing")
            try:
                rating = int(ctx.body.get("rating"))
            except (TypeError, ValueError):
                raise ApiError(400, "Rating must be 1-5")
            need(1 <= rating <= 5, "Rating must be 1-5")
            need(not db().execute("SELECT 1 FROM reviews WHERE order_id=?", (oid,)).fetchone(),
                 "You already reviewed this order")
            db().execute("INSERT INTO reviews(order_id,seller_id,buyer_id,rating,text,created) "
                         "VALUES(?,?,?,?,?,?)", (oid, order["seller_id"], ctx.uid, rating,
                                                 clean(ctx.body.get("text"), 500), time.time()))
        else:
            raise ApiError(404, "Unknown action")
        db().commit()
    return {"ok": True}


def h_threads(ctx):
    ctx.auth()
    sql = ("SELECT m.listing_id, l.title, l.image, u.username AS other, u.id AS other_id, "
           "m.body AS last, m.created FROM messages m JOIN listings l ON l.id=m.listing_id "
           "JOIN users u ON u.id=CASE WHEN m.from_id=? THEN m.to_id ELSE m.from_id END "
           "WHERE m.id IN (SELECT MAX(id) FROM messages WHERE from_id=? OR to_id=? GROUP BY "
           "listing_id, MIN(from_id,to_id), MAX(from_id,to_id)) ORDER BY m.created DESC")
    return {"threads": rows(sql, (ctx.uid, ctx.uid, ctx.uid))}


def h_messages(ctx):
    ctx.auth()
    try:
        lid, other = int(ctx.query.get("listing", 0)), int(ctx.query.get("with", 0))
    except ValueError:
        raise ApiError(400, "Bad thread")
    sql = ("SELECT m.*, u.username AS sender FROM messages m JOIN users u ON u.id=m.from_id "
           "WHERE m.listing_id=? AND ((m.from_id=? AND m.to_id=?) OR (m.from_id=? AND m.to_id=?))"
           " ORDER BY m.id")
    return {"messages": rows(sql, (lid, ctx.uid, other, other, ctx.uid))}


def h_send(ctx):
    ctx.auth()
    body = clean(ctx.body.get("body"), 1000)
    need(body, "Message is empty")
    try:
        lid, to = int(ctx.body.get("listing_id")), int(ctx.body.get("to"))
    except (TypeError, ValueError):
        raise ApiError(400, "Bad recipient")
    item = get_listing(ctx, lid)
    need(to != ctx.uid, "You cannot message yourself")
    need(db().execute("SELECT 1 FROM users WHERE id=?", (to,)).fetchone(), "User not found", 404)
    need(ctx.uid == item["seller_id"] or to == item["seller_id"],
         "Messages go between the buyer and the seller")
    db().execute("INSERT INTO messages(listing_id,from_id,to_id,body,created) VALUES(?,?,?,?,?)",
                 (lid, ctx.uid, to, body, time.time()))
    db().commit()
    return {"ok": True}


def h_profile(ctx, username):
    u = db().execute("SELECT id,username,bio,city,created FROM users WHERE username=?",
                     (username,)).fetchone()
    need(u, "User not found", 404)
    out = dict(u)
    out["rating"] = seller_rating(u["id"])
    out["sold"] = db().execute("SELECT COUNT(*) FROM orders WHERE seller_id=? AND " + VALID_ORDER,
                               (u["id"],)).fetchone()[0]
    out["reviews"] = rows("SELECT r.rating, r.text, r.created, b.username AS buyer FROM reviews r "
                          "JOIN users b ON b.id=r.buyer_id WHERE r.seller_id=? ORDER BY r.id DESC "
                          "LIMIT 20", (u["id"],))
    out["listings"] = rows(LISTING_SQL + " WHERE l.seller_id=? AND l.status='active' "
                           "ORDER BY l.created DESC", (ctx.uid, u["id"]))
    return {"profile": out}


def h_update_profile(ctx):
    ctx.auth()
    email = clean_email(ctx.body.get("email")) if "email" in ctx.body else ctx.user["email"]
    db().execute("UPDATE users SET bio=?, city=?, email=? WHERE id=?",
                 (clean(ctx.body.get("bio"), 300), clean(ctx.body.get("city"), 40), email,
                  ctx.uid))
    db().commit()
    return {"ok": True}


def h_dashboard(ctx):
    ctx.auth()
    uid, conn, now = ctx.uid, db(), time.time()
    one = lambda sql, *a: conn.execute(sql, a).fetchone()[0] or 0  # noqa: E731
    days = []
    start = now - (now % 86400) - 13 * 86400
    for i in range(14):
        lo = start + i * 86400
        days.append({"day": time.strftime("%b %d", time.gmtime(lo)),
                     "total": round(one("SELECT SUM(price) FROM orders WHERE seller_id=? AND "
                                        "created>=? AND created<? AND " + VALID_ORDER, uid, lo, lo + 86400), 2)})
    activity = rows(
        "SELECT * FROM (SELECT 'sale' AS kind, l.title, b.username AS who, o.price AS amount, "
        "o.created FROM orders o JOIN listings l ON l.id=o.listing_id JOIN users b ON "
        "b.id=o.buyer_id WHERE o.seller_id=? AND o." + VALID_ORDER + " UNION ALL SELECT 'offer', l.title, b.username, "
        "o.amount, o.created FROM offers o JOIN listings l ON l.id=o.listing_id JOIN users b ON "
        "b.id=o.buyer_id WHERE l.seller_id=? UNION ALL SELECT 'like', l.title, u.username, NULL, "
        "f.created FROM favorites f JOIN listings l ON l.id=f.listing_id JOIN users u ON "
        "u.id=f.user_id WHERE l.seller_id=?) ORDER BY created DESC LIMIT 12", (uid, uid, uid))
    return {
        "stats": {
            "revenue": round(one("SELECT SUM(price) FROM orders WHERE seller_id=? AND " + VALID_ORDER,
                                 uid), 2),
            "balance": round(ctx.user["balance"], 2),
            "pending": round(one("SELECT SUM(price) FROM orders WHERE seller_id=? AND "
                                 "status IN ('paid','shipped')", uid), 2),
            "sold": one("SELECT COUNT(*) FROM orders WHERE seller_id=? AND " + VALID_ORDER, uid),
            "active": one("SELECT COUNT(*) FROM listings WHERE seller_id=? AND status='active'",
                          uid),
            "views": one("SELECT SUM(views) FROM listings WHERE seller_id=?", uid),
            "likes": one("SELECT COUNT(*) FROM favorites f JOIN listings l ON l.id=f.listing_id "
                         "WHERE l.seller_id=?", uid),
            "offers": one("SELECT COUNT(*) FROM offers o JOIN listings l ON l.id=o.listing_id "
                          "WHERE l.seller_id=? AND o.status='pending'", uid),
            "to_ship": one("SELECT COUNT(*) FROM orders WHERE seller_id=? AND status='paid'", uid),
        },
        "rating": seller_rating(uid), "days": days, "activity": activity,
        "listings": rows(LISTING_SQL + " WHERE l.seller_id=? ORDER BY (l.status='active') DESC, "
                         "l.created DESC LIMIT 60", (uid, uid)),
    }


def h_ads(ctx):
    return {"ads": rows("SELECT id, text FROM ads ORDER BY id")}


def h_add_ad(ctx):
    ctx.auth()
    need(ctx.user["is_owner"], "Only the marketplace owner can edit sale ads", 403)
    text = clean(ctx.body.get("text"), 90)
    need(len(text) >= 3, "Ad text is too short")
    need(db().execute("SELECT COUNT(*) FROM ads").fetchone()[0] < 20, "20 ads max")
    db().execute("INSERT INTO ads(text,created) VALUES(?,?)", (text, time.time()))
    db().commit()
    return h_ads(ctx)


def h_del_ad(ctx, aid):
    ctx.auth()
    need(ctx.user["is_owner"], "Only the marketplace owner can edit sale ads", 403)
    db().execute("DELETE FROM ads WHERE id=?", (aid,))
    db().commit()
    return h_ads(ctx)


def h_report(ctx, lid):
    ctx.auth()
    rate_hit("report", ctx.ip)
    item = get_listing(ctx, lid)
    need(item["seller_id"] != ctx.uid, "You cannot report your own listing")
    reason = clean(ctx.body.get("reason"), 300)
    need(len(reason) >= 3, "Tell us briefly what's wrong")
    need(not db().execute("SELECT 1 FROM reports WHERE listing_id=? AND reporter_id=? AND "
                          "status='open'", (lid, ctx.uid)).fetchone(),
         "You already reported this listing")
    db().execute("INSERT INTO reports(listing_id,reporter_id,reason,created) VALUES(?,?,?,?)",
                 (lid, ctx.uid, reason, time.time()))
    db().commit()
    return {"ok": True}


def owner_only(ctx):
    ctx.auth()
    need(ctx.user["is_owner"], "Only the marketplace owner can do that", 403)


def h_admin(ctx):
    owner_only(ctx)
    one = lambda sql, *a: db().execute(sql, a).fetchone()[0] or 0  # noqa: E731
    return {
        "stats": {
            "users": one("SELECT COUNT(*) FROM users"),
            "banned": one("SELECT COUNT(*) FROM users WHERE banned=1"),
            "active": one("SELECT COUNT(*) FROM listings WHERE status='active'"),
            "orders": one("SELECT COUNT(*) FROM orders WHERE " + VALID_ORDER),
            "gmv": round(one("SELECT SUM(price) FROM orders WHERE " + VALID_ORDER), 2),
            "fees": round(one("SELECT SUM(fee) FROM orders WHERE " + VALID_ORDER), 2),
            "open_reports": one("SELECT COUNT(*) FROM reports WHERE status='open'"),
        },
        "reports": rows(
            "SELECT r.id, r.reason, r.created, r.listing_id, l.title, l.image, l.status AS "
            "listing_status, s.username AS seller, s.id AS seller_id, u.username AS reporter "
            "FROM reports r JOIN listings l ON l.id=r.listing_id JOIN users s ON "
            "s.id=l.seller_id JOIN users u ON u.id=r.reporter_id WHERE r.status='open' "
            "ORDER BY r.id DESC LIMIT 100"),
        "users": rows(
            "SELECT u.id, u.username, u.email, u.city, u.banned, u.is_owner, u.is_demo, "
            "u.created, (SELECT COUNT(*) FROM listings l WHERE l.seller_id=u.id AND "
            "l.status='active') AS active, (SELECT COUNT(*) FROM reports r JOIN listings l ON "
            "l.id=r.listing_id WHERE l.seller_id=u.id) AS reports FROM users u "
            "ORDER BY u.id DESC LIMIT 200"),
        "payments": "stripe" if payments.enabled() else "simulated",
        "email": mailer.enabled(),
    }


def h_admin_report(ctx, rid):
    owner_only(ctx)
    report = db().execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()
    need(report, "Report not found", 404)
    action = ctx.body.get("action")
    need(action in ("dismiss", "remove"), "Action must be dismiss or remove")
    if action == "remove":
        db().execute("UPDATE listings SET status='removed' WHERE id=? AND status IN "
                     "('active','hidden')", (report["listing_id"],))
        db().execute("UPDATE reports SET status='actioned' WHERE listing_id=? AND status='open'",
                     (report["listing_id"],))
    else:
        db().execute("UPDATE reports SET status='dismissed' WHERE id=?", (rid,))
    db().commit()
    return {"ok": True}


def h_admin_user(ctx, uid):
    owner_only(ctx)
    user = db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    need(user, "User not found", 404)
    action = ctx.body.get("action")
    need(action in ("ban", "unban", "reset_link"), "Unknown action")
    if action == "reset_link":
        return {"link": reset_link(ctx, uid)}
    need(not user["is_owner"], "The owner account cannot be suspended")
    banned = 1 if action == "ban" else 0
    db().execute("UPDATE users SET banned=? WHERE id=?", (banned, uid))
    if banned:
        db().execute("DELETE FROM sessions WHERE user_id=?", (uid,))
        db().execute("UPDATE listings SET status='hidden' WHERE seller_id=? AND status='active'",
                     (uid,))
    db().commit()
    return {"ok": True}


def h_ai(ctx):
    ctx.auth()
    need(clean(ctx.body.get("title"), 80), "Add a title first")
    return ai_describe({k: clean(ctx.body.get(k), 80)
                        for k in ("title", "brand", "category", "size", "condition")})


ROUTES = [
    ("POST", r"/api/register", h_register), ("POST", r"/api/login", h_login),
    ("POST", r"/api/logout", h_logout), ("GET", r"/api/me", h_me),
    ("GET", r"/api/meta", h_meta), ("POST", r"/api/profile", h_update_profile),
    ("GET", r"/api/listings", h_listings), ("POST", r"/api/listings", h_create_listing),
    ("GET", r"/api/listings/(\d+)", h_listing), ("PATCH", r"/api/listings/(\d+)", h_update_listing),
    ("DELETE", r"/api/listings/(\d+)", h_delete_listing),
    ("POST", r"/api/listings/(\d+)/favorite", h_favorite),
    ("POST", r"/api/listings/(\d+)/offer", h_offer), ("POST", r"/api/listings/(\d+)/buy", h_buy),
    ("GET", r"/api/favorites", h_favorites), ("GET", r"/api/offers", h_offers),
    ("POST", r"/api/offers/(\d+)", h_offer_action), ("GET", r"/api/orders", h_orders),
    ("POST", r"/api/orders/(\d+)/(ship|received|review)", h_order_action),
    ("GET", r"/api/threads", h_threads), ("GET", r"/api/messages", h_messages),
    ("POST", r"/api/messages", h_send), ("GET", r"/api/users/([A-Za-z0-9_]{3,24})", h_profile),
    ("GET", r"/api/dashboard", h_dashboard), ("GET", r"/api/ads", h_ads),
    ("POST", r"/api/ads", h_add_ad), ("DELETE", r"/api/ads/(\d+)", h_del_ad),
    ("POST", r"/api/ai/describe", h_ai), ("GET", r"/api/health", h_health),
    ("POST", r"/api/password/forgot", h_forgot), ("POST", r"/api/password/reset", h_reset),
    ("POST", r"/api/password/change", h_change_password),
    ("POST", r"/api/orders/(\d+)/(confirm|cancel)", h_pay_status),
    ("POST", r"/api/listings/(\d+)/report", h_report), ("GET", r"/api/admin", h_admin),
    ("POST", r"/api/admin/reports/(\d+)", h_admin_report),
    ("POST", r"/api/admin/users/(\d+)", h_admin_user),
]
ROUTES = [(m, re.compile("^" + p + "$"), fn) for m, p, fn in ROUTES]
MIME = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8", ".svg": "image/svg+xml",
        ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp",
        ".ico": "image/x-icon"}


class Ctx:
    def __init__(self, handler, query, body):
        self.query, self.body, self.set_cookie = query, body, None
        self.user, self.token = None, None
        self.host = handler.headers.get("Host", f"{HOST}:{PORT}")
        self.ip = handler.client_address[0]
        if TRUST_PROXY and handler.headers.get("X-Forwarded-For"):
            self.ip = handler.headers["X-Forwarded-For"].split(",")[0].strip()
        jar = cookies.SimpleCookie(handler.headers.get("Cookie", ""))
        if "dr_session" in jar:
            self.token = jar["dr_session"].value
            self.user = db().execute(
                "SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND "
                "s.created>? AND u.banned=0", (self.token, time.time() - 30 * 86400)).fetchone()
        self.uid = self.user["id"] if self.user else 0

    def auth(self):
        need(self.user, "Please log in first", 401)

    def login(self, uid):
        self.token = secrets.token_urlsafe(32)
        db().execute("INSERT INTO sessions VALUES(?,?,?)", (self.token, uid, time.time()))
        db().commit()
        self.user = db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        self.uid = uid
        self.set_cookie = (f"dr_session={self.token}; Path=/; Max-Age=2592000; HttpOnly; "
                           "SameSite=Lax" + ("; Secure" if SECURE_COOKIES else ""))


class Handler(BaseHTTPRequestHandler):
    server_version = "DriftRack/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if os.environ.get("DRIFTRACK_QUIET") != "1":
            sys.stderr.write("[driftrack] " + fmt % args + "\n")

    def send_bytes(self, status, payload, ctype, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CSP)
        if SECURE_COOKIES:
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def send_json(self, status, obj, cookie=None):
        extra = {"Cache-Control": "no-store"}
        if cookie:
            extra["Set-Cookie"] = cookie
        self.send_bytes(status, json.dumps(obj).encode(), "application/json", extra)

    def serve_file(self, base, rel):
        full = os.path.realpath(os.path.join(base, rel))
        if not full.startswith(os.path.realpath(base) + os.sep) or not os.path.isfile(full):
            return self.send_json(404, {"error": "Not found"})
        with open(full, "rb") as fh:
            data = fh.read()
        cache = "public, max-age=86400" if base == UPLOADS else "no-cache"
        self.send_bytes(200, data, MIME.get(os.path.splitext(full)[1], "application/octet-stream"),
                        {"Cache-Control": cache})

    def handle_any(self):
        url = urlparse(self.path)
        path = url.path
        if not path.startswith("/api/"):
            if self.command not in ("GET", "HEAD"):
                return self.send_json(405, {"error": "Method not allowed"})
            if path.startswith("/uploads/"):
                return self.serve_file(UPLOADS, path[len("/uploads/"):])
            return self.serve_file(STATIC, "index.html" if path == "/" else path.lstrip("/"))
        try:
            body = {}
            if self.command in ("POST", "PATCH"):
                # Same-origin check: blocks cross-site form posts riding the session cookie.
                origin = self.headers.get("Origin")
                if origin and urlparse(origin).netloc != self.headers.get("Host"):
                    raise ApiError(403, "Cross-site request blocked")
                length = int(self.headers.get("Content-Length") or 0)
                need(length <= MAX_BODY, "Request too large", 413)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw or b"{}")
                except ValueError:
                    raise ApiError(400, "Body must be JSON")
                need(isinstance(body, dict), "Body must be a JSON object")
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            ctx = Ctx(self, query, body)
            for method, pattern, fn in ROUTES:
                match = pattern.match(path)
                if match and method == self.command:
                    args = [int(g) if g.isdigit() else g for g in match.groups()]
                    return self.send_json(200, fn(ctx, *args), ctx.set_cookie)
            raise ApiError(404, "Unknown endpoint")
        except ApiError as exc:
            self.send_json(exc.status, {"error": exc.msg})
        except Exception as exc:  # keep the server alive, hide internals from the client
            sys.stderr.write(f"[driftrack] ERROR {self.command} {path}: {exc!r}\n")
            self.send_json(500, {"error": "Something went wrong on our side"})

    def finish(self):
        super().finish()
        conn = getattr(_local, "conn", None)  # one connection per request thread
        if conn is not None:
            conn.close()
            _local.conn = None

    do_GET = do_POST = do_PATCH = do_DELETE = do_HEAD = handle_any


def make_server(host=HOST, port=PORT):
    init_db()
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    if "--seed" in sys.argv:
        import seed
        seed.run()
    server = make_server()
    print(f"\n  DriftRack is live  ->  http://{HOST}:{PORT}"
          f"\n  Payments: {'Stripe' if payments.enabled() else 'simulated'}"
          f" | Email: {'on' if mailer.enabled() else 'off'}\n  Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  DriftRack stopped.")
