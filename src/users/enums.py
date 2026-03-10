import enum


class UserGroupEnum(enum.StrEnum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class GenderEnum(enum.StrEnum):
    MAN = "man"
    WOMAN = "woman"
