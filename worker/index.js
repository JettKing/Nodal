const PAGES_ORIGIN = "https://jettking.github.io/Nodal";
const SOURCES = ["HMQ006", "HYL001", "LXS004", "FYH002", "WXQ005", "WXY003", "vpn"];

function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=300",
      "access-control-allow-origin": "*",
      ...extraHeaders,
    },
  });
}

function cors(request) {
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "access-control-allow-origin": "*",
        "access-control-allow-methods": "GET, OPTIONS",
        "access-control-allow-headers": "content-type",
        "access-control-max-age": "86400",
      },
    });
  }
  return null;
}

async function handle(request) {
    const preflight = cors(request);
    if (preflight) return preflight;
    if (request.method !== "GET") return json({ error: "method_not_allowed" }, 405);

    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "/api") {
      return json({
        name: "Nodal API",
        version: 1,
        endpoints: ["/health", "/sources", "/config/:source"],
        source: PAGES_ORIGIN,
      });
    }
    if (url.pathname === "/health") {
      return json({ ok: true, service: "nodal-api", source: PAGES_ORIGIN });
    }
    if (url.pathname === "/sources") {
      return json({ sources: SOURCES.map((name) => ({ name, url: url.origin + "/config/" + name })) });
    }
    const match = url.pathname.match(/^\/config\/([A-Za-z0-9_-]+)$/);
    if (!match || !SOURCES.includes(match[1])) {
      return json({ error: "not_found" }, 404);
    }
    const upstream = await fetch(PAGES_ORIGIN + "/" + match[1] + ".yaml", {
      cf: { cacheTtl: 300, cacheEverything: true },
    });
    if (!upstream.ok) return json({ error: "upstream_unavailable", status: upstream.status }, 502);
    const headers = new Headers(upstream.headers);
    headers.set("content-type", "text/yaml; charset=utf-8");
    headers.set("content-disposition", "inline; filename=\"" + match[1] + ".yaml\"");
    headers.set("access-control-allow-origin", "*");
    headers.set("cache-control", "public, max-age=300");
    return new Response(upstream.body, { status: 200, headers });
}

addEventListener("fetch", (event) => {
  event.respondWith(handle(event.request));
});
