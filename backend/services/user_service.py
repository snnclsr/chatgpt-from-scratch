from sqlalchemy.orm import Session
from typing import Union
from ..repositories.user import UserRepository
from ..models import User


class UserService:
    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def get_user(self, user_id: int) -> Union[User, None]:
        return self.repository.get(user_id)

    def get_or_create_default_user(self) -> User:
        return self.repository.get_or_create_default_user()

    def create_user(self, username: str) -> User:
        return self.repository.create(username=username)

    def get_by_username(self, username: str) -> Union[User, None]:
        return self.repository.get_by_username(username)
