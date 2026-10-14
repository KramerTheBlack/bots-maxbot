#!/usr/bin/env python3
"""
MAX Messenger Bot with Mistral AI integration
"""

import asyncio
import configparser
import json
import os
import sys
from pathlib import Path
from typing import Optional

import aiohttp

# Global configuration
config = configparser.ConfigParser()
MAX_TOKEN: Optional[str] = None
MISTRAL_API_KEY: Optional[str] = None
LLM_ADD: Optional[str] = None
CONFIG_LOADED: bool = False


async def load_config(config_path: str = "/app/config/bot.conf") -> None:
    """Load configuration from bot.conf"""
    global MAX_TOKEN, MISTRAL_API_KEY, LLM_ADD, CONFIG_LOADED
    
    config_path_obj = Path(config_path)
    if not config_path_obj.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    config.read(config_path)
    
    # Read token from file
    token_file = config.get("DEFAULT", "token_file", fallback="/app/config/token.txt")
    token_file_path = Path(token_file)
    if not token_file_path.exists():
        print(f"ERROR: Token file not found: {token_file}")
        sys.exit(1)
    
    with open(token_file_path, "r") as f:
        MAX_TOKEN = f.read().strip()
    
    MISTRAL_API_KEY = config.get("DEFAULT", "mistral_api_key", fallback="")
    LLM_ADD = config.get("DEFAULT", "LLMADD", fallback="")
    CONFIG_LOADED = True
    
    print(f"Configuration loaded:")
    print(f"  MAX Token: {'*' * len(MAX_TOKEN) if MAX_TOKEN else 'NOT SET'}")
    print(f"  Mistral API Key: {'*' * len(MISTRAL_API_KEY) if MISTRAL_API_KEY else 'NOT SET'}")
    print(f"  LLM ADD: {LLM_ADD[:50] + '...' if len(LLM_ADD) > 50 else LLM_ADD}")


async def call_mistral(prompt: str) -> str:
    """Call Mistral AI API"""
    url = "https://api.mistral.ai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # Add LLMADD to prompt if available
    if LLM_ADD:
        full_prompt = f"{LLM_ADD}\n\nПользователь: {prompt}"
    else:
        full_prompt = prompt
    
    payload = {
        "model": "mistral-tiny",
        "messages": [
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500,  # Уменьçus с 2000 до 500 для скорости
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_data = await response.text()
                    print(f"ERROR: Mistral API returned {response.status}: {error_data}")
                    return "Извините, произошла ошибка при обращении к AI."
    except Exception as e:
        print(f"ERROR: Failed to call Mistral API: {e}")
        return "Извините, не удалось получить ответ от AI."


async def send_message(chat_id: int, text: str) -> bool:
    """Send message to MAX chat"""
    url = f"https://botapi.max.ru/messages"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": MAX_TOKEN,  # MAX Bot API expects raw token without "Bearer"
    }
    params = {
        "chat_id": chat_id,
    }
    
    payload = {"text": text}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, params=params, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return True
                else:
                    error_data = await response.text()
                    print(f"ERROR: Failed to send message to chat {chat_id}: {response.status} - {error_data}")
                    return False
    except Exception as e:
        print(f"ERROR: Failed to send message: {e}")
        return False


async def get_updates(marker: int = 0) -> tuple[list, int]:
    """Get updates from MAX Bot API"""
    url = "https://botapi.max.ru/updates"
    
    if not MAX_TOKEN:
        print("ERROR: MAX_TOKEN is empty in get_updates")
        return [], marker
    
    headers = {
        "Authorization": MAX_TOKEN,  # MAX Bot API expects raw token without "Bearer"
    }
    params = {
        "marker": marker,
        "timeout": 10,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    updates = data.get("updates", [])
                    new_marker = data.get("marker", marker)
                    return updates, new_marker
                else:
                    error_data = await response.text()
                    print(f"ERROR: Failed to get updates: {response.status} - {error_data}")
                    return [], marker
    except asyncio.TimeoutError:
        print("ERROR: get_updates timeout - server not responding in time")
        return [], marker
    except aiohttp.ClientError as e:
        print(f"ERROR: get_updates network error: {type(e).__name__}: {e}")
        return [], marker
    except Exception as e:
        print(f"ERROR: Failed to get updates: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return [], marker


async def process_update(update: dict) -> None:
    """Process a single update"""
    # MAX API uses "update_type" field, not "type"
    update_type = update.get("update_type")
    
    if update_type == "message_created":
        message = update.get("message", {})
        body = message.get("body", {})
        text = body.get("text", "").strip()
        
        # Get chat info
        recipient = message.get("recipient", {})
        chat_id = recipient.get("chat_id")
        chat_type = recipient.get("chat_type", "unknown")  # Changed from "type" to "chat_type"
        
        # Get sender info
        sender = message.get("sender", {})
        user_id = sender.get("user_id")
        is_bot = sender.get("is_bot", False)
        
        # Skip messages from bot itself
        if is_bot:
            return
        
        # Skip empty messages
        if not text:
            return
        
        print(f"Received message in {chat_type} {chat_id} from {user_id}: {text[:100]}")
        
        # Process message and call Mistral AI
        try:
            response = await call_mistral(text)
            await send_message(chat_id, response)
        except Exception as e:
            print(f"ERROR in processing message: {type(e).__name__}: {e}")
    
    elif update_type == "bot_added":
        chat = update.get("chat", {})
        chat_id = chat.get("chat_id")
        title = chat.get("title", "Unknown")
        print(f"Bot was added to chat: {title} (ID: {chat_id})")


async def main():
    """Main bot loop"""
    # Load configuration
    await load_config()
    
    if not MAX_TOKEN:
        print("ERROR: MAX_TOKEN is not set")
        sys.exit(1)
    
    if not MISTRAL_API_KEY:
        print("ERROR: MISTRAL_API_KEY is not set")
        sys.exit(1)
    
    print("\n=== MAX Bot with Mistral AI ===")
    print("Starting bot...\n")
    
    # Test MAX token
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://botapi.max.ru/me",
                headers={"Authorization": MAX_TOKEN},  # MAX Bot API expects raw token without "Bearer"
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    bot_info = await response.json()
                    print(f"Bot info: {json.dumps(bot_info, indent=2, ensure_ascii=False)}")
                else:
                    error_data = await response.text()
                    print(f"WARNING: Failed to get bot info: {response.status} - {error_data}")
    except Exception as e:
        print(f"WARNING: Failed to verify token: {e}")
    
    # Main polling loop
    marker = 0
    while True:
        try:
            updates, new_marker = await get_updates(marker)
            
            if updates:
                for update in updates:
                    await process_update(update)
            
            if new_marker:
                marker = new_marker
            
            # No delay - long polling handles timing
            # await asyncio.sleep(0.01)
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"ERROR in main loop: {e}")
            await asyncio.sleep(5)





if __name__ == "__main__":
    asyncio.run(main())
