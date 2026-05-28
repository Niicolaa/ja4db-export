# ja4db-proxy (Cloudflare Worker)

GitHub Actions runners (Azure IPs) currently cannot reach `https://ja4db.com/api/read/`
— the TCP handshake times out, so we never even get an HTTP response. This Worker
proxies the request from Cloudflare's network instead, which is allowed.

## Deploy

You need a free Cloudflare account and `npx wrangler` (no global install required).

```bash
cd worker
npx wrangler login
npx wrangler deploy
```

Wrangler will print the deployed URL, e.g.
`https://ja4db-proxy.<your-subdomain>.workers.dev`.

## Wire it into the workflow

In the GitHub repo: **Settings → Secrets and variables → Actions → Variables**,
add a repository variable:

- Name: `JA4DB_API_URL`
- Value: `https://ja4db-proxy.<your-subdomain>.workers.dev/`

The workflow reads this variable and falls back to the direct ja4db.com URL if
it's unset, so nothing breaks if you don't deploy the Worker.
