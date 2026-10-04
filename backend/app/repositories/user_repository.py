from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.preference import UserPreference
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling User entity persistence and Firebase UID synchronization."""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(joinedload(User.preference))
            .where(User.email == email)
        )
        return self.db.scalars(stmt).first()

    def get_by_firebase_uid(self, firebase_uid: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(joinedload(User.preference))
            .where(User.firebase_uid == firebase_uid)
        )
        return self.db.scalars(stmt).first()

    def get_with_preference(self, user_id) -> Optional[User]:
        stmt = (
            select(User)
            .options(joinedload(User.preference))
            .where(User.id == user_id)
        )
        return self.db.scalars(stmt).first()

    def get_or_create_by_firebase_uid(
        self,
        firebase_uid: str,
        email: str,
        name: Optional[str] = None,
        profile_image: Optional[str] = None,
    ) -> User:
        """
        Synchronizes a Firebase authenticated user with the PostgreSQL database.
        Adheres to non-destructive profile synchronization:
        - If existing: updates email if changed, only fills name/image if empty.
        - If new: creates user and initializes default travel preferences.
        """
        user = self.get_by_firebase_uid(firebase_uid)
        if user:
            # Sync email if updated in Firebase
            if email and user.email != email:
                user.email = email
            # Do not overwrite user-customized profile unless previously unset
            if not user.name and name:
                user.name = name
            if not user.profile_image and profile_image:
                user.profile_image = profile_image
            self.db.commit()
            self.db.refresh(user)
            return user

        # Check if an existing account has the same email
        user_by_email = self.get_by_email(email)
        if user_by_email:
            user_by_email.firebase_uid = firebase_uid
            if not user_by_email.name and name:
                user_by_email.name = name
            if not user_by_email.profile_image and profile_image:
                user_by_email.profile_image = profile_image
            self.db.commit()
            self.db.refresh(user_by_email)
            return user_by_email

        # Create new ADA user entity
        user = User(
            firebase_uid=firebase_uid,
            email=email,
            name=name,
            profile_image=profile_image,
            timezone="UTC",
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()

        # Initialize default user travel & notification preference
        pref = UserPreference(
            user_id=user.id,
            default_transportation="driving",
            default_preparation_time=30,
            default_safety_buffer=15,
        )
        self.db.add(pref)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_or_create_dev_user(
        self,
        firebase_uid: str = "dev-user-firebase-uid-001",
        email: str = "dev@ada-alarm.com",
        name: str = "ADA Developer",
    ) -> User:
        """
        Retrieves or initializes a local development placeholder user.
        Ensures a default UserPreference record is linked.
        """
        return self.get_or_create_by_firebase_uid(
            firebase_uid=firebase_uid,
            email=email,
            name=name,
        )
