from jose import jwt
from jose.exceptions import JWTError
from fastapi import Request, HTTPException, status, Depends
from typing import Dict
import httpx
import os

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
API_IDENTIFIER = "http://localhost:8000"
ALGORITHMS = ["RS256"]

# Get JWKS on startup
async def get_jwks():
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()["keys"]

jwks_cache = None

async def get_token_auth_header(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return auth.split(" ")[1]

async def verify_jwt_token(request: Request) -> Dict:
    global jwks_cache
    token = await get_token_auth_header(request)

    if jwks_cache is None:
        jwks_cache = await get_jwks()

    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}

    for key in jwks_cache:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }

    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_IDENTIFIER,
                issuer=f"https://{AUTH0_DOMAIN}/",
            )
            return payload
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    raise HTTPException(status_code=401, detail="Unable to find appropriate key")
