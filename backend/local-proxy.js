/**
 * @title Local Development Proxy Server
 * @description Proxy server for Decap CMS with Hugo, handling local authentication
 * @version 1.0.0
 * @author ropean
 *
 * This script creates a proxy server that handles Netlify Identity authentication
 * locally while proxying all other requests to the Hugo development server.
 *
 * @example
 * node local-proxy.js
 * // Then access http://localhost:8080/admin/
 *
 * @requires http-proxy
 * @note For development use only
 */

// Installation: npm install http-proxy
const http = require("http");
const httpProxy = require("http-proxy");

// Create proxy instance
const proxy = httpProxy.createProxyServer({});

// Configuration
const hugoPort = 1313; // Hugo development server port
const proxyPort = 8080; // Proxy server port

/**
 * Create HTTP server with request handling
 */
const server = http.createServer((req, res) => {
  // Set CORS headers for all responses
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

  // Handle preflight OPTIONS requests
  if (req.method === "OPTIONS") {
    res.writeHead(200);
    res.end();
    return;
  }

  // Intercept authentication requests for Netlify Identity
  if (req.url.startsWith("/.netlify/identity/")) {
    if (req.method === "POST") {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", async () => {
        try {
          const data = JSON.parse(body);
          console.log("Authentication request:", data);

          // TODO: Integrate with your OAuth service
          // const response = await fetch('https://your-oauth-service.com/auth', {...});

          // Mock response for testing purposes
          const mockResponse = {
            access_token: "test-token-" + Date.now(),
            token_type: "bearer",
            expires_in: 3600,
            refresh_token: "refresh-token",
            user: {
              id: "1",
              email: data.username || "test@example.com",
              user_metadata: {},
              app_metadata: {
                provider: "custom",
                roles: ["admin"],
              },
            },
          };

          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify(mockResponse));
        } catch (error) {
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: error.message }));
        }
      });
    } else {
      res.writeHead(404);
      res.end();
    }
  } else {
    // Proxy all other requests to Hugo development server
    proxy.web(req, res, { target: `http://localhost:${hugoPort}` });
  }
});

/**
 * Start the proxy server
 */
server.listen(proxyPort, () => {
  console.log(`Proxy server running at http://localhost:${proxyPort}`);
  console.log(`Visit http://localhost:${proxyPort}/admin/ to test Decap CMS`);
});

/**
 * USAGE INSTRUCTIONS:
 *
 * 1. Prerequisites:
 *    - Install dependencies: npm install http-proxy
 *    - Ensure Hugo server is running: hugo server -p 1313
 *
 * 2. Run the proxy:
 *    - Execute: node local-proxy.js
 *
 * 3. Configure Decap CMS:
 *    - In your Decap CMS config.yml, set:
 *        base_url: http://localhost:8080
 *
 * 4. Access:
 *    - Visit http://localhost:8080/admin/ for Decap CMS
 *    - All other routes are proxied to Hugo on port 1313
 *
 * 5. Customization:
 *    - Modify the mockResponse object to match your user schema
 *    - Replace mock authentication with real OAuth integration
 *    - Adjust ports as needed for your environment
 *
 * NOTES:
 * - This is for development use only
 * - Replace mock authentication with production OAuth service
 * - Ensure CORS settings are appropriate for your security requirements
 */
