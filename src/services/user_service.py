"""User service for querying and managing users."""

import hashlib
import hmac
from typing import Optional
from urllib.parse import parse_qsl

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserService:
    """Service for user-related operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    @staticmethod
    def verify_telegram_webapp_signature(init_data: str, bot_token: str) -> Optional[dict]:
        """
        Verify Telegram WebApp init data signature.
        
        Algorithm per https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
        
        Args:
            init_data: The initData string from Telegram.WebApp.initData
            bot_token: Telegram bot token
            
        Returns:
            Parsed data dict if signature is valid, None otherwise
        """
        try:
            # Parse query string
            parsed_data = dict(parse_qsl(init_data))
            
            # Extract hash
            received_hash = parsed_data.pop('hash', None)
            if not received_hash:
                return None
            
            # Create data-check-string (sorted alphabetically by key)
            data_check_arr = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
            data_check_string = '\n'.join(data_check_arr)
            
            # Calculate secret key
            secret_key = hmac.new(
                key=b"WebAppData",
                msg=bot_token.encode(),
                digestmod=hashlib.sha256
            ).digest()
            
            # Calculate hash
            calculated_hash = hmac.new(
                key=secret_key,
                msg=data_check_string.encode(),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            # Compare hashes
            if calculated_hash != received_hash:
                return None
            
            # TODO: Check auth_date is within acceptable time window (±5 minutes)
            # For now, accepting any auth_date
            
            return parsed_data
            
        except Exception:
            return None

    async def get_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        """
        Get user by Telegram ID.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            User if found, None otherwise
        """
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def can_access_mini_app(self, telegram_id: str) -> bool:
        """
        Check if user can access Mini App (PRIMARY access gate).
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if user exists and is_active=True, False otherwise
        """
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None and user.is_active

    async def can_access_invest(self, telegram_id: str) -> bool:
        """
        Check if user can access Invest features.
        
        Requires both is_active=True AND is_investor=True.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if user can access Invest, False otherwise
        """
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None and user.is_active and user.is_investor

    async def is_administrator(self, telegram_id: str) -> bool:
        """
        Check if user is an administrator.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if user is an administrator, False otherwise
        """
        user = await self.get_by_telegram_id(telegram_id)
        return user is not None and user.is_administrator

    async def create_user(
        self,
        telegram_id: str,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        is_active: bool = False,  # Default: not active until approved
    ) -> User:
        """
        Create a new user.
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            is_active: Whether user can access Mini App (default: False)
            
        Returns:
            Created User
        """
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def activate_user(self, telegram_id: str) -> Optional[User]:
        """
        Activate user (set is_active=True).
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            Updated User if found, None otherwise
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.is_active = True
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def deactivate_user(self, telegram_id: str) -> Optional[User]:
        """
        Deactivate user (set is_active=False) - soft delete.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            Updated User if found, None otherwise
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.is_active = False
            await self.session.commit()
            await self.session.refresh(user)
        return user


__all__ = ["UserService"]
