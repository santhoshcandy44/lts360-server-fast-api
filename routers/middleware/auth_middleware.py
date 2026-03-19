from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from config import ACCESS_TOKEN_SECRET, ALGORITHM   

bearer_scheme = HTTPBearer()

async def authenticate_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials
 
    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token access denied")
 
    user_id      = payload.get("userId")
    last_sign_in = payload.get("lastSignIn")
 
    if not user_id:
        raise HTTPException(status_code=401, detail="No valid token access denied")
 
    existing_user = await get_user_by_id(user_id)  
    if not existing_user:
        raise HTTPException(status_code=401, detail="User not exist access denied")
 
    if last_sign_in != str(existing_user["last_sign_in"]):
        raise HTTPException(status_code=498, detail="Invalid session")
 
    request.state.user = existing_user
    return existing_user