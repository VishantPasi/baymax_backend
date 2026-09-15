
import asyncio

from app.services.llm_service import LLMService


async def main():

    messages = [
        {
            "role": "user",
            "content": "What is artificial intelligence?"
        }
    ]

    response = await LLMService.generate_response(messages)

    print("\nAI RESPONSE:\n")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())

