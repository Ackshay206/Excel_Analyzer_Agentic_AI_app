from pydantic import BaseModel, Field, validator
from typing import Optional

class BillingQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The query to analyze billing data")
    file_name: Optional[str] = Field(None, description="Name of the Excel file to analyze")
    username: str = Field(..., description="Username for the session")

    @validator('username')
    def username_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()


class SetApiKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=20, description="OpenAI API key starting with 'sk-'")
    username: str = Field(..., description="Username for the session")

    @validator('username')
    def username_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        return v.strip()

    @validator('api_key')
    def api_key_must_be_valid(cls, v):
        if not v.startswith('sk-'):
            raise ValueError('API key must start with sk-')
        return v