import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Завдання (html/py/md) передаються через server actions
  experimental: {
    serverActions: { bodySizeLimit: "15mb" },
  },
  poweredByHeader: false,
};

export default nextConfig;
