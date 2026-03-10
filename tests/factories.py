from decimal import Decimal

import factory
from movies.models import Certification, Genre, Movie, MovieComment
from users.models import User, UserProfile
from users.utils import hash_password


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "flush"

    email = factory.Faker("email")
    group_id = 1
    _hashed_password = factory.LazyFunction(
        lambda: hash_password("password123")
    )


class GenreFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Genre
        sqlalchemy_session_persistence = "flush"

    name = factory.Faker("word")


class CertificationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Certification
        sqlalchemy_session_persistence = "flush"

    name = factory.Faker(
        "random_element", elements=["G", "PG", "PG-13", "R", "NC-17"]
    )


class MovieFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Movie
        sqlalchemy_session_persistence = "flush"

    name = factory.Faker("sentence", nb_words=3)
    year = factory.Faker("year")
    time = factory.Faker("random_int", min=80, max=180)
    imdb = factory.Faker("pyfloat", min_value=4.0, max_value=9.5)
    votes = factory.Faker("random_int", min=1000, max=1000000)
    meta_score = None
    gross = None
    description = factory.Faker("paragraph")
    price = Decimal("9.99")

    certification = factory.SubFactory(CertificationFactory)


class UserProfileFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = UserProfile
        sqlalchemy_session_persistence = "flush"

    user = factory.SubFactory(UserFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    gender = None
    birth_date = None
    info = factory.Faker("sentence")
    avatar_url = None


class MovieCommentFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = MovieComment
        sqlalchemy_session_persistence = "flush"

    movie = factory.SubFactory(MovieFactory)
    user = factory.SubFactory(UserFactory)
    content = factory.Faker("sentence")
    parent = None
