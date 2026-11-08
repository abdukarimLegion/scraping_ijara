# scraping_ijara

OLX, birbir, joyme va Telegram kanal/guruhlardan ijara e'lonlarini yig'ib, **yangi e'lon paydo bo'lishi bilanoq** xabar beradigan scraper.

```
manbalar ──► Runner ──► filtr ──► SQLite (dublikat yo'q) ──► yangi bo'lsa ──► Notifier (konsol / Telegram bot / webhook)
```

- **Polling manbalar** (OLX, `t.me/s/` kanallar, birbir, joyme) har `interval` soniyada so'raladi (jitter va xatoda backoff bilan).
- **Push manba** (`telegram_live`, Telethon) — guruh va yopiq kanallarda xabar kelishi bilan **darhol** ishlaydi.
- Yangi manba/kanal qo'shilganda birinchi yurishda eski e'lonlar jim saqlanadi (spam bo'lmaydi); `notify_on_first_run: true` bilan o'zgartiriladi.

## Ishga tushirish

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp config.example.yaml config.yaml     # manbalarni to'ldiring
python -m ijara_scraper run            # doimiy kuzatish
python -m ijara_scraper once           # bir marta
python -m ijara_scraper stats
python -m ijara_scraper export --format csv > listings.csv
pytest
```

Telegram bot orqali xabar olish: `BOT_TOKEN` va `BOT_CHAT_ID` muhit o'zgaruvchilari (yoki `notify.telegram`).

## Manbalar holati (muhim)

| Manba | Holat |
|---|---|
| `telegram_web` (ommaviy kanallar) | ✅ haqiqiy `t.me/s/` HTML bilan tekshirilgan |
| `telegram_live` (guruh, yopiq kanal) | ⚠️ kod tayyor, `TG_API_ID`/`TG_API_HASH` bilan jonli sinalmagan. `python -m ijara_scraper tg-login` |
| `olx` | ⚠️ OLX API'si dev-muhit IP'sini 403 (CloudFront) bilan bloklagan, maydonlar jonli tekshirilmagan. `category_id` ni DevTools'dan aniqlang. Serveringizda (uy/rezident IP) sinab ko'ring |
| birbir.uz | ⚠️ Cloudflare "Just a moment" challenge. Aylanib o'tish **qilinmagan**; `render: true` (Playwright) yordam berishi mumkin, selektorlarni to'ldirish kerak |
| joyme.uz | ⚠️ Vue SPA, API `api.resttab.com`; `/room/search` parametrsiz 500 qaytardi. Haqiqiy endpoint va maydonlarni DevTools'dan topib `config.yaml`ga yozing |

Birbir va joyme umumiy `html` / `json_api` manbalari orqali **config bilan** sozlanadi — sayt o'zgarsa kod emas, config tuzatiladi.

## Eslatma

Saytlarning foydalanish shartlari va `robots.txt` ga rioya qiling, so'rovlar chastotasini oshirib yubormang. Telegram'da faqat o'zingiz a'zo bo'lgan chatlarni o'qing.
