import asyncio
import json
import random
from typing import AsyncGenerator
import google.generativeai as genai
from app.config import settings

class LLMService:
  @staticmethod
  async def stream_response(prompt: str, routing: str = "cheap") -> AsyncGenerator[str, None]:
    """
    Streams response content from an LLM provider.
    
    Model Routing:
      - "cheap": fast, low-cost models (llama-3-8b, gemini-2.0-flash, gpt-4o-mini, claude-3-5-haiku)
      - "complex": larger models (llama-3.3-70b, gemini-2.0-flash, gpt-4o, claude-3-5-sonnet)
      
    Provider Priority Chain:
      1. Groq (llama-3.1-8b-instant or llama-3.3-70b-versatile)
      2. Gemini (gemini-2.0-flash)
      3. OpenAI (gpt-4o-mini or gpt-4o)
      4. Anthropic/Claude (claude-3-5-haiku or claude-3-5-sonnet)
      5. Mock fallback (word-by-word stream)
      
    Features:
      - Exponential backoff + jitter retries on transient connection errors
      - Automatic failover to next provider if all retries of the current provider fail
    """
    # 1. Try Groq
    groq_key = settings.GROQ_API_KEY.strip()
    if groq_key and "YOUR_GROQ_API_KEY" not in groq_key:
      models_to_try = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"] if routing != "cheap" else ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"]
      for model_name in models_to_try:
        print(f"LLMService: Trying Groq ({model_name})...")
        try:
          got_data = False
          async for token in LLMService._stream_groq(prompt, model_name, groq_key):
            got_data = True
            yield token
          if got_data:
            return
        except Exception as e:
          print(f"LLMService: Groq ({model_name}) failed ({type(e).__name__}: {e}).")

    # 2. Try Gemini
    gemini_key = settings.GEMINI_API_KEY.strip()
    if gemini_key and "YOUR_GEMINI_API_KEY" not in gemini_key:
      for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
        print(f"LLMService: Trying Gemini ({model_name})...")
        try:
          got_data = False
          async for token in LLMService._stream_gemini(prompt, model_name, gemini_key):
            got_data = True
            yield token
          if got_data:
            return
        except Exception as e:
          print(f"LLMService: Gemini ({model_name}) failed ({type(e).__name__}: {e}).")

    # 3. Try OpenAI
    openai_key = settings.OPENAI_API_KEY.strip() if hasattr(settings, "OPENAI_API_KEY") else ""
    if openai_key and "YOUR_OPENAI_API_KEY" not in openai_key:
      model_name = "gpt-4o-mini" if routing == "cheap" else "gpt-4o"
      print(f"LLMService: Trying OpenAI ({model_name})...")
      
      try:
        async for token in LLMService._stream_openai(prompt, model_name, openai_key):
          yield token
        return
      except Exception as e:
        print(f"LLMService: OpenAI failed ({type(e).__name__}: {e}). Trying Claude fallback...")

    # 4. Try Claude (Anthropic)
    claude_key = settings.CLAUDE_API_KEY.strip() if hasattr(settings, "CLAUDE_API_KEY") else ""
    if claude_key and "YOUR_CLAUDE_API_KEY" not in claude_key:
      model_name = "claude-3-5-haiku" if routing == "cheap" else "claude-3-5-sonnet"
      print(f"LLMService: Trying Claude ({model_name})...")
      
      try:
        async for token in LLMService._stream_claude(prompt, model_name, claude_key):
          yield token
        return
      except Exception as e:
        print(f"LLMService: Claude failed ({type(e).__name__}: {e}).")

    # 5. Mock Fallback
    print("LLMService: [Warning] No working LLM provider. Generating mock stream.")
    mock_response = (
      "This is a mock response because no LLM provider is currently available. "
      "Please check that your API keys in the .env file are active and valid."
    )
    for word in mock_response.split(" "):
      yield word + " "
      await asyncio.sleep(0.03)

  @staticmethod
  async def _stream_groq(prompt: str, model: str, key: str) -> AsyncGenerator[str, None]:
    import httpx
    max_retries = 3
    for attempt in range(max_retries):
      try:
        async with httpx.AsyncClient(timeout=60.0) as client:
          async with client.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
              "Authorization": f"Bearer {key}",
              "Content-Type": "application/json"
            },
            json={
              "model": model,
              "messages": [{"role": "user", "content": prompt}],
              "stream": True
            }
          ) as response:
            if response.status_code == 200:
              async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                  continue
                if line.startswith("data: "):
                  data_str = line[6:]
                  if data_str == "[DONE]":
                    break
                  try:
                    data = json.loads(data_str)
                    delta = data["choices"][0]["delta"]
                    if "content" in delta:
                      yield delta["content"]
                  except Exception:
                    pass
              return
            else:
              raise httpx.HTTPStatusError(
                f"Groq returned HTTP {response.status_code}", 
                request=None, 
                response=response
              )
      except Exception as e:
        if attempt == max_retries - 1:
          raise e
        delay = 1.0 * (2 ** attempt) + random.uniform(0, 0.5)
        print(f"LLMService: Groq attempt {attempt + 1} failed. Retrying in {delay:.2f}s...")
        await asyncio.sleep(delay)

  @staticmethod
  async def _stream_openai(prompt: str, model: str, key: str) -> AsyncGenerator[str, None]:
    import httpx
    max_retries = 3
    for attempt in range(max_retries):
      try:
        async with httpx.AsyncClient(timeout=60.0) as client:
          async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={
              "Authorization": f"Bearer {key}",
              "Content-Type": "application/json"
            },
            json={
              "model": model,
              "messages": [{"role": "user", "content": prompt}],
              "stream": True
            }
          ) as response:
            if response.status_code == 200:
              async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                  continue
                if line.startswith("data: "):
                  data_str = line[6:]
                  if data_str == "[DONE]":
                    break
                  try:
                    data = json.loads(data_str)
                    delta = data["choices"][0]["delta"]
                    if "content" in delta:
                      yield delta["content"]
                  except Exception:
                    pass
              return
            else:
              raise httpx.HTTPStatusError(
                f"OpenAI returned HTTP {response.status_code}", 
                request=None, 
                response=response
              )
      except Exception as e:
        if attempt == max_retries - 1:
          raise e
        delay = 1.0 * (2 ** attempt) + random.uniform(0, 0.5)
        print(f"LLMService: OpenAI attempt {attempt + 1} failed. Retrying in {delay:.2f}s...")
        await asyncio.sleep(delay)

  @staticmethod
  async def _stream_claude(prompt: str, model: str, key: str) -> AsyncGenerator[str, None]:
    import httpx
    max_retries = 3
    for attempt in range(max_retries):
      try:
        async with httpx.AsyncClient(timeout=60.0) as client:
          async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
              "x-api-key": key,
              "anthropic-version": "2023-06-01",
              "content-type": "application/json"
            },
            json={
              "model": model,
              "max_tokens": 4000,
              "messages": [{"role": "user", "content": prompt}],
              "stream": True
            }
          ) as response:
            if response.status_code == 200:
              async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                  continue
                if line.startswith("data: "):
                  data_str = line[6:]
                  try:
                    data = json.loads(data_str)
                    if data.get("type") == "content_block_delta":
                      delta = data.get("delta", {})
                      if delta.get("type") == "text_delta" and "text" in delta:
                        yield delta["text"]
                  except Exception:
                    pass
              return
            else:
              raise httpx.HTTPStatusError(
                f"Claude returned HTTP {response.status_code}", 
                request=None, 
                response=response
              )
      except Exception as e:
        if attempt == max_retries - 1:
          raise e
        delay = 1.0 * (2 ** attempt) + random.uniform(0, 0.5)
        print(f"LLMService: Claude attempt {attempt + 1} failed. Retrying in {delay:.2f}s...")
        await asyncio.sleep(delay)

  @staticmethod
  async def _stream_gemini(prompt: str, model_name: str, key: str) -> AsyncGenerator[str, None]:
    max_retries = 3
    for attempt in range(max_retries):
      try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
          None,
          lambda: model.generate_content(prompt, stream=True)
        )
        
        chunk_count = 0
        for chunk in response:
          if chunk.text:
            chunk_count += 1
            yield chunk.text
        return
      except Exception as e:
        if attempt == max_retries - 1:
          raise e
        delay = 1.0 * (2 ** attempt) + random.uniform(0, 0.5)
        print(f"LLMService: Gemini attempt {attempt + 1} failed. Retrying in {delay:.2f}s...")
        await asyncio.sleep(delay)
