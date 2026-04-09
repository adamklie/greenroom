from pydantic import BaseModel


class TagRead(BaseModel):
    id: int
    name: str
    category: str
    color: str | None = None
    is_predefined: bool = True

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str
    category: str = "general"
    color: str | None = None
