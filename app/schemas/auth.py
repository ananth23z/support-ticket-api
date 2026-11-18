"""
app/schemas/auth.py
===================
WHAT:  The shape of the login response.
WHY:   OAuth2 (the standard Swagger's "Authorize" button follows) expects the token
       endpoint to return exactly:  {"access_token": "...", "token_type": "bearer"}
"""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
