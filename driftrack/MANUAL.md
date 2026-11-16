# DriftRack Owner's Manual

## 1. Start it

```powershell
cd driftrack
python app.py --seed
```

Then open http://127.0.0.1:8750. Stop it with `Ctrl+C`.

- `--seed` loads 5 demo sellers and 24 listings. Leave it off for an empty shop.
- `.\start.ps1` gives a menu: install check, run with demo, run empty, run tests.

## 2. Become the owner

The **first account created through the sign-up form** is the marketplace owner.
Demo accounts never count. Create yours first, before sharing the link.

The owner gets one extra power: editing the scrolling sale ads.

## 3. The screens

| Screen | What you do there |
| --- | --- |
| Browse | Search, filter by category / condition / price, sort, save with the heart |
| Item | Buy now, make an offer, message the seller |
| Sell | Add a photo, details and price. "Write it for me" drafts the description |
| Dashboard | Earnings, stats, 14-day sales chart, live activity, offers, your rack, sale ads |
| Orders | Mark shipped (seller), confirm delivery and review (buyer) |
| Inbox | Chats, grouped by item |
| Saved | Everything you hearted |
| Profile | Bio, city, reviews, active listings |

On a phone the menu moves to a tab bar at the bottom.

## 4. How a sale works

1. Seller lists an item. It shows as **active**.
2. Buyer taps **Buy now**, or sends an offer (40% of the price or more, below asking).
3. Seller accepts or declines offers on the Dashboard. An accepted offer becomes that buyer's price.
4. Buyer pays the item price plus buyer protection: **5% + $0.70**. Item flips to **sold**.
5. Seller taps **Mark shipped** in Orders.
6. Buyer taps **I got it**. Only then does the money land in the seller's wallet.
7. Buyer can leave one 1-5 star review.

Order status: `paid` > `shipped` > `complete`.

## 5. Scrolling sale ads

The band under the header on every page. Hover (or touch) pauses it.

- Edit: Dashboard > **Scrolling sale ads** (owner only). Add or remove, up to 20.
- Changes go live right away for everyone.

## 6. Moving parts in the look

- Floating lights and colour clouds behind every page.
- Scrolling ad band.
- Hero word that swaps every 2 seconds, with drifting item tiles.
- Dashboard: flowing gradient banner, scrolling word wall, count-up numbers, growing bars.

All motion switches off automatically for people who set "reduce motion" on their device.

## 7. AI descriptions and model switching

Works with no key: a built-in template writes the description.

To use OpenRouter:

```powershell
$env:OPENROUTER_API_KEY = "sk-or-..."
$env:DRIFTRACK_AI_MODELS = "deepseek/deepseek-chat,meta-llama/llama-3.3-70b-instruct:free,openrouter/auto"
python app.py
```

Models are tried left to right. If one is out of credit, rate limited or down,
DriftRack moves to the next. If every model fails, the template is used.
The Sell page shows which one wrote the text.
Put the exact model IDs from openrouter.ai/models in the list, best first.

## 8. Your data

- Everything is in `driftrack\data\` : `driftrack.db` plus `uploads\` (photos).
- **Back up:** copy the `data` folder while the app is stopped.
- **Start fresh:** stop the app, rename or remove the `data` folder, start again.
- Move it elsewhere with `$env:DRIFTRACK_DATA = "C:\driftrack-data"`.

## 9. Change the name, colours, fees

| Change | Where |
| --- | --- |
| Colours | Top of `static\style.css` (`--pink`, `--amber`, `--mint`, `--bg`) |
| Name / tagline | `static\index.html` and the hero text in `static\app.js` |
| Categories, conditions | `CATEGORIES`, `CONDITIONS` in `app.py` |
| Buyer fee | `FEE_PCT`, `FEE_FLAT` in `app.py` |
| Default ads | `DEFAULT_ADS` in `app.py` (only used on a brand-new database) |
| Port | `$env:DRIFTRACK_PORT = "9000"` |

## 10. Before going public (not done yet, on purpose)

This is the sandbox build. Before real customers use it:

- Real payments (Stripe Connect or similar). Today nothing is charged.
- HTTPS and a real host. Today it only answers on your own machine.
- Email verification, password reset, login rate limiting.
- Moderation and reporting tools, terms and privacy pages.
- Shipping labels and dispute handling.

## 11. Fixes

| Problem | Fix |
| --- | --- |
| "python is not recognized" | Install from python.org, tick "Add to PATH" |
| Port already in use | `$env:DRIFTRACK_PORT = "8751"` then run again |
| Can't edit ads | You're not on the owner account (see section 2) |
| Photo rejected | Use JPG, PNG or WEBP under 4 MB |
