/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",   // required for Docker deployment
};

module.exports = nextConfig;
