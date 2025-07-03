/* @jsxImportSource solid-js */
import { createSignal, onCleanup, For, createEffect } from "solid-js";
import { render } from "solid-js/web";

const API_BASE = import.meta.env.VITE_API_BASE_URL;

function App() {
  const [dark, setDark] = createSignal(false);
  const [chatInput, setChatInput] = createSignal("");
  const [chatMessages, setChatMessages] = createSignal([
    { sender: "bot", text: "🤖 Hello! How can I assist you today?" }
  ]);
  const [tweetPrompt, setTweetPrompt] = createSignal("");
  const [tweetTone, setTweetTone] = createSignal("");
  const [generatedTweet, setGeneratedTweet] = createSignal("");
  const [tweetHistory, setTweetHistory] = createSignal([]);
  const [editingTweet, setEditingTweet] = createSignal("");
  const [isSendingChat, setIsSendingChat] = createSignal(false);
  const [isGeneratingTweet, setIsGeneratingTweet] = createSignal(false);
  const [isBotTyping, setIsBotTyping] = createSignal(false);

  let chatEndRef;

  const toggleTheme = () => setDark(!dark());

  const sendChat = async () => {
    const message = chatInput().trim();
    if (!message || isSendingChat()) return;

    setIsSendingChat(true);
    setIsBotTyping(true);
    setChatMessages(prev => [...prev, { sender: "user", text: message }]);
    setChatInput("");

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message })
      });
      const data = await res.json();
      setChatMessages(prev => [...prev, { sender: "bot", text: data.reply }]);
    } catch (e) {
      setChatMessages(prev => [...prev, { sender: "bot", text: "❌ Error getting response." }]);
    } finally {
      setIsSendingChat(false);
      setIsBotTyping(false);
    }
  };

  const generateTweet = async () => {
    const prompt = tweetPrompt().trim();
    const tone = tweetTone().trim();
    if (!prompt || !tone || isGeneratingTweet()) return;

    setIsGeneratingTweet(true);
    setGeneratedTweet("Generating...");

    try {
      const res = await fetch(`${API_BASE}/tweet`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, tone })
      });
      const data = await res.json();

      setGeneratedTweet(data.tweet);
      fetchTweetHistory();
    } catch (e) {
      setGeneratedTweet("❌ Error generating tweet.");
    } finally {
      setIsGeneratingTweet(false);
    }
  };

  const fetchTweetHistory = async () => {
    const res = await fetch(`${API_BASE}/tweet/history`);
    const data = await res.json();
    setTweetHistory(data.history || []);
  };

  const postTweet = async (tweet) => {
    const res = await fetch(`${API_BASE}/tweet/post`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tweet })
    });
    const data = await res.json();
    if (data.redirect_url) window.open(data.redirect_url, "_blank");
  };

  createEffect(() => {
    chatEndRef?.scrollIntoView({ behavior: "smooth" });
  });

  return (
    <div class={`container ${dark() ? "dark" : ""}`}>
      <div class="theme-toggle" onClick={toggleTheme}>
        {dark() ? "🌙 Dark" : "☀️ Light"}
      </div>

      <div class="section">
        {/* Chat Section */}
        <div class="card">
          <h2>💬 Chatbot</h2>
          <div class="chat-box">
            <For each={chatMessages()}>
              {(msg) => (
                <div class={`chat-msg ${msg.sender}`}>
                  {msg.text}
                </div>
              )}
            </For>
            {isBotTyping() && (
              <div class="chat-msg bot typing">Bot is typing...</div>
            )}
            <div ref={chatEndRef}></div>
          </div>
          <div class="input-row">
            <input
              value={chatInput()}
              onInput={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendChat()}
              placeholder="Type your message..."
              disabled={isSendingChat()}
            />
            <button onClick={sendChat} disabled={isSendingChat()}>
              {isSendingChat() ? "Sending..." : "Send"}
            </button>
          </div>
        </div>

        {/* Tweet Section */}
        <div class="card">
          <h2>🐦 Tweet Generator</h2>
          <input
            placeholder="Prompt"
            value={tweetPrompt()}
            onInput={(e) => setTweetPrompt(e.target.value)}
          />
          <input
            placeholder="Tone (e.g. sarcastic, wise, funny)"
            value={tweetTone()}
            onInput={(e) => setTweetTone(e.target.value)}
          />
          <button onClick={generateTweet} disabled={isGeneratingTweet()}>
            {isGeneratingTweet() ? "Generating..." : "Generate"}
          </button>
          <div class="tweet-result">{generatedTweet()}</div>

          <h3>📜 History</h3>
          <For each={tweetHistory()}>
            {(item) => (
              <div class="history-card">
                <p>{item.tweet}</p>
                <input
                  value={item.tweet}
                  onInput={(e) => setEditingTweet(e.target.value)}
                />
                <button onClick={() => postTweet(editingTweet() || item.tweet)}>
                  Post
                </button>
              </div>
            )}
          </For>
        </div>
      </div>
    </div>
  );
}

render(() => <App />, document.getElementById("root"));

