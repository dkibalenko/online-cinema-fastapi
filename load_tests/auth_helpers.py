from locust.clients import HttpSession

from .config import TEST_USER_EMAIL, TEST_USER_PASSWORD, VERIFY_SSL


def login_and_set_headers(client: HttpSession) -> None:
    resp = client.post(
        "/auth/login",
        json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        verify=VERIFY_SSL,
        name="/auth/login",
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    client.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "X-Disable-Rate-Limit": "true",
        }
    )
