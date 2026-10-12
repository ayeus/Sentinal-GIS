# SentinelGIS frontend

React 19 + Vite + Tailwind CSS 4, with React Router, Leaflet (maps) and Recharts (charts).

```bash
npm install
npm run dev      # development server on http://localhost:3000 (expects the API on http://127.0.0.1:8000)
npm run build    # production build into build/ (served by the backend, nginx or any static host)
npm test         # unit tests (Vitest)
```

Settings live in `src/config.js` and can be overridden with `VITE_*` variables: copy `.env.example` to `.env.local`.

- `src/pages/` one file per page: Reported, Forecast, Trends, News, About the data
- `src/components/` map, lists, charts, district panel, search
- `src/hooks/` shared state: filters, data status, district panel
- `src/services/api.js` every call to the backend
