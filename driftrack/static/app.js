// driftrack/static/app.js
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const view = $("#view");
const state = { user: null, meta: null, filters: { sort: "new" } };

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const money = (n) => "$" + Number(n || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ago = (ts) => {
  const s = Date.now() / 1000 - ts;
  if (s < 3600) return Math.max(1, Math.round(s / 60)) + "m ago";
  if (s < 86400) return Math.round(s / 3600) + "h ago";
  return Math.round(s / 86400) + "d ago";
};
const stars = (n) => "★".repeat(Math.round(n || 0)) + "☆".repeat(5 - Math.round(n || 0));
const pic = (src) => esc(src || "/logo.svg");

async function api(path, method = "GET", body) {
  const res = await fetch("/api" + path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

let toastTimer;
function toast(msg, isErr) {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast show" + (isErr ? " err" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.className = "toast"), 2600);
}
const guard = (fn) => async (...args) => {
  try {
    await fn(...args);
  } catch (err) {
    toast(err.message, true);
  }
};
function needLogin() {
  if (state.user) return false;
  toast("Log in to do that");
  location.hash = "#/login";
  return true;
}

// ---------------------------------------------------------------- chrome
function renderNav() {
  const route = location.hash.split("/")[1] || "";
  const on = (r) => (route === r ? " on" : "");
  const u = state.user;
  $("#nav").innerHTML = u
    ? `<a class="${on("")}" href="#/">Browse</a><a class="${on("favorites")}" href="#/favorites">Saved</a>
       <a class="${on("inbox")}" href="#/inbox">Inbox</a><a class="${on("orders")}" href="#/orders">Orders</a>
       <a class="${on("dashboard")}" href="#/dashboard">Dashboard</a>
       <a class="btn primary" href="#/sell">+ Sell</a>
       <a href="#/u/${esc(u.username)}">@${esc(u.username)}</a><a href="#" id="logout">Log out</a>`
    : `<a class="${on("")}" href="#/">Browse</a><a href="#/login">Log in</a><a class="btn primary" href="#/login">Start selling</a>`;
  $("#tabbar").innerHTML = `
    <a class="${on("")}" href="#/"><i>⌂</i>Browse</a>
    <a class="${on("favorites")}" href="#/favorites"><i>♥</i>Saved</a>
    <a class="${on("sell")}" href="#/sell"><i>＋</i>Sell</a>
    <a class="${on("inbox")}" href="#/inbox"><i>✉</i>Inbox</a>
    <a class="${on("dashboard")}" href="${u ? "#/dashboard" : "#/login"}"><i>◔</i>${u ? "Dash" : "Log in"}</a>`;
  const out = $("#logout");
  if (out)
    out.onclick = guard(async (e) => {
      e.preventDefault();
      await api("/logout", "POST");
      state.user = null;
      location.hash = "#/";
      route_();
    });
}

async function loadTicker() {
  const { ads } = await api("/ads");
  const html = ads.map((a) => `<span>${esc(a.text)}</span>`).join("");
  const track = $("#tickerTrack");
  track.innerHTML = html + html; // doubled so the loop is seamless
  track.style.animationDuration = Math.max(22, ads.length * 8) + "s";
  return ads;
}

function startSky() {
  const c = $("#sky");
  const ctx = c.getContext("2d");
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let w, h, dots;
  const colors = ["#ff4d8d", "#ffb347", "#3df2b4", "#8b6cff", "#ffffff"];
  function size() {
    w = c.width = innerWidth;
    h = c.height = innerHeight;
    dots = Array.from({ length: Math.min(90, Math.round((w * h) / 16000)) }, () => ({
      x: Math.random() * w, y: Math.random() * h, r: Math.random() * 2.2 + 0.6,
      vy: Math.random() * 0.35 + 0.08, vx: (Math.random() - 0.5) * 0.25,
      c: colors[(Math.random() * colors.length) | 0], p: Math.random() * 6.28,
    }));
  }
  function frame(t) {
    ctx.clearRect(0, 0, w, h);
    for (const d of dots) {
      d.y -= d.vy;
      d.x += d.vx + Math.sin(t / 1800 + d.p) * 0.15;
      if (d.y < -8) { d.y = h + 8; d.x = Math.random() * w; }
      ctx.globalAlpha = 0.35 + 0.45 * Math.abs(Math.sin(t / 1100 + d.p));
      ctx.fillStyle = d.c;
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, 6.28);
      ctx.fill();
    }
    if (!still) requestAnimationFrame(frame);
  }
  size();
  addEventListener("resize", size);
  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------- pieces
function card(l) {
  return `<a class="card" href="#/item/${l.id}">
    ${l.status !== "active" ? `<span class="badge flag ${esc(l.status)}">${esc(l.status)}</span>` : ""}
    <img class="pic" loading="lazy" src="${pic(l.image)}" alt="${esc(l.title)}" />
    <button class="heart${l.liked ? " on" : ""}" data-like="${l.id}" aria-label="Save item">♥ <span>${l.likes}</span></button>
    <div class="info"><div class="price">${money(l.price)}</div>
      <div class="title">${esc(l.title)}</div>
      <div class="meta">${esc([l.brand, l.size, l.condition].filter(Boolean).join(" · "))}</div></div></a>`;
}
const grid = (items, emptyTitle, emptyText) =>
  items.length
    ? `<div class="grid">${items.map(card).join("")}</div>`
    : `<div class="empty panel"><b>${esc(emptyTitle)}</b>${esc(emptyText)}</div>`;

view.addEventListener(
  "click",
  guard(async (e) => {
    const btn = e.target.closest("[data-like]");
    if (!btn) return;
    e.preventDefault();
    if (needLogin()) return;
    const { liked } = await api(`/listings/${btn.dataset.like}/favorite`, "POST");
    btn.classList.toggle("on", liked);
    const n = $("span", btn);
    n.textContent = Number(n.textContent) + (liked ? 1 : -1);
  })
);

// ---------------------------------------------------------------- home
const HERO_WORDS = ["denim", "sneakers", "vintage", "handbags", "knitwear", "streetwear"];
let heroTimer;
async function pageHome() {
  const f = state.filters;
  const qs = new URLSearchParams(Object.entries(f).filter(([, v]) => v)).toString();
  const { listings } = await api("/listings?" + qs);
  const cats = state.meta.categories;
  const filtering = f.q || f.category || f.condition || f.min || f.max;
  const tiles = listings.slice(0, 8).map((l) => `<img src="${pic(l.image)}" alt="" />`);
  const col = (a) => `<div class="hero-col">${a.join("")}${a.join("")}</div>`;
  view.innerHTML = `
    ${filtering ? "" : `<section class="hero">
      <div class="hero-tags">${col(tiles.slice(0, 4))}${col(tiles.slice(4))}</div>
      <h1>Give great <span class="swap" id="swap">denim</span> a second life.</h1>
      <p>DriftRack is the night market for pre-loved style. Snap it, list it in a minute, and get paid when it lands.</p>
      <div class="row"><a class="btn primary" href="#/sell">Sell an item</a><button type="button" class="btn" id="shopBtn">Shop the racks</button></div>
    </section>`}
    <h2 class="section-title" id="shop">${f.q ? `Results for "${esc(f.q)}"` : "Fresh on the racks"}</h2>
    <div class="chips">
      <button class="chip${f.category ? "" : " on"}" data-cat="">All</button>
      ${cats.map((c) => `<button class="chip${f.category === c ? " on" : ""}" data-cat="${esc(c)}">${esc(c)}</button>`).join("")}
    </div>
    <div class="filters">
      <select id="fCond" aria-label="Condition"><option value="">Any condition</option>
        ${state.meta.conditions.map((c) => `<option${f.condition === c ? " selected" : ""}>${esc(c)}</option>`).join("")}</select>
      <input id="fMin" type="number" min="0" inputmode="decimal" placeholder="Min $" value="${esc(f.min || "")}" aria-label="Minimum price" />
      <input id="fMax" type="number" min="0" inputmode="decimal" placeholder="Max $" value="${esc(f.max || "")}" aria-label="Maximum price" />
      <select id="fSort" aria-label="Sort">
        ${[["new", "Newest"], ["hot", "Most loved"], ["low", "Price: low to high"], ["high", "Price: high to low"]]
          .map(([v, t]) => `<option value="${v}"${f.sort === v ? " selected" : ""}>${t}</option>`).join("")}</select>
    </div>
    ${grid(listings, "Nothing on this rack yet", "Try a different search or clear the filters.")}`;
  view.querySelectorAll("[data-cat]").forEach((b) => (b.onclick = () => { f.category = b.dataset.cat; pageHome().catch(fail); }));
  const bind = (id, key) => ($(id).onchange = (e) => { f[key] = e.target.value; pageHome().catch(fail); });
  bind("#fCond", "condition"); bind("#fMin", "min"); bind("#fMax", "max"); bind("#fSort", "sort");
  if ($("#shopBtn")) $("#shopBtn").onclick = () => $("#shop").scrollIntoView({ behavior: "smooth" });
  clearInterval(heroTimer);
  let i = 0;
  heroTimer = setInterval(() => {
    const el = $("#swap");
    if (!el) return clearInterval(heroTimer);
    el.textContent = HERO_WORDS[++i % HERO_WORDS.length];
    el.style.animation = "none";
    void el.offsetWidth;
    el.style.animation = "";
  }, 2200);
}

// ---------------------------------------------------------------- item
async function pageItem(id) {
  const { listing: l } = await api("/listings/" + id);
  const mine = state.user && state.user.id === l.seller_id;
  const deal = l.my_offer && l.my_offer.status === "accepted" ? l.my_offer.amount : null;
  const price = deal || l.price;
  const fee = price * state.meta.fee.pct + state.meta.fee.flat;
  const r = l.seller_rating;
  let actions = "";
  if (l.status === "sold") actions = `<div class="badge sold">Sold</div>`;
  else if (mine)
    actions = `<a class="btn" href="#/sell/${l.id}">Edit listing</a>
      <button class="btn" id="hideBtn">${l.status === "hidden" ? "Put back on the rack" : "Hide listing"}</button>
      <button class="btn danger" id="delBtn">Delete</button>`;
  else
    actions = `<button class="btn primary block" id="buyBtn">Buy now · ${money(price + fee)}</button>
      <div class="muted" style="font-size:13.500px">${money(price)} item + ${money(fee)} buyer protection${deal ? " · your offer was accepted" : ""}</div>
      <form id="offerForm" class="row"><input style="flex:1;min-width:0;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.07)"
        type="number" step="0.01" min="1" name="amount" placeholder="Your offer $" aria-label="Offer amount" required />
        <button class="btn">Make offer</button></form>
      ${l.my_offer ? `<div class="muted">Your last offer: ${money(l.my_offer.amount)} <span class="badge ${esc(l.my_offer.status)}">${esc(l.my_offer.status)}</span></div>` : ""}
      <form id="msgForm" class="row"><input style="flex:1;min-width:0;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.07)"
        name="body" maxlength="1000" placeholder="Ask the seller a question" aria-label="Message" required /><button class="btn">Send</button></form>`;
  view.innerHTML = `
    <div class="item">
      <img class="pic" src="${pic(l.image)}" alt="${esc(l.title)}" />
      <div class="panel stack">
        <h1>${esc(l.title)}</h1>
        <div class="bigprice">${money(l.price)}</div>
        <dl class="specs">
          ${[["Brand", l.brand], ["Size", l.size], ["Condition", l.condition], ["Category", l.category]]
            .filter(([, v]) => v).map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}
          <dt>Listed</dt><dd>${ago(l.created)} · ${l.views} views · ${l.likes} saves</dd>
        </dl>
        <p style="margin:0;white-space:pre-wrap;overflow-wrap:anywhere">${esc(l.description)}</p>
        <a class="row" href="#/u/${esc(l.seller)}"><b>@${esc(l.seller)}</b>
          <span class="stars">${r.count ? stars(r.avg) : ""}</span>
          <span class="muted">${r.count ? `${r.avg} (${r.count})` : "No reviews yet"}</span></a>
        ${actions}
      </div>
    </div>
    ${l.more.length ? `<h2 class="section-title">More from @${esc(l.seller)}</h2>${grid(l.more)}` : ""}`;
  const on = (sel, ev, fn) => { const el = $(sel); if (el) el[ev] = guard(fn); };
  on("#buyBtn", "onclick", async () => {
    if (needLogin()) return;
    if (!confirm(`Buy "${l.title}" for ${money(price + fee)}? (simulated payment)`)) return;
    await api(`/listings/${l.id}/buy`, "POST");
    toast("It's yours! Order placed.");
    location.hash = "#/orders";
  });
  on("#offerForm", "onsubmit", async (e) => {
    e.preventDefault();
    if (needLogin()) return;
    await api(`/listings/${l.id}/offer`, "POST", { amount: e.target.amount.value });
    toast("Offer sent");
    pageItem(id);
  });
  on("#msgForm", "onsubmit", async (e) => {
    e.preventDefault();
    if (needLogin()) return;
    await api("/messages", "POST", { listing_id: l.id, to: l.seller_id, body: e.target.body.value });
    toast("Message sent");
    e.target.reset();
  });
  on("#hideBtn", "onclick", async () => {
    await api(`/listings/${l.id}`, "PATCH", { status: l.status === "hidden" ? "active" : "hidden" });
    pageItem(id);
  });
  on("#delBtn", "onclick", async () => {
    if (!confirm("Delete this listing for good?")) return;
    await api(`/listings/${l.id}`, "DELETE");
    toast("Listing deleted");
    location.hash = "#/dashboard";
  });
}

// ---------------------------------------------------------------- sell
function shrink(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, 1200 / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * k);
      c.height = Math.round(img.height * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(img.src);
      resolve(c.toDataURL("image/jpeg", 0.86));
    };
    img.onerror = () => reject(new Error("That file is not a readable image"));
    img.src = URL.createObjectURL(file);
  });
}

