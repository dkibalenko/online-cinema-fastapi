from typing import Annotated
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from database import get_db
from auth.models import User, UserGroup, UserGroupEnum
from auth.schemas import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
)


router = APIRouter()


@router.post(
    "/register/",
    response_model=UserRegistrationResponseSchema,
    summary="User Registration",
    status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserRegistrationRequestSchema,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRegistrationResponseSchema:
    existing_stmt = select(User).where((User.email == user_data.email))

    existing_result = await db.execute(existing_stmt)
    existing_user = existing_result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this email '{user_data.email}' already exists."
        )

    stmt = select(UserGroup).where(UserGroup.name == UserGroupEnum.USER)

    result = await db.execute(stmt)
    user_group = result.scalar_one_or_none()
    if not user_group:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default user group not found."
        )

    try:
        new_user = User.create(
            email=str(user_data.email),
            raw_password=user_data.password,
            group_id=user_group.id
        )
        db.add(new_user)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during user creation."
        ) from e

    return new_user
