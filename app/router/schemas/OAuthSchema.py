from pydantic import BaseModel, ConfigDict, Field


class OAuthBaseModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class OAuthExchangeCodeRequest(OAuthBaseModel):
    """Request to exchange authorization code for token."""
    code: str = Field(..., description='Authorization code from OAuth callback')


class OAuthTokenResponse(OAuthBaseModel):
    """Token response after code exchange."""
    access_token: str
    token_type: str = 'bearer'
    expires_in: int