async function pageSell(id) {
  if (needLogin()) return;
  const l = id ? (await api("/listings/" + id)).listing : {};
  let image = null;
  const opt = (list, cur) => list.map((v) => `<option${v === cur ? " selected" : ""}>${esc(v)}</option>`).join("");
  view.innerHTML = `
    <form id="sellForm" class="panel narrow">
      <h1 style="font-size:28px;margin-bottom:16px">${id ? "Edit listing" : "List an item"}</h1>
      <label class="drop" id="drop"><input type="file" id="file" accept="image/*" hidden />
        ${l.image ? `<img src="${pic(l.image)}" alt="" />` : "<span><b>Tap to add a photo</b><br>JPG or PNG. Natural light sells faster.</span>"}</label>
      <div class="field" style="margin-top:14px"><label for="title">Title</label>
        <input id="title" name="title" maxlength="80" required value="${esc(l.title)}" placeholder="e.g. Levi's 501 straight jeans" /></div>
      <div class="two">
        <div class="field"><label for="brand">Brand</label><input id="brand" name="brand" maxlength="40" value="${esc(l.brand)}" /></div>
        <div class="field"><label for="size">Size</label><input id="size" name="size" maxlength="20" value="${esc(l.size)}" /></div>
      </div>
      <div class="two">
        <div class="field"><label for="category">Category</label><select id="category" name="category">${opt(state.meta.categories, l.category)}</select></div>
        <div class="field"><label for="condition">Condition</label><select id="condition" name="condition">${opt(state.meta.conditions, l.condition || "Good")}</select></div>
      </div>
      <div class="field"><label for="price">Price ($)</label>
        <input id="price" name="price" type="number" step="0.01" min="0.5" inputmode="decimal" required value="${esc(l.price || "")}" /></div>
      <div class="field"><div class="row spread"><label for="description">Description</label>
        <button type="button" class="btn small" id="aiBtn">✦ Write it for me</button></div>
        <textarea id="description" name="description" rows="5" maxlength="1500">${esc(l.description)}</textarea>
        <small class="muted" id="aiNote"></small></div>
      <button class="btn primary block">${id ? "Save changes" : "Put it on the rack"}</button>
    </form>`;
  const form = $("#sellForm");
  $("#file").onchange = guard(async (e) => {
    if (!e.target.files[0]) return;
    image = await shrink(e.target.files[0]);
    $("#drop").innerHTML = `<img src="${image}" alt="Preview" />`;
  });
  $("#aiBtn").onclick = guard(async () => {
    const data = Object.fromEntries(new FormData(form));
    $("#aiBtn").disabled = true;
    try {
      const out = await api("/ai/describe", "POST", data);
      form.description.value = out.text;
      $("#aiNote").textContent = out.model === "local-template" ? "Written by the built-in template." : "Written by " + out.model;
    } finally {
      $("#aiBtn").disabled = false;
    }
  });
  form.onsubmit = guard(async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    if (image) data.image = image;
    const out = id ? await api("/listings/" + id, "PATCH", data) : await api("/listings", "POST", data);
    toast(id ? "Saved" : "Listed! It's on the rack.");
    location.hash = "#/item/" + (id || out.id);
  });
}

