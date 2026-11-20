# driftrack/tests/test_api.py
"""End-to-end API tests against a real server on a temp database.

Run:  python -m unittest discover -s tests -v     (from the driftrack folder)
"""
import base64
import http.cookiejar
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

TMP = tempfile.mkdtemp(prefix="driftrack_test_")
os.environ["DRIFTRACK_DATA"] = TMP
os.environ["DRIFTRACK_QUIET"] = "1"
os.environ.pop("OPENROUTER_API_KEY", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402
import seed  # noqa: E402

PNG = "data:image/png;base64," + base64.b64encode(
    b"\x89PNG\r\n\x1a\n" + b"\x00" * 64).decode()


class Client:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method, path, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json",
                                              **(headers or {})})
        try:
            with self.opener.open(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"{}")


class DriftRackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.make_server("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        seed.run()
        cls.seller, cls.buyer, cls.anon = Client(cls.base), Client(cls.base), Client(cls.base)
        s, out = cls.seller.call("POST", "/api/register", {"username": "owner1", "password": "secret1"})
        assert s == 200 and out["user"]["is_owner"], out
        s, out = cls.buyer.call("POST", "/api/register", {"username": "buyer1", "password": "secret1"})
        assert s == 200 and not out["user"]["is_owner"], out
        cls.buyer_id = out["user"]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def new_listing(self, price=40):
        s, out = self.seller.call("POST", "/api/listings", {
            "title": "Test jacket", "price": price, "category": "Men", "condition": "Good",
            "brand": "Acme", "size": "M", "description": "<script>alert(1)</script>",
            "image": PNG})
        self.assertEqual(s, 200, out)
        return out["id"]

    def test_static_and_traversal(self):
        with urllib.request.urlopen(self.base + "/") as r:
            self.assertIn(b"DriftRack", r.read())
        for bad in ("/../app.py", "/..%2fapp.py", "/uploads/../driftrack.db"):
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(self.base + bad)
            self.assertEqual(cm.exception.code, 404)

    def test_auth_rules(self):
        self.assertEqual(self.anon.call("POST", "/api/listings", {})[0], 401)
        self.assertEqual(self.anon.call("GET", "/api/dashboard")[0], 401)
        self.assertEqual(self.anon.call("POST", "/api/login",
                                        {"username": "owner1", "password": "nope"})[0], 401)
        self.assertEqual(self.anon.call("POST", "/api/register",
                                        {"username": "owner1", "password": "secret1"})[0], 409)
        self.assertEqual(self.anon.call("POST", "/api/register",
                                        {"username": "a b", "password": "secret1"})[0], 400)
        s, _ = self.seller.call("POST", "/api/profile", {"bio": "x"},
                                {"Origin": "http://evil.example"})
        self.assertEqual(s, 403)

    def test_browse_search_filter(self):
        s, out = self.anon.call("GET", "/api/listings")
        self.assertEqual(s, 200)
        self.assertGreaterEqual(len(out["listings"]), 24)
        _, out = self.anon.call("GET", "/api/listings?q=Levi&category=Women")
        self.assertTrue(out["listings"])
        self.assertTrue(all(x["category"] == "Women" for x in out["listings"]))
        _, out = self.anon.call("GET", "/api/listings?sort=low&max=20")
        prices = [x["price"] for x in out["listings"]]
        self.assertEqual(prices, sorted(prices))
        self.assertTrue(all(p <= 20 for p in prices))
        _, out = self.anon.call("GET", "/api/listings?q=%27%20OR%201=1--")
        self.assertEqual(out["listings"], [])

    def test_listing_validation_and_ownership(self):
        lid = self.new_listing()
        bad = {"title": "x", "price": 5, "category": "Men", "condition": "Good"}
        self.assertEqual(self.seller.call("POST", "/api/listings", bad)[0], 400)
        bad.update(title="Fine title", price=-3)
        self.assertEqual(self.seller.call("POST", "/api/listings", bad)[0], 400)
        bad.update(price=5, image="data:image/svg+xml;base64,PHN2Zz4=")
        self.assertEqual(self.seller.call("POST", "/api/listings", bad)[0], 400)
        bad.update(image="data:image/png;base64," + base64.b64encode(b"<html>").decode())
        self.assertEqual(self.seller.call("POST", "/api/listings", bad)[0], 400)
        self.assertEqual(self.buyer.call("PATCH", f"/api/listings/{lid}", {"price": 1})[0], 403)
        self.assertEqual(self.buyer.call("DELETE", f"/api/listings/{lid}")[0], 403)
        self.assertEqual(self.seller.call("PATCH", f"/api/listings/{lid}", {"price": 35})[0], 200)
        _, out = self.anon.call("GET", f"/api/listings/{lid}")
        self.assertEqual(out["listing"]["price"], 35)
        self.assertTrue(out["listing"]["image"].startswith("/uploads/"))
        self.assertEqual(self.seller.call("DELETE", f"/api/listings/{lid}")[0], 200)
        self.assertEqual(self.anon.call("GET", f"/api/listings/{lid}")[0], 404)

    def test_listing_update_only_writes_known_columns(self):
        full = {"title": "Coat", "price": 9, "category": "Men", "condition": "Good",
                "description": "", "size": "", "brand": ""}
        self.assertTrue(set(app.listing_fields(full)) <= set(app.EDITABLE_LISTING_COLUMNS))
        lid = self.new_listing(40)
        s, _ = self.seller.call("PATCH", f"/api/listings/{lid}",
                                {"price": 30, "views=999,seller_id": 1, "status=?--": "x"})
        self.assertEqual(s, 200)
        _, out = self.anon.call("GET", f"/api/listings/{lid}")
        self.assertEqual(out["listing"]["price"], 30)
        self.assertNotEqual(out["listing"]["views"], 999)
        self.assertEqual(self.seller.call("DELETE", f"/api/listings/{lid}")[0], 200)

    def test_full_sale_flow(self):
        lid = self.new_listing(40)
        self.assertEqual(self.seller.call("POST", f"/api/listings/{lid}/buy")[0], 400)
        s, out = self.buyer.call("POST", f"/api/listings/{lid}/favorite")
        self.assertTrue(out["liked"])
        self.assertEqual(len(self.buyer.call("GET", "/api/favorites")[1]["listings"]), 1)
        self.assertEqual(self.buyer.call("POST", f"/api/listings/{lid}/offer", {"amount": 5})[0], 400)
        self.assertEqual(self.buyer.call("POST", f"/api/listings/{lid}/offer", {"amount": 50})[0], 400)
        self.assertEqual(self.buyer.call("POST", f"/api/listings/{lid}/offer", {"amount": 30})[0], 200)
        _, offers = self.seller.call("GET", "/api/offers")
        oid = offers["incoming"][0]["id"]
        self.assertEqual(self.buyer.call("POST", f"/api/offers/{oid}", {"action": "accept"})[0], 403)
        self.assertEqual(self.seller.call("POST", f"/api/offers/{oid}", {"action": "accept"})[0], 200)
        s, order = self.buyer.call("POST", f"/api/listings/{lid}/buy")
        self.assertEqual((s, order["price"], order["fee"], order["total"]), (200, 30, 2.2, 32.2))
        self.assertEqual(self.buyer.call("POST", f"/api/listings/{lid}/buy")[0], 409)
        oid = order["order_id"]
        self.assertEqual(self.buyer.call("POST", f"/api/orders/{oid}/received")[0], 400)
        self.assertEqual(self.buyer.call("POST", f"/api/orders/{oid}/ship")[0], 403)
        self.assertEqual(self.seller.call("POST", f"/api/orders/{oid}/ship")[0], 200)
        self.assertEqual(self.buyer.call("POST", f"/api/orders/{oid}/received")[0], 200)
        self.assertEqual(self.buyer.call("POST", f"/api/orders/{oid}/review",
                                         {"rating": 9})[0], 400)
        self.assertEqual(self.buyer.call("POST", f"/api/orders/{oid}/review",
                                         {"rating": 5, "text": "Great"})[0], 200)
        self.assertEqual(self.buyer.call("POST", f"/api/orders/{oid}/review",
                                         {"rating": 5})[0], 400)
        _, dash = self.seller.call("GET", "/api/dashboard")
        self.assertEqual(dash["stats"]["revenue"], 30)
        self.assertEqual(dash["stats"]["balance"], 30)
        self.assertEqual(dash["stats"]["sold"], 1)
        self.assertEqual(dash["rating"], {"avg": 5.0, "count": 1})
        self.assertEqual(len(dash["days"]), 14)
        self.assertEqual(dash["days"][-1]["total"], 30)
        _, prof = self.anon.call("GET", "/api/users/owner1")
        self.assertEqual(prof["profile"]["reviews"][0]["text"], "Great")
        self.assertEqual(self.seller.call("DELETE", f"/api/listings/{lid}")[0], 400)

    def test_messages(self):
        lid = self.new_listing()
        _, me = self.seller.call("GET", "/api/me")
        sid = me["user"]["id"]
        self.assertEqual(self.buyer.call("POST", "/api/messages",
                                         {"listing_id": lid, "to": sid, "body": "Hi?"})[0], 200)
        self.assertEqual(self.seller.call("POST", "/api/messages", {
            "listing_id": lid, "to": self.buyer_id, "body": "Yes!"})[0], 200)
        _, th = self.seller.call("GET", "/api/threads")
        self.assertEqual((len(th["threads"]), th["threads"][0]["last"]), (1, "Yes!"))
        _, ms = self.buyer.call("GET", f"/api/messages?listing={lid}&with={sid}")
        self.assertEqual([m["body"] for m in ms["messages"]], ["Hi?", "Yes!"])
        _, ms = self.anon.call("GET", f"/api/messages?listing={lid}&with={sid}")
        self.assertNotIn("messages", ms)

    def test_ads_owner_only_and_ai_fallback(self):
        _, ads = self.anon.call("GET", "/api/ads")
        n = len(ads["ads"])
        self.assertGreaterEqual(n, 5)
        self.assertEqual(self.buyer.call("POST", "/api/ads", {"text": "Hack sale"})[0], 403)
        s, ads = self.seller.call("POST", "/api/ads", {"text": "Friday shoe sale"})
        self.assertEqual((s, len(ads["ads"])), (200, n + 1))
        aid = ads["ads"][-1]["id"]
        self.assertEqual(self.buyer.call("DELETE", f"/api/ads/{aid}")[0], 403)
        self.assertEqual(len(self.seller.call("DELETE", f"/api/ads/{aid}")[1]["ads"]), n)
        s, out = self.seller.call("POST", "/api/ai/describe",
                                  {"title": "Wool coat", "condition": "Like new"})
        self.assertEqual((s, out["model"]), (200, "local-template"))
        self.assertIn("Wool coat", out["text"])

    def test_ai_switches_models_when_one_runs_out(self):
        calls = []

        def fake_urlopen(req, timeout=0):
            model = json.loads(req.data)["model"]
            calls.append(model)
            if model == "model-a":
                raise urllib.error.HTTPError(req.full_url, 402, "Payment Required", {}, None)
            if model == "model-b":
                raise urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)

            class Resp:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def read(self):
                    return json.dumps({"choices": [{"message": {"content": "Nice coat."}}]}).encode()
            return Resp()

        real = app.urllib.request.urlopen
        os.environ.update(OPENROUTER_API_KEY="test", DRIFTRACK_AI_MODELS="model-a,model-b,model-c")
        app.urllib.request.urlopen = fake_urlopen
        try:
            out = app.ai_describe({"title": "Coat"})
        finally:
            app.urllib.request.urlopen = real
            os.environ.pop("OPENROUTER_API_KEY")
            os.environ.pop("DRIFTRACK_AI_MODELS")
        self.assertEqual(calls, ["model-a", "model-b", "model-c"])
        self.assertEqual((out["model"], out["text"]), ("model-c", "Nice coat."))
        self.assertEqual([t["error"] for t in out["tried"]], ["HTTP 402", "HTTP 429"])


if __name__ == "__main__":
    unittest.main()
