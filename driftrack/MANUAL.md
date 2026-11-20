# DriftRack Owner's Manual

## 1. Start it

```powershell
cd driftrack
python app.py --seed
```

Open http://127.0.0.1:8750. Stop with `Ctrl+C`.

- `--seed` loads 5 demo sellers and 24 listings. Leave it off for an empty shop.
- `.\start.ps1` gives a menu: install check, run with demo, run empty, run tests.
- The start-up line tells you what's switched on: `Payments: simulated | Email: off`.

## 2. Become the owner

The **first account created through the sign-up form** is the marketplace owner.
Demo accounts never count. Create yours first, before sharing the link.

The owner gets the **Admin** page and controls the scrolling sale ads.

## 3. The screens

| Screen | What you do there |
| --- | --- |
| Browse | Search, filter by category / condition / price, sort, save with the heart |
| Item | Buy now, make an offer, message the seller, report the listing |
| Sell | Photo, details, price. "Write it for me" drafts the description |
| Dashboard | Earnings, stats, 14-day sales chart, live activity, offers, your rack, sale ads |
| Orders | Mark shipped (seller), confirm delivery and review (buyer) |
| Inbox | Chats, grouped by item |
| Saved | Everything you hearted |
| Profile | Bio, city, email, change password, reviews, listings |
| Admin (owner) | Sales volume, fees earned, reports, members, suspend, reset links |
| Terms / Privacy | Footer links. Template text |

On a phone the menu moves to a tab bar at the bottom. The owner reaches Admin
from the **Admin** button on the Dashboard banner.

## 4. How a sale works

1. Seller lists an item. It shows as **active**.
2. Buyer taps **Buy now**, or sends an offer (40% of the price or more, below asking).
3. Seller accepts or declines offers on the Dashboard. An accepted offer becomes that buyer's price.
4. Buyer pays item price plus buyer protection: **5% + $0.70**.
5. Seller taps **Mark shipped** in Orders.
6. Buyer taps **I got it**. Only then is the money added to the seller's wallet.
7. Buyer can leave one 1-5 star review.

Order status: `paid` > `shipped` > `complete`.
With Stripe on, an order starts as `awaiting_payment` and the item shows **Reserved**.

## 5. Payments

**Off by default.** Every purchase is simulated, which is right for the sandbox.

**Turn on Stripe (test mode first):**

1. Make a free account at stripe.com. Stay in **Test mode**.
2. Developers > API keys > copy the **Secret key** (`sk_test_...`).
3. Start DriftRack with it:

```powershell
$env:STRIPE_SECRET_KEY = "sk_test_..."
python app.py
```

4. Buy something. You land on Stripe's checkout page. Test card: `4242 4242 4242 4242`,
   any future date, any CVC.
5. After paying you're sent back and the order shows **paid**.

How it behaves:

- While the buyer is on Stripe the item is **Reserved** so nobody else can buy it.
- Cancel on Stripe, or leave for 35 minutes, and the item goes back on the rack.
- Money lands in **your** Stripe account. Seller wallets are a ledger: you pay sellers
  out yourself for now. Automatic seller payouts need Stripe Connect (not built yet).
- Swap to a live key (`sk_live_...`) only when you're ready for real money.

## 6. Accounts and passwords

- **Email** is optional at sign-up and can be added on the Profile page.
- **Change password:** Profile page. Signs out your other devices.
- **Forgot password:**
  - Email on (section 8): the member gets a one-hour reset link.
  - Email off: Admin > Members > **Reset link**. Copy it and send it privately.
- A reset signs the member out everywhere.
- **Lockout:** 5 wrong passwords in 15 minutes locks that username from that
  connection for 15 minutes. Sign-ups and reset requests are rate limited too.

## 7. Keeping it clean (Admin)

- Members tap **Report this listing** on any item that isn't theirs.
- Admin > Reports: **Remove listing** takes it down for good, **Dismiss** keeps it.
- Admin > Members: **Suspend** signs the member out, blocks login, hides their
  listings. **Restore** lets them back in; they re-show listings themselves.
- The owner account can't be suspended.

## 8. Email (password reset)

Any SMTP service works (Gmail app password, Brevo, Mailgun, SendGrid...).

```powershell
$env:SMTP_HOST = "smtp.your-provider.com"
$env:SMTP_PORT = "587"
$env:SMTP_USER = "you@example.com"
$env:SMTP_PASS = "app-password"
$env:SMTP_FROM = "DriftRack <you@example.com>"
$env:DRIFTRACK_PUBLIC_URL = "https://your-shop-address"
```

`DRIFTRACK_PUBLIC_URL` is required: reset emails only ever link there.