// ---------------------------------------------------------------- dashboard
function countUp(el) {
  const end = Number(el.dataset.to);
  const isMoney = el.dataset.money === "1";
  const t0 = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - t0) / 900);
    const v = end * (1 - Math.pow(1 - k, 3));
    el.textContent = isMoney ? money(v) : Math.round(v).toLocaleString("en-US");
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function barChart(days) {
  const W = 640, H = 220, pad = 26, max = Math.max(10, ...days.map((d) => d.total));
  const bw = (W - pad * 2) / days.length;
  const bars = days.map((d, i) => {
    const h = (d.total / max) * (H - 62);
    return `<rect class="bar" style="animation-delay:${i * 45}ms" x="${pad + i * bw + 5}" y="${H - 30 - h}" width="${bw - 10}" height="${Math.max(h, 2)}" rx="5"><title>${esc(d.day)}: ${money(d.total)}</title></rect>
      ${i % 2 === 0 ? `<text x="${pad + i * bw + bw / 2}" y="${H - 10}" text-anchor="middle">${esc(d.day)}</text>` : ""}`;
  });
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Sales over the last 14 days">
    <defs><linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffb347"/><stop offset="1" stop-color="#ff4d8d"/></linearGradient></defs>
    <text x="${pad}" y="16">Peak day ${money(max)}</text>
    <line x1="${pad}" x2="${W - pad}" y1="${H - 30}" y2="${H - 30}" stroke="rgba(255,255,255,.18)"/>${bars.join("")}</svg>`;
}

async function pageDashboard() {
  if (needLogin()) return;
  const [d, { ads }, offers] = await Promise.all([api("/dashboard"), api("/ads"), api("/offers")]);
  const s = d.stats;
  const u = state.user;
  const wall = ["Sold", "Fresh drop", "New offer", "Shipped", "Five stars", "Paid out"];
  const stat = (label, val, isMoney, cls = "") =>
    `<div class="stat ${cls}"><small>${label}</small><b data-to="${val}" data-money="${isMoney ? 1 : 0}">0</b></div>`;
  const pending = offers.incoming.filter((o) => o.status === "pending");
  view.innerHTML = `
    <section class="dash-hero">
      <div class="wordwall">${[0, 1, 2, 3].map((r) => `<div>${Array(8).fill(wall.slice(r).concat(wall.slice(0, r)).join(" ✦ ")).join(" ✦ ")}</div>`).join("")}</div>
      <div class="row spread">
        <div><div class="muted" style="color:#f1e6ff">Seller dashboard${u.is_owner ? " · marketplace owner" : ""}</div>
          <h1>Hey @${esc(u.username)}, you've made <span data-to="${s.revenue}" data-money="1">$0</span></h1>
          <div style="margin-top:8px"><span class="stars">${d.rating.count ? stars(d.rating.avg) : "☆☆☆☆☆"}</span>
            ${d.rating.count ? `${d.rating.avg} from ${d.rating.count} reviews` : "No reviews yet"}</div></div>
        <a class="btn primary" href="#/sell">+ List an item</a>
      </div>
    </section>
    <div class="stats">
      ${stat("Wallet balance", s.balance, true, "mint")}${stat("On the way", s.pending, true)}
      ${stat("Items sold", s.sold)}${stat("Active listings", s.active, false, "violet")}
      ${stat("Views", s.views, false, "violet")}${stat("Saves", s.likes)}
      ${stat("Open offers", s.offers)}${stat("To ship", s.to_ship, false, "mint")}
    </div>
    <div class="dash-grid">
      <div class="panel"><div class="row spread"><h2 style="font-size:19px">Sales, last 14 days</h2></div>${barChart(d.days)}</div>
      <div class="panel"><h2 style="font-size:19px;margin-bottom:12px">Live activity</h2>
        <div class="feed">${d.activity.map((a) => `<div><i class="dot ${a.kind}"></i><span><b>@${esc(a.who)}</b>
          ${a.kind === "sale" ? "bought" : a.kind === "offer" ? "offered " + money(a.amount) + " on" : "saved"} ${esc(a.title)}
          ${a.kind === "sale" ? "for " + money(a.amount) : ""} <span class="muted">· ${ago(a.created)}</span></span></div>`).join("") || `<div class="muted">Activity shows up here as buyers find you.</div>`}</div></div>
    </div>
    ${pending.length ? `<h2 class="section-title">Offers waiting on you</h2><div class="panel table-wrap"><table>
      <tr><th></th><th>Item</th><th>Buyer</th><th class="num">Asking</th><th class="num">Offer</th><th></th></tr>
      ${pending.map((o) => `<tr><td><img class="thumb" src="${pic(o.image)}" alt="" /></td><td><a href="#/item/${o.listing_id}">${esc(o.title)}</a></td>
        <td>@${esc(o.buyer)}</td><td class="num">${money(o.price)}</td><td class="num"><b>${money(o.amount)}</b></td>
        <td class="num"><button class="btn small mint" data-offer="${o.id}" data-act="accept">Accept</button>
          <button class="btn small" data-offer="${o.id}" data-act="decline">Decline</button></td></tr>`).join("")}</table></div>` : ""}
    <h2 class="section-title">Your rack</h2>
    <div class="panel table-wrap">${d.listings.length ? `<table>
      <tr><th></th><th>Item</th><th>Status</th><th class="num">Price</th><th class="num">Views</th><th class="num">Saves</th></tr>
      ${d.listings.map((l) => `<tr><td><img class="thumb" src="${pic(l.image)}" alt="" /></td><td><a href="#/item/${l.id}">${esc(l.title)}</a></td>
        <td><span class="badge ${esc(l.status)}">${esc(l.status)}</span></td><td class="num">${money(l.price)}</td>
        <td class="num">${l.views}</td><td class="num">${l.likes}</td></tr>`).join("")}</table>`
      : `<div class="empty"><b>Your rack is empty</b>List your first item - it takes about a minute.</div>`}</div>
    <h2 class="section-title">Scrolling sale ads</h2>
    <div class="panel">${u.is_owner ? `<p class="muted" style="margin-top:0">These scroll across the top of every page. You own this marketplace, so you control them.</p>
      <div id="adList">${ads.map((a) => `<div class="adrow"><span>${esc(a.text)}</span><button class="btn small danger" data-ad="${a.id}">Remove</button></div>`).join("")}</div>
      <form id="adForm" class="row" style="margin-top:12px"><input name="text" maxlength="90" required placeholder="e.g. 20% off all shoes this Friday" aria-label="New ad"
        style="flex:1;min-width:0;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.07)" /><button class="btn primary">Add ad</button></form>`
      : `<p class="muted" style="margin:0">${ads.length} ads are scrolling right now. Only the marketplace owner account can edit them.</p>`}</div>`;
  view.querySelectorAll("[data-to]").forEach(countUp);
  view.querySelectorAll("[data-offer]").forEach((b) => (b.onclick = guard(async () => {
    await api("/offers/" + b.dataset.offer, "POST", { action: b.dataset.act });
    toast("Offer " + b.dataset.act + "ed");
    pageDashboard();
  })));
  view.querySelectorAll("[data-ad]").forEach((b) => (b.onclick = guard(async () => {
    await api("/ads/" + b.dataset.ad, "DELETE");
    await loadTicker();
    pageDashboard();
  })));
  const adForm = $("#adForm");
  if (adForm) adForm.onsubmit = guard(async (e) => {
    e.preventDefault();
    await api("/ads", "POST", { text: e.target.text.value });
    await loadTicker();
    toast("Ad is now scrolling");
    pageDashboard();
  });
}

// ---------------------------------------------------------------- orders
async function pageOrders() {
  if (needLogin()) return;
  const { bought, sold } = await api("/orders");
  const row = (o, side) => {
    let act = "";
    if (side === "sold" && o.status === "paid") act = `<button class="btn small mint" data-order="${o.id}" data-act="ship">Mark shipped</button>`;
    if (side === "bought" && o.status === "shipped") act = `<button class="btn small mint" data-order="${o.id}" data-act="received">I got it</button>`;
    if (side === "bought" && o.status === "complete") act = o.rating ? `<span class="stars">${stars(o.rating)}</span>` : `<button class="btn small" data-order="${o.id}" data-act="review">Leave review</button>`;
    if (side === "sold" && o.rating) act = `<span class="stars">${stars(o.rating)}</span>`;
    return `<tr><td><img class="thumb" src="${pic(o.image)}" alt="" /></td><td>${esc(o.title)}<div class="muted" style="font-size:13px">${side === "sold" ? "to @" + esc(o.buyer) : "from @" + esc(o.seller)} · ${ago(o.created)}</div></td>
      <td><span class="badge ${esc(o.status)}">${esc(o.status)}</span></td><td class="num">${money(side === "sold" ? o.price : o.price + o.fee)}</td><td class="num">${act}</td></tr>`;
  };
  const table = (list, side, emptyText) => list.length
    ? `<div class="panel table-wrap"><table><tr><th></th><th>Item</th><th>Status</th><th class="num">Total</th><th></th></tr>${list.map((o) => row(o, side)).join("")}</table></div>`
    : `<div class="panel empty">${emptyText}</div>`;
  view.innerHTML = `<h2 class="section-title" style="margin-top:0">Things you bought</h2>${table(bought, "bought", "<b>No purchases yet</b>Find something you love on the racks.")}
    <h2 class="section-title">Things you sold</h2>${table(sold, "sold", "<b>No sales yet</b>Your sold items will show up here.")}`;
  view.querySelectorAll("[data-order]").forEach((b) => (b.onclick = guard(async () => {
    let body;
    if (b.dataset.act === "review") {
      const rating = prompt("Rate the seller from 1 to 5 stars", "5");
      if (!rating) return;
      body = { rating, text: prompt("Add a short review (optional)", "") || "" };
    }
    await api(`/orders/${b.dataset.order}/${b.dataset.act}`, "POST", body || {});
    toast("Updated");
    pageOrders();
  })));
}

// ---------------------------------------------------------------- inbox
async function pageInbox(lid, other) {
  if (needLogin()) return;
  const { threads } = await api("/threads");
  if (!lid && threads.length) { lid = threads[0].listing_id; other = threads[0].other_id; }
  const cur = threads.find((t) => t.listing_id == lid && t.other_id == other);
  const msgs = cur ? (await api(`/messages?listing=${lid}&with=${other}`)).messages : [];
  view.innerHTML = threads.length ? `<div class="inbox">
    <div class="panel" style="padding:10px">${threads.map((t) => `<a class="thread${t === cur ? " on" : ""}" href="#/inbox/${t.listing_id}/${t.other_id}">
      <img class="thumb" src="${pic(t.image)}" alt="" /><div><b>@${esc(t.other)}</b><p>${esc(t.title)}</p><p>${esc(t.last)}</p></div></a>`).join("")}</div>
    <div class="panel stack">${cur ? `<a href="#/item/${cur.listing_id}"><b>${esc(cur.title)}</b> <span class="muted">with @${esc(cur.other)}</span></a>
      <div class="bubbles" id="bubbles">${msgs.map((m) => `<div class="bubble${m.from_id === state.user.id ? " me" : ""}">${esc(m.body)}</div>`).join("")}</div>
      <form id="replyForm" class="row"><input name="body" maxlength="1000" required placeholder="Write a reply" aria-label="Reply"
        style="flex:1;min-width:0;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.07)" /><button class="btn primary">Send</button></form>` : ""}</div></div>`
    : `<div class="panel empty"><b>Your inbox is quiet</b>Questions from buyers and your chats with sellers land here.</div>`;
  const box = $("#bubbles");
  if (box) box.scrollTop = box.scrollHeight;
  const form = $("#replyForm");
  if (form) form.onsubmit = guard(async (e) => {
    e.preventDefault();
    await api("/messages", "POST", { listing_id: cur.listing_id, to: cur.other_id, body: e.target.body.value });
    pageInbox(lid, other);
  });
}

// ---------------------------------------------------------------- others
async function pageFavorites() {
  if (needLogin()) return;
  const { listings } = await api("/favorites");
  view.innerHTML = `<h2 class="section-title" style="margin-top:0">Saved items</h2>${grid(listings, "Nothing saved yet", "Tap the heart on anything you like.")}`;
}

async function pageProfile(name) {
  const { profile: p } = await api("/users/" + encodeURIComponent(name));
  const mine = state.user && state.user.id === p.id;
  view.innerHTML = `<div class="panel"><div class="row spread"><div><h1 style="font-size:30px">@${esc(p.username)}</h1>
      <div class="muted">${esc(p.city || "Somewhere stylish")} · ${p.sold} sold · joined ${ago(p.created)}</div>
      <div><span class="stars">${p.rating.count ? stars(p.rating.avg) : ""}</span> ${p.rating.count ? `${p.rating.avg} (${p.rating.count} reviews)` : "No reviews yet"}</div></div></div>
      <p style="margin-bottom:0;overflow-wrap:anywhere">${esc(p.bio)}</p>
      ${mine ? `<form id="bioForm" class="row" style="margin-top:14px"><input name="city" maxlength="40" placeholder="City" value="${esc(p.city)}" aria-label="City"
        style="width:130px;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.07)" />
        <input name="bio" maxlength="300" placeholder="Short bio" value="${esc(p.bio)}" aria-label="Bio"
        style="flex:1;min-width:0;padding:11px 14px;border-radius:12px;border:1px solid var(--line);background:rgba(255,255,255,.07)" /><button class="btn">Save</button></form>` : ""}</div>
    <h2 class="section-title">On the rack</h2>${grid(p.listings, "Nothing listed right now", "Check back soon.")}
    ${p.reviews.length ? `<h2 class="section-title">Reviews</h2><div class="panel stack">${p.reviews.map((r) => `<div><span class="stars">${stars(r.rating)}</span> <b>@${esc(r.buyer)}</b> <span class="muted">· ${ago(r.created)}</span><div>${esc(r.text)}</div></div>`).join("")}</div>` : ""}`;
  const form = $("#bioForm");
  if (form) form.onsubmit = guard(async (e) => {
    e.preventDefault();
    await api("/profile", "POST", Object.fromEntries(new FormData(form)));
    toast("Profile saved");
    pageProfile(name);
  });
}

function pageLogin() {
  view.innerHTML = `<form id="authForm" class="panel narrow">
    <h1 style="font-size:28px">Welcome to DriftRack</h1>
    <p class="muted">Log in, or pick a username and password to create your account.</p>
    <div class="field"><label for="username">Username</label><input id="username" name="username" autocomplete="username" required minlength="3" maxlength="24" /></div>
    <div class="field"><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required minlength="6" /></div>
    <div class="row"><button class="btn primary" style="flex:1" value="login">Log in</button><button class="btn" style="flex:1" value="register">Create account</button></div>
    <p class="muted" style="margin-bottom:0;font-size:13.500px">Demo seller: <b>demo</b> / <b>demo123</b></p></form>`;
  $("#authForm").onsubmit = guard(async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    const out = await api("/" + (e.submitter?.value || "login"), "POST", data);
    state.user = out.user;
    toast("Welcome, @" + out.user.username);
    location.hash = "#/dashboard";
  });
}

// ---------------------------------------------------------------- router
function fail(err) {
  view.innerHTML = `<div class="panel empty"><b>That didn't load</b>${esc(err.message)}<br><br><a class="btn" href="#/">Back to the racks</a></div>`;
}
function route_() {
  const [, page = "", a, b] = location.hash.split("/");
  renderNav();
  const pages = {
    "": pageHome, item: () => pageItem(a), sell: () => pageSell(a), dashboard: pageDashboard, orders: pageOrders,
    inbox: () => pageInbox(a, b), favorites: pageFavorites, u: () => pageProfile(a), login: pageLogin,
  };
  Promise.resolve((pages[page] || pageHome)()).catch(fail);
  if (page !== "") scrollTo(0, 0);
}

$("#searchForm").onsubmit = (e) => {
  e.preventDefault();
  state.filters.q = $("#searchBox").value.trim();
  if (location.hash.replace("#/", "") === "") route_();
  else location.hash = "#/";
};
$("#searchBox").addEventListener("search", (e) => { if (!e.target.value) $("#searchForm").requestSubmit(); });
addEventListener("hashchange", route_);

(async function boot() {
  startSky();
  try {
    const [me, meta] = await Promise.all([api("/me"), api("/meta")]);
    state.user = me.user;
    state.meta = meta;
    loadTicker().catch(() => {});
    route_();
  } catch (err) {
    fail(err);
  }
})();
