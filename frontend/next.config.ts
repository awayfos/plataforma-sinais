import type { NextConfig } from "next";

// O frontend fala só com /api; o Next repassa para o backend FastAPI.
// SINAIS_API_URL é lido no build (as regras de rewrite ficam no manifesto).
const api = process.env.SINAIS_API_URL ?? "http://127.0.0.1:8000";

const config: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  async rewrites() {
    return [{ source: "/api/:caminho*", destination: `${api}/api/:caminho*` }];
  },
  async headers() {
    return [
      {
        source: "/:caminho*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default config;