## 9. Scrolling sale ads

The band under the header on every page. Hover or touch pauses it.

- Edit: Dashboard > **Scrolling sale ads** (owner only). Up to 20.
- Changes go live right away.

## 10. Moving parts in the look

- Floating lights and colour clouds behind every page.
- Scrolling ad band.
- Hero word that swaps every 2 seconds, with drifting item tiles.
- Dashboard and Admin: flowing gradient banner, scrolling word wall, count-up numbers, growing bars.

All motion switches off for people who set "reduce motion" on their device.

## 11. AI descriptions and model switching

Works with no key: a built-in template writes the description.

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
$env:DRIFTRACK_AI_MODELS = "deepseek/deepseek-chat,meta-llama/llama-3.3-70b-instruct:free,openrouter/auto"
```

Models are tried left to right. Out of credit, rate limited or down: it moves to
the next. All fail: template. The Sell page shows which one wrote the text.
Use the exact model IDs from openrouter.ai/models, best first.

## 12. Going live

Nothing below happens until you do it. The default stays local-only.

**Option A - quick public link from your PC (testing with friends):**

```powershell
python app.py
cloudflared tunnel --url http://localhost:8750
```

Install `cloudflared` from Cloudflare first. It prints an `https://...trycloudflare.com`
link. The site is up only while your PC and both windows stay open.

**Option B - real hosting (Render, recommended):**

1. Push this repo to GitHub (already there).
2. render.com > New > **Blueprint** > pick the repo. It reads `driftrack/render.yaml`.
3. Fill in the secret values it asks for (`DRIFTRACK_PUBLIC_URL`, Stripe, SMTP, OpenRouter).
4. Deploy. Render gives you HTTPS and keeps your data on a 1 GB disk.
5. Open the site and **create your owner account first**.
6. Optional: add your own domain in Render > Settings > Custom Domains.

**Any other host with Docker:**

```powershell
docker build -t driftrack .
docker run -d -p 8750:8750 -v driftrack-data:/data `
  -e DRIFTRACK_PUBLIC_URL=https://your-domain `
  -e DRIFTRACK_SECURE_COOKIES=1 -e DRIFTRACK_TRUST_PROXY=1 driftrack
```

Put it behind an HTTPS proxy (Caddy, Nginx, Cloudflare). Set `DRIFTRACK_SECURE_COOKIES=1`
only when the site is served over HTTPS, or logins won't stick.

## 13. Your data

- Everything is in `driftrack\data\` (or `/data` in Docker): `driftrack.db` plus `uploads\`.
- **Back up:** copy the folder while the app is stopped.
- **Start fresh:** stop the app, rename or remove the folder, start again.
- Move it with `$env:DRIFTRACK_DATA = "C:\driftrack-data"`.
- Older databases upgrade themselves on start.

## 14. Change the name, colours, fees

| Change | Where |
| --- | --- |
| Colours | Top of `static\style.css` (`--pink`, `--amber`, `--mint`, `--bg`) |
| Name / tagline | `static\index.html` and the hero text in `static\app.js` |
| Categories, conditions | `CATEGORIES`, `CONDITIONS` in `app.py` |
| Buyer fee | `FEE_PCT`, `FEE_FLAT` in `app.py` |
| Default ads | `DEFAULT_ADS` in `app.py` (brand-new database only) |
| Terms / Privacy text | `LEGAL` in `static\app.js` |
| Port | `$env:DRIFTRACK_PORT = "9000"` |

## 15. Still not built

- Automatic seller payouts (Stripe Connect). You pay sellers manually today.
- Email verification at sign-up.
- Shipping labels and tracking numbers.
- Dispute and refund workflow (refunds are done in the Stripe dashboard).
- Stripe webhooks (payment is confirmed when the buyer returns or on the next page load).
- Terms and Privacy need a legal review for your country.

## 16. Fixes

| Problem | Fix |
| --- | --- |
| "python is not recognized" | Install from python.org, tick "Add to PATH" |
| Port already in use | `$env:DRIFTRACK_PORT = "8751"` then run again |
| Can't see Admin | You're not on the owner account (section 2) |
| "Too many attempts" | Wait 15 minutes, or restart the app |
| Logins don't stick online | Site isn't on HTTPS but `DRIFTRACK_SECURE_COOKIES=1` is set |
| Stripe page won't open | Check the key starts with `sk_test_` or `sk_live_` |
| Reset email never arrives | Check SMTP settings and `DRIFTRACK_PUBLIC_URL`; use Admin reset link meanwhile |
| Photo rejected | JPG, PNG or WEBP under 4 MB |
