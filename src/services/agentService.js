const API_URL = import.meta.env.VITE_AGENT_API_URL;
const TIMEOUT_MS = 30000;

// One id per browser tab, so the agent can remember the conversation
const sessionId = crypto.randomUUID();

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Fake agent used while no real agent exists
const MOCK_PRODUCTS = [
  {
    id: "1",
    name: "Example Laptop 15",
    price: 899,
    image: "",
    url: "#",
    specs: { color: "white", ram: "16GB", storage: "512GB SSD" },
  },
  {
    id: "2",
    name: "Example Laptop Pro 16",
    price: 1299,
    image: "",
    url: "#",
    specs: { color: "white", ram: "32GB", storage: "1TB SSD" },
  },
];

async function mockAgent(query, history) {
  console.log("[agentService] Query ready for the AI agent:", {
    sessionId,
    query,
    history,
  });
  await delay(800);
  return {
    reply: `Mock reply: I received "${query}"`,
    products: MOCK_PRODUCTS,
  };
}

// Makes sure the UI always gets the same shape, whatever the agent returns
function normalize(data) {
  return {
    reply: data?.reply ?? "",
    products: Array.isArray(data?.products) ? data.products : [],
  };
}

export async function sendToAgent(query, history = []) {
  if (!API_URL) return mockAgent(query, history);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sessionId, query, history }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Agent request failed: ${response.status}`);
    }

    return normalize(await response.json());
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("The agent took too long to respond");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
