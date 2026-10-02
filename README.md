# pieTrade

Python Trading Bot using the OANDA trading API.



## Trade API and web dashboard (local network)

`api/` is a read-only FastAPI service over `Trades_db/pytrade.db`; `web/` is an Angular app that uses it
(trade explorer and performance dashboard).

```
pip install -r requirements-api.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000     # API, docs at http://<host>:8000/docs

cd web && npm install && npx ng serve --host 0.0.0.0   # app at http://<host>:4200
```

- `PYTRADE_DB` overrides the database path; `CORS_ORIGINS` adds allowed origins (localhost and private LAN ranges are allowed by default).
- The web app calls the API on the same hostname, port 8000 (see `web/src/environments/environment.ts`).
- Tests: `pip install -r requirements-api-dev.txt && pytest tests`.
