import asyncio
from app.services.llm_service import LLMService

async def test():
    result = ""
    async for chunk in LLMService.stream_response("Say hello in exactly 5 words"):
        result += chunk
    print("RESULT:", result)

asyncio.run(test())
