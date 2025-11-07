/**
 * @title Decap CMS Auth Request Interceptor
 * @description Intercepts and redirects Decap CMS authentication requests to local development server
 * @version 1.0.0
 *
 * This utility intercepts Netlify Identity authentication requests from Decap CMS
 * and redirects them to a local authentication endpoint. Useful for local development
 * and testing of Decap CMS without requiring actual Netlify Identity setup.
 *
 * @example
 * // Include this script in your HTML before Decap CMS loads
 * <script src="intercept-requests.js"></script>
 *
 * @requires Local auth server running on http://localhost:3000/auth
 * @note This is for development use only. Do not use in production.
 */

const originalFetch = window.fetch;
window.fetch = async function (...args) {
  let [url, options] = args;

  console.warn('⚠️ Using local development mode, not suitable for production environment');

  // Intercept authentication requests
  if (location.hostname === 'localhost' && url.includes('/.netlify/identity/token')) {
    console.log('Intercepting authentication request');

    const response = await originalFetch('http://localhost:3000/auth', options);
    const data_2 = await response.json();
    return new Response(
      JSON.stringify({
        access_token: data_2.token,
        token_type: 'bearer',
        expires_in: 3600,
        user: {
          id: data_2.user.id,
          email: data_2.user.email,
          user_metadata: {},
          app_metadata: { roles: ['admin'] },
        },
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  return originalFetch(...args);
};
