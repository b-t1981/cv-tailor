/** @type {import('next').NextConfig} */
const backendUrl = (process.env.BACKEND_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!process.env.BACKEND_URL && process.env.VERCEL) {
      console.warn(
        "[cv-tailor] BACKEND_URL is not set on Vercel — configure it or NEXT_PUBLIC_API_URL (see .env.vercel.example).",
      );
    }
    return [
      {
        source: "/api-backend/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
