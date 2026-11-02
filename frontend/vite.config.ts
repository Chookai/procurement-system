import { defineConfig, type ProxyOptions } from "vite";

// The API proxy target defaults to the local development backend. The browser
// smoke suite overrides it (SMOKE_API_PROXY) so the test frontend talks to its
// own isolated backend without changing the default behaviour.
const apiTarget = process.env.SMOKE_API_PROXY ?? "http://127.0.0.1:8001";

// The backend only accepts browser origins it knows about. During the smoke run
// the frontend listens on a disposable port, so the proxy presents an allowed
// loopback origin to the API. This override applies only when SMOKE_API_PROXY
// is set and leaves normal local development untouched.
const smokeOrigin = process.env.SMOKE_ORIGIN;

const proxy: Record<string, ProxyOptions> = {
  "/api": {
    target: apiTarget,
    changeOrigin: false,
    ...(smokeOrigin
      ? {
          configure(server) {
            server.on("proxyReq", (proxyRequest) => {
              proxyRequest.setHeader("Origin", smokeOrigin);
            });
          },
        }
      : {}),
  },
};

export default defineConfig({
  server: { proxy },
});
