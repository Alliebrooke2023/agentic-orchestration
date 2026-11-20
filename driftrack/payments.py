# driftrack/payments.py
"""Stripe Checkout (hosted page). Off unless STRIPE_SECRET_KEY is set.

Uses a test key (sk_test_...) for the sandbox. Money lands in the platform's Stripe
account; seller payouts stay on the in-app wallet until Stripe Connect is added.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.stripe.com/v1/"


class PaymentError(Exception):
    pass


def enabled():
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def _call(method, path, params=None):
    data = urllib.parse.urlencode(params or {}).encode() if method == "POST" else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": "Bearer " + os.environ.get("STRIPE_SECRET_KEY", ""),
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read())["error"]["message"]
        except Exception:
            msg = f"HTTP {exc.code}"
        raise PaymentError(msg)
    except Exception as exc:
        raise PaymentError(type(exc).__name__)


def create_checkout(order_id, title, price, fee, success_url, cancel_url):
    """Return (session_id, hosted_url). Session expires in 31 minutes."""
    params = {
        "mode": "payment",
        "client_reference_id": str(order_id),
        "metadata[order_id]": str(order_id),
        "success_url": success_url,
        "cancel_url": cancel_url,
        "expires_at": str(int(time.time()) + 31 * 60),
    }
    for i, (name, amount) in enumerate(((title[:120], price), ("Buyer protection", fee))):
        params[f"line_items[{i}][quantity]"] = "1"
        params[f"line_items[{i}][price_data][currency]"] = os.environ.get("STRIPE_CURRENCY", "usd")
        params[f"line_items[{i}][price_data][unit_amount]"] = str(int(round(amount * 100)))
        params[f"line_items[{i}][price_data][product_data][name]"] = name
    out = _call("POST", "checkout/sessions", params)
    return out["id"], out["url"]


def is_paid(session_id):
    out = _call("GET", "checkout/sessions/" + urllib.parse.quote(session_id, safe=""))
    return out.get("payment_status") == "paid"
