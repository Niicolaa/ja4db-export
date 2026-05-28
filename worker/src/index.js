const UPSTREAM = "https://ja4db.com/api/read/";

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    const upstreamResp = await fetch(UPSTREAM, {
      method: "GET",
      headers: {
        "User-Agent": "ja4db-export-proxy/1.0 (+https://github.com/Niicolaa/ja4db-export)",
        "Accept": "application/json",
      },
      cf: { cacheTtl: 3600, cacheEverything: true },
    });

    return new Response(upstreamResp.body, {
      status: upstreamResp.status,
      headers: {
        "Content-Type":
          upstreamResp.headers.get("content-type") || "application/json",
        "Cache-Control": "public, max-age=3600",
      },
    });
  },
};
