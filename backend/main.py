from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL", "deepseek/deepseek-chat-v3-0324:free")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
TWITTER_CLONE_API_KEY = os.getenv("TWITTER_CLONE_API_KEY", "").strip()
TWITTER_CLONE_POST_ENDPOINT = os.getenv("TWITTER_CLONE_POST_ENDPOINT", "").strip()
TWITTER_CLONE_UI = os.getenv("TWITTER_CLONE_URL", "").strip()

# Extract username from API key
USERNAME = TWITTER_CLONE_API_KEY.split("_")[0] if "_" in TWITTER_CLONE_API_KEY else "guest"

# === FastAPI App Setup ===
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yupcha-cgx.pages.dev/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")

# === Pydantic Models ===
class ChatRequest(BaseModel):
    message: str

class TweetRequest(BaseModel):
    prompt: str
    tone: str = "neutral"

class PostTweetRequest(BaseModel):
    tweet: str

# In-memory tweet history
tweet_history = []

# === /chat endpoint ===
@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Chatbot"
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request.message}
            ]
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()

        if SUPABASE_URL and SUPABASE_KEY:
            await log_to_supabase("chats", {"user_msg": request.message, "bot_reply": reply})

        return {"reply": reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# === /tweet endpoint ===
@app.post("/tweet")
async def generate_tweet(request: TweetRequest):
    try:
        prompt = f"Write a short, {request.tone.lower()} tweet about: {request.prompt}"

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "TweetBot"
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a tweet generator bot."},
                {"role": "user", "content": prompt}
            ]
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            tweet_text = data["choices"][0]["message"]["content"].strip()[:280]

        tweet_history.append({
            "prompt": request.prompt,
            "tone": request.tone,
            "tweet": tweet_text
        })

        if SUPABASE_URL and SUPABASE_KEY:
            await log_to_supabase("tweets", {
                "prompt": request.prompt,
                "tone": request.tone,
                "tweet": tweet_text
            })

        return {"tweet": tweet_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tweet generation error: {str(e)}")

# === /tweet/history endpoint ===
@app.get("/tweet/history")
async def get_tweet_history():
    return {"history": tweet_history}

# === /tweet/post endpoint ===
@app.post("/tweet/post")
async def post_tweet(payload: PostTweetRequest):
    if not TWITTER_CLONE_API_KEY or not TWITTER_CLONE_POST_ENDPOINT:
        raise HTTPException(status_code=400, detail="Missing Twitter clone configuration")

    try:
        post_data = {
            "username": USERNAME,
            "text": payload.tweet.strip()[:280]
        }

        headers = {
            "api-key": TWITTER_CLONE_API_KEY,  # ✅ FIXED: use "api-key" instead of Authorization
            "Content-Type": "application/json"
        }

        print("Posting to:", TWITTER_CLONE_POST_ENDPOINT)
        print("Payload:", post_data)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(TWITTER_CLONE_POST_ENDPOINT, headers=headers, json=post_data)

        if response.status_code != 200:
            print("RESPONSE STATUS:", response.status_code)
            print("RESPONSE TEXT:", response.text)
            raise HTTPException(status_code=422, detail="Twitter clone rejected the post")

        data = response.json()
        tweet_id = data.get("id") or data.get("tweet_id") or ""
        redirect_url = f"{TWITTER_CLONE_UI}/tweet/{tweet_id}" if tweet_id else TWITTER_CLONE_UI

        return {
            "message": "Tweet posted successfully",
            "redirect_url": redirect_url
        }

    except httpx.HTTPStatusError as e:
        print("HTTPStatusError:", e.response.text)
        raise HTTPException(status_code=422, detail="Twitter clone rejected the post")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Posting error: {str(e)}")

# === Optional Supabase Logger ===
async def log_to_supabase(table: str, data: dict):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient() as client:
        await client.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=headers, json=[data])



