from sqlalchemy.orm import Session
from typing import Union
from .base import BaseRepository
from ..models import User


class UserRepository(BaseRepository[User]):
    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_username(self, username: str) -> Union[User, None]:
        return self.db.query(User).filter(User.username == username).first()

    def get_or_create_default_user(self) -> User:
        user = self.get_by_username("default_user")
        if not user:
            user = self.create(username="default_user")
        return user
