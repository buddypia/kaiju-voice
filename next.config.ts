import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  output: 'standalone',
  serverExternalPackages: ['sucrase'],
  devIndicators: process.env.NEXT_DEV_INDICATORS === 'true' ? {} : (false as const),
};

export default nextConfig;
