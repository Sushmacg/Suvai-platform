from typing import Annotated

from pydantic import BaseModel, StringConstraints

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ChatRequest(BaseModel):
    question: Question


class ChatResponse(BaseModel):
    answer: str