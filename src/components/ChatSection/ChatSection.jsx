import { useState } from "react";
import ChatInput from "../ChatInput/ChatInput";
import { sendToAgent } from "../../services/agentService";
import "./ChatSection.css";

function ChatSection() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSend = async (text) => {
    // Previous messages become the history sent to the agent
    const history = messages.map(({ role, text }) => ({ role, text }));

    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);
    setError(null);

    try {
      const { reply, products } = await sendToAgent(text, history);
      console.log("[ChatSection] Agent response:", { reply, products });
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: reply, products },
      ]);
    } catch (err) {
      console.error(err);
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="chat-section">
      <ChatInput onSend={handleSend} disabled={loading} />
      {loading && <p>Searching...</p>}
      {error && <p>{error}</p>}
    </section>
  );
}

export default ChatSection;
