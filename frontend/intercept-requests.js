// Intercept Decap CMS authentication requests
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
