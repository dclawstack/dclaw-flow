/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/v1/flows/:path*",
        destination: "http://localhost:8088/api/v1/flows/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
