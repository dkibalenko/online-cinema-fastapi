from logger_config import get_logger
from notifications.email.base_renderer import TemplateRenderer
from notifications.email.smtp_client import SMTPClient
from notifications.interfaces import AuthEmailSenderInterface

log = get_logger()


class AuthEmailSender(AuthEmailSenderInterface):
    """Class responsible for sending authentication-related emails.

    Handles tasks such as account activation and password reset emails.
    """

    def __init__(
        self,
        smtp: SMTPClient,
        renderer: TemplateRenderer,
        activation_template: str,
        activation_complete_template: str,
        password_reset_template: str,
        password_reset_complete_template: str,
    ):
        self.smtp = smtp
        self.renderer = renderer
        self.activation_template = activation_template
        self.activation_complete_template = activation_complete_template
        self.password_reset_template = password_reset_template
        self.password_reset_complete_template = (
            password_reset_complete_template
        )

    async def send_activation_email(
        self, email: str, activation_link: str
    ) -> None:
        """Asynchronously send an email with an account activation link.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to include in the email.

        """
        log.debug(
            f"Rendering activation template "
            f"'{self.activation_template}' for {email}"
        )

        template = self.renderer.get(self.activation_template)
        html = template.render(email=email, activation_link=activation_link)

        log.debug(
            f"Rendered activation template ({len(html)} chars) for {email}"
        )

        await self.smtp.send(email, "Account Activation", html)

    async def send_activation_complete_email(
        self, email: str, login_link: str
    ) -> None:
        """Asynchronously send email confirming the account has been activated.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.

        """
        log.debug(
            f"Rendering activation complete template "
            f"'{self.activation_complete_template}' for {email}"
        )

        template = self.renderer.get(self.activation_complete_template)
        html = template.render(email=email, login_link=login_link)

        log.debug(
            f"Rendered activation complete template "
            f"({len(html)} chars) for {email}"
        )

        await self.smtp.send(email, "Account Activated", html)

    async def send_password_reset_email(
        self, email: str, reset_link: str
    ) -> None:
        """Asynchronously send an email with a password reset link.

        Args:
            email (str): The recipient's email address.
            reset_link (str): The password reset link to include in the email.
        """
        log.debug(
            f"Rendering password reset template "
            f"'{self.password_reset_template}' for {email}"
        )

        template = self.renderer.get(self.password_reset_template)
        html = template.render(email=email, reset_link=reset_link)

        log.debug(
            f"Rendered password reset template ({len(html)} chars) for {email}"
        )

        await self.smtp.send(email, "Password Reset", html)

    async def send_password_reset_complete_email(
        self, email: str, login_link: str
    ) -> None:
        """Asynchronously send an email confirming the password has been reset.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        log.debug(
            f"Rendering password reset complete template "
            f"'{self.password_reset_complete_template}' for {email}"
        )

        template = self.renderer.get(self.password_reset_complete_template)
        html = template.render(email=email, login_link=login_link)

        log.debug(
            f"Rendered password reset complete template "
            f"({len(html)} chars) for {email}"
        )

        await self.smtp.send(email, "Password Reset Complete", html)
