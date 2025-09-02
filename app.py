import chainlit as cl
import aiohttp
import os
import json

GPU_URL = os.getenv("GPU_URL", "http://localhost:11434/api/chat")

IS_OLLAMA = "localhost:11434" in GPU_URL

@cl.on_message
async def on_message(message: cl.Message):
    msg = cl.Message(content="")
    await msg.send()

    model_name = "gemma3:latest" if IS_OLLAMA else "google/gemma-3-7b"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": message.content}],
        "stream": True,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GPU_URL, json=payload) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    msg.content = f"Error: {resp.status} - {error_text}"
                    await msg.update()
                    return

                async for line in resp.content:
                    if not line:
                        continue
                    
                    if IS_OLLAMA:
                        data = json.loads(line.decode("utf-8"))
                        
                        if "message" in data:
                            token = data["message"]["content"]
                            await msg.stream_token(token)

                        if data.get("done"):
                            break
                    else:
                        text = line.decode("utf-8").strip()
                        if text.startswith("data: "):
                            data_str = text[len("data: "):]
                            if data_str == "[DONE]":
                                break
                            delta = json.loads(data_str)
                            token = delta["choices"][0]["delta"].get("content", "")
                            if token:
                                await msg.stream_token(token)

    except Exception as e:
        msg.content = f"An unexpected error occurred: {e}"
    
    await msg.update()