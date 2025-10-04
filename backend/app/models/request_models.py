from pydantic import BaseModel,Field
from typing import Optional

#Query Request Model
class BillingQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    file_name: Optional[str] = Field(None)
    session_id : Optional[str] = Field("default", description="Session identifier")


class SetApiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=20)
    session_id : Optional[str] = Field("default", description="Session identifier")