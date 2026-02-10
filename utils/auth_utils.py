import logging
import time
from typing import Any, Dict

import jwt
from fastapi import HTTPException, status
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import os
import aiohttp
logger = logging.getLogger()


class AuthValidator(HTTPBearer):
    def __init__(self, api=None, auto_error: bool = True):
        super(AuthValidator, self).__init__(auto_error=auto_error)
        self.api = api

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(AuthValidator, self).__call__(request)
        token = None

        if credentials and credentials.scheme == "Bearer":
            token = credentials.credentials
        elif 'token' in request.path_params:
            token = request.path_params['token']
        
        if token:
            if not await AuthValidator.valid_token(token):
                raise HTTPException(status_code=403, detail="Invalid token or expired token.")
            user_model = await AuthValidator.get_user_model(token)
            if not await AuthValidator.user_has_access_to_api(str(user_model['sub']), self.api):
                raise HTTPException(status_code=403, detail="User doesn't have access to this API")
            return user_model
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

    @staticmethod
    async def get_user_model(token: str) -> Dict[str, Any]:
        # TODO Verify JWT token and check Redis for revocation
        secret_key = os.getenv('SECRET_KEY')
        algorithm = os.getenv('ALGORITHM')
        if not secret_key or not algorithm:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Missing JWT configuration"
            )
        try:
            payload: dict = jwt.decode(
                token, secret_key, algorithms=[algorithm]
            )
            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    @staticmethod
    async def valid_token(auth_token: str):
        user = await AuthValidator.get_user_model(auth_token)
        token_expiry_time = user['exp']
        time_now = int(time.time())
        logger.info(f'Auth token expiry time - {token_expiry_time}')
        logger.info(f'Current time - {token_expiry_time}')
        return time_now <= token_expiry_time

    # TODO the below functions needs to be optimized to get the data from cache and not from API for every call.
    @staticmethod
    async def validate_user_api_permission(permissions_for_the_user):
        permissions = permissions_for_the_user['data']
        response = True
        return response
    
    @staticmethod
    async def check_user_permission_in_redis(user_id, api):
        import os
        import aioredis

        logger.info(f'Checking user details in cache started')
        REDIS_URL = os.getenv("REDIS_HOST")
        REDIS_PORT = int(os.getenv("REDIS_PORT"))
        redis = aioredis.Redis(host=REDIS_URL, port=REDIS_PORT, decode_responses=True)
        try:
            await redis.ping()
            logger.info(f"Getting user permissions from Redis cache")
            permissions_len = await redis.llen(user_id)
            user_permissions = await redis.lrange(user_id, 0, permissions_len - 1 )
            if api in user_permissions:
                logger.info(f'User have access to - {api} - api')
                return True
        except aioredis.exceptions.ConnectionError as e:
            logger.info(f"Redis connection failed: {e} - Checking user details in Access Manager API")
            return False
        
    @staticmethod
    async def check_user_permission_in_access_manage_api(user_id, api):
        async def fetch(session, url):
            async with session.get(url) as response:
                return await response.json()
        logger.info(f"Getting user permissions from Access Manager API")
        async with aiohttp.ClientSession() as session:
            access_check_url = f"{os.getenv('DEPLOYMENT_MANAGER_URL')}/v1/auth/module_access/{user_id}/{api}"
            access_response = await fetch(session, access_check_url)
            logger.info(f"User permission response from API: {access_response}")
            user_has_access = access_response.get('has_access', False)
            logger.info(f'Checking user details in Access Manager API ended')
        return user_has_access

    @staticmethod
    async def user_has_access_to_api(user_id, api):
        try:
            user_has_access = False
            user_has_access = await AuthValidator.check_user_permission_in_redis(user_id, api)
            if not user_has_access:
                user_has_access = await AuthValidator.check_user_permission_in_access_manage_api(user_id, api)
            logger.info(f'Checking user details in Access Manager API ended')
            return user_has_access
        except Exception as exception:
            logger.error(f'Error getting user permissions from redis cache - {exception}')
            return False


class DualAuthValidator:
    """
    Simple dual authentication validator that supports both Bearer token and Basic Authentication
    """
    def __init__(self, api=None, auto_error: bool = True):
        self.api = api
        self.auto_error = auto_error
        self.bearer_auth = HTTPBearer(auto_error=False)
        self.basic_auth = HTTPBasic(auto_error=False)

    async def __call__(self, request: Request):
        # Try Bearer token authentication first (for browsers)
        logger.info(f"request in dual auth validator: {request}")
        try:
            credentials: HTTPAuthorizationCredentials = await self.bearer_auth(request)
            if credentials and credentials.scheme == "Bearer":
                token = credentials.credentials
                if token:
                    if not await AuthValidator.valid_token(token):
                        raise HTTPException(status_code=403, detail="Invalid token or expired token.")
                    user_model = await AuthValidator.get_user_model(token)
                    if not await AuthValidator.user_has_access_to_api(str(user_model['sub']), self.api):
                        raise HTTPException(status_code=403, detail="User doesn't have access to this API")
                    return user_model
        except HTTPException:
            logger.info(f"Bearer auth failed")
            pass  # Continue to Basic Auth if Bearer fails

        # Try Basic Authentication (for Mule devices)
        try:
            logger.info(f"Trying basic auth")
            credentials: HTTPBasicCredentials = await self.basic_auth(request)
            if credentials:
                username = credentials.username
                password = credentials.password
                logger.info(f"Username: {username}, Password: {password}")
                # Validate against local password file
                if await self._validate_basic_auth(username, password):
                    logger.info(f"Basic auth successful")
                    user_model = {
                        "sub": username,
                        "user_name": username,
                        "role": "static_access",
                        "auth_method": "basic"
                    }
                    logger.info(f"User model: {user_model}")
                    return user_model
        except HTTPException:
            logger.info(f"Basic auth failed")
            pass

        # If both authentication methods fail
        if self.auto_error:
            raise HTTPException(status_code=401, detail="Invalid authorization credentials")
        return None

    @staticmethod
    async def _validate_basic_auth(username: str, password: str) -> bool:
        """
        Validate Basic Authentication against local password file
        """
        logger.info(f"Validating basic auth for user: {username}")
        try:
            # Path to the password file (same format as nginx htpasswd)
            password_file = os.getenv("STATIC_AUTH_FILE", "/app/misc/nginx.htpasswd")
            logger.info(f"Password file: {password_file}")
            if not os.path.exists(password_file):
                logger.info(f"Password file not found: {password_file}")
                return False
            
            with open(password_file, 'r') as f:
                logger.info(f"Reading password file")
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        stored_username, stored_hash = line.split(':', 1)
                        if username == stored_username:
                            logger.info(f"Username: {username}, Stored username: {stored_username}")
                            # Validate password against stored hash
                            if DualAuthValidator._check_password(password, stored_hash):
                                logger.info(f"Basic auth successful for user: {username}")
                                return True
                            else:
                                logger.info(f"Invalid password for user: {username}")
                                return False
            
            logger.info(f"User not found: {username}")
            return False
            
        except Exception as e:
            logger.info(f"Error validating basic auth: {e}")
            return False

    @staticmethod
    def _check_password(password: str, stored_hash: str) -> bool:
        """
        Check password against stored hash (supports Apache htpasswd format)
        """
        logger.info(f"Checking password against stored hash: {stored_hash[:10]}...")
        try:
            # Handle different hash formats
            if stored_hash.startswith('$apr1$'):
                logger.info(f"Apache MD5 format detected")
                # Apache MD5 format - use passlib for verification
                from passlib.hash import apr_md5_crypt
                return apr_md5_crypt.verify(password, stored_hash)
                        
        except Exception as e:
            logger.error(f"Error checking password: {e}")
            return False


async def websocket_token_auth(token: str):
    try:
        secret_key = os.getenv('SECRET_KEY')
        algorithm = os.getenv('ALGORITHM')
        if not secret_key or not algorithm:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Missing JWT configuration"
            )
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")