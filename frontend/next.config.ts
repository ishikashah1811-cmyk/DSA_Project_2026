import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  agentRules: false,
  allowedDevOrigins: ["127.0.0.1", "localhost", "192.168.1.21"],
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
