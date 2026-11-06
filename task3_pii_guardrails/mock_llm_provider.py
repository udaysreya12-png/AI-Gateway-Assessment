
import asyncio
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Mock LLM Provider")


class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    stream: bool = True


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    async def generate():
        chunks = [
            "Hello! Contact john@",
            "example.com for support. ",
            "SSN: 123-",
            "45-6789. ",
            "Card: 4111 1111 ",
            "1111 1111. ",
            "Thank you!",
        ]

        for text in chunks:
            event = {
                "choices": [
                    {
                        "delta": {
                            "content": text
                        }
                    }
                ]
            }

            yield (
                "data: "
                + json.dumps(event)
                + "\n\n"
            )

            await asyncio.sleep(0.05)

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
