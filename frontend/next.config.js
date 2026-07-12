/** @type {import('next').NextConfig} */
// Eval's own FastAPI backend. Must point at THIS app's API, not a sibling's.
const API = process.env.EVAL_API_URL || "http://127.0.0.1:8703";
module.exports = {
  reactStrictMode: false,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};
