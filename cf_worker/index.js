export default {
  async fetch(request) {
    if (request.method !== "POST") {
      return new Response("V2 Proxy Active (Use POST with JSON payload)", { status: 200 });
    }
    try {
      const data = await request.json();
      const options = {
        method: data.method || "GET",
        headers: data.headers || {},
      };
      if (data.body) {
        options.body = data.body;
      }
      const response = await fetch(data.url, options);
      return new Response(response.body, {
        status: response.status,
        headers: response.headers
      });
    } catch(e) {
      return new Response(JSON.stringify({error: e.message}), { status: 500 });
    }
  }
};
