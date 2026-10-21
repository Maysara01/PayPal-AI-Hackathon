
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ollama_service import OllamaService
from app.services.product_service import ProductService

router = APIRouter()

ollama = OllamaService()
products_service = ProductService()


class AgentRequest(BaseModel):
    sessionId: str
    query: str = Field(min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


@router.post("/agent")
def send_to_agent(request: AgentRequest):
    try:
        products = products_service.search(request.query)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a shopping assistant for a demo catalog. "
                    "Recommend only products supplied in the catalog. "
                    "Never invent product prices or specifications. "
                    "Explain that the catalog is for demonstration only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User request: {request.query}\n"
                    f"Available products: {products}\n"
                    "Briefly explain which products match the request."
                ),
            },
        ]

        # Only accept recognized conversation roles and text content.
        for item in request.history[-8:]:
            if (
                isinstance(item, dict)
                and item.get("role") in {"user", "assistant"}
                and isinstance(item.get("content"), str)
            ):
                messages.insert(
                    -1,
                    {
                        "role": item["role"],
                        "content": item["content"][:2000],
                    },
                )

        reply = ollama.chat(messages)

        return {
            "reply": reply,
            "products": products,
        }

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
