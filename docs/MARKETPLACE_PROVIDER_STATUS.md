# Marketplace provider integration status

**Important:** Live marketplace search is **not** claimed complete. Providers without credentials return empty results with status `PARTNER_ACCESS_REQUIRED`. Local testing uses the **demonstration** catalogue and **imported** CSV catalogues only.

| Provider | Status | API access | Auth requirements | Sandbox | Live data | Redirect |
|---|---|---|---|---|---|---|
| VoiceKhata Demo Catalogue | DEMONSTRATION | Built-in seed | None | Yes (local) | No (demo) | Yes (`example.com`) |
| Independent wholesalers | IMPORT_READY | CSV / Excel upload | Shop JWT | Yes | Imported only | Optional HTTPS URL |
| Jumbotail | PARTNER_ACCESS_REQUIRED | Unknown without partner agreement | Partner credentials | TBD | No | Pending domain allow-list |
| Wishbee | PARTNER_ACCESS_REQUIRED | Partner portal TBD | Partner credentials | TBD | No | Pending |
| Udaan | PARTNER_ACCESS_REQUIRED | Partner integration TBD | Partner credentials | TBD | No | Pending |
| ONDC RET10 | PARTNER_ACCESS_REQUIRED | Official ONDC participant onboarding | Subscriber ID, keys, gateway | Official sandbox when onboarded | No | Pending |
| Blinkit | PARTNER_ACCESS_REQUIRED | No scraping; partner API only | Partner credentials | TBD | No | Pending |
| BigBasket | PARTNER_ACCESS_REQUIRED | Partner / affiliate TBD | Partner credentials | TBD | No | Pending |
| JioMart | PARTNER_ACCESS_REQUIRED | Partner API TBD | Partner credentials | TBD | No | Pending |

## Environment variables (optional future live connectors)

```
# Placeholder — do not invent live endpoints
JUMBOTAIL_API_KEY=
JUMBOTAIL_BASE_URL=
WISHBEE_API_KEY=
UDAAN_API_KEY=
ONDC_SUBSCRIBER_ID=
ONDC_PRIVATE_KEY=
BLINKIT_API_KEY=
BIGBASKET_API_KEY=
JIOMART_API_KEY=
MARKETPLACE_CACHE_TTL_SEC=120
MARKETPLACE_PROVIDER_TIMEOUT_SEC=4
```

## Local test instructions

1. Start backend: `uvicorn app.main:app --reload --port 8000` from `backend/`
2. Start frontend: `npm run dev` from `frontend/`
3. Open http://127.0.0.1:5173 → sign in with email → open **Market** tab
4. Search: `Fortune sunflower oil wholesale` or `20 kg Aashirvaad atta`
5. Try CSV import under “Import supplier catalogue”
6. Voice (optional): “Find 10 litre Fortune sunflower oil wholesale”
