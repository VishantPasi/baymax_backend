# import httpx
# import os

# from dotenv import load_dotenv

# load_dotenv()


# class LLMService:

#     OLLAMA_BASE_URL = os.getenv(
#         "OLLAMA_BASE_URL",
#         "http://127.0.0.1:11434"
#     )

#     MODEL = os.getenv(
#         "LLM_MODEL",
#         "llama3.2:3b"
#     )

#     @classmethod
#     async def generate_response(
#         cls,
#         messages: list[dict]
#     ) -> str:

#         payload = {
#             "model": cls.MODEL,
#             "messages": messages,
#             "stream": False
#         }

#         try:
#             async with httpx.AsyncClient(
#                 timeout=120.0
#             ) as client:

#                 response = await client.post(
#                     f"{cls.OLLAMA_BASE_URL}/api/chat",
#                     json=payload
#                 )

#                 response.raise_for_status()

#                 data = response.json()

#                 return data["message"]["content"]

#         except httpx.TimeoutException:
#             raise Exception(
#                 "Ollama request timed out"
#             )

#         except httpx.HTTPStatusError as e:
#             raise Exception(
#                 f"Ollama returned HTTP {e.response.status_code}"
#             )

#         except Exception as e:
#             raise Exception(
#                 f"LLM service error: {str(e)}"
#             )



import httpx
import json
import os

from dotenv import load_dotenv

load_dotenv()


class LLMService:

    OLLAMA_BASE_URL = os.getenv(
        "OLLAMA_BASE_URL",
        "http://127.0.0.1:11434"
    )

    MODEL = os.getenv(
        "LLM_MODEL",
        "llama3.2:3b"
    )

    @classmethod
    async def generate_stream(
        cls,
        messages: list[dict]
    ):

        payload = {
            "model": cls.MODEL,
            "messages": messages,
            "stream": True
        }

        try:

            async with httpx.AsyncClient(
                timeout=None
            ) as client:

                async with client.stream(
                    "POST",
                    f"{cls.OLLAMA_BASE_URL}/api/chat",
                    json=payload
                ) as response:

                    response.raise_for_status()

                    async for line in response.aiter_lines():

                        if not line:
                            continue

                        data = json.loads(line)

                        message = data.get("message", {})
                        content = message.get("content", "")

                        if content:
                            yield content

                        if data.get("done", False):
                            break

        except httpx.ConnectError:
            raise Exception(
                "Unable to connect to Ollama"
            )

        except httpx.TimeoutException:
            raise Exception(
                "Ollama request timed out"
            )

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Ollama returned HTTP {e.response.status_code}"
            )

        except Exception as e:
            raise Exception(
                f"LLM service error: {str(e)}"
            )

