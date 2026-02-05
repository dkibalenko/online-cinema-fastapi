from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from logger_config import get_logger
from auth.exceptions import BaseEmailError
from auth.interfaces import EmailSenderInterface


log = get_logger()


class EmailSender(EmailSenderInterface):

    def __init__(
        self,
        hostname: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        template_dir: str,
        activation_email_template_name: str,
        activation_complete_email_template_name: str,
        password_email_template_name: str,
        password_complete_email_template_name: str,
        from_email: str = None,
    ):
        self._hostname = hostname  # SMTP_SERVER
        self._port = port  # SMTP_PORT
        self._username = username  # SMTP_USERNAME
        self._password = password  # SMTP_PASSWORD
        self._use_tls = use_tls

        # Sender address defaults to username
        self._from_email = from_email or username

        self._activation_email_template_name = activation_email_template_name
        self._activation_complete_email_template_name = (
            activation_complete_email_template_name
        )
        self._password_email_template_name = password_email_template_name
        self._password_complete_email_template_name = (
            password_complete_email_template_name
        )

        self._env = Environment(loader=FileSystemLoader(template_dir))

    async def _send_email(
        self,
        recipient: str,
        subject: str,
        html_content: str
    ) -> None:
        message = MIMEMultipart()
        message["From"] = self._from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(html_content, "html"))

        try:
            log.info(
                f"Connecting to SMTP {self._hostname}:{self._port} "
                f"(use_tls={self._use_tls})"
            )

            smtp = aiosmtplib.SMTP(
                hostname=self._hostname,  # SMTP_SERVER
                port=self._port,  # SMTP_PORT
                start_tls=self._use_tls
            )

            await smtp.connect()
            log.info(f"Connected to SMTP server {self._hostname}:{self._port}")

            log.debug(f"Authenticating as {self._username}")
            await smtp.login(self._username, self._password)  # SMTP_USERNAME, SMTP_PASSWORD

            log.info(f"Sending email to {recipient}")
            await smtp.sendmail(
                self._from_email, [recipient], message.as_string()
            )
            await smtp.quit()

            log.info(f"✅ Email sent to {recipient}")
        except aiosmtplib.SMTPException as error:
            log.error(f"❌ Failed to send email to {recipient}: {error}")
            raise BaseEmailError(
                f"❌ Failed to send email to {recipient}: {error}"
            )

    async def send_activation_email(
        self,
        email: str,
        activation_link: str
    ) -> None:
        """
        Send an account activation email asynchronously.

        Args:
            email (str): The recipient's email address.
            activation_link (str): The activation link to be included
                in the email.
        """
        log.debug(
            f"Rendering activation template "
            f"'{self._activation_email_template_name}' for {email}"
        )

        template = self._env.get_template(self._activation_email_template_name)
        html_content = template.render(
            email=email, activation_link=activation_link
        )

        log.debug(
            f"Rendered activation template ({len(html_content)} chars) "
            f"for {email}"
        )

        await self._send_email(email, "Account Activation", html_content)

    async def send_activation_complete_email(
        self,
        email: str,
        login_link: str
    ) -> None:
        """
        Send an account activation completion email asynchronously.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to include in the email.
        """
        log.debug(
            f"Rendering activation complete template "
            f"'{self._activation_complete_email_template_name}' for {email}"
        )

        template = self._env.get_template(
            self._activation_complete_email_template_name
        )
        html_content = template.render(email=email, login_link=login_link)

        log.debug(
            f"Rendered activation complete template "
            f"({len(html_content)} chars) for {email}"
        )

        await self._send_email(
            email,
            "Account Activated Successfully",
            html_content
        )

    async def send_password_reset_email(
        self,
        email: str,
        reset_link: str
    ) -> None:
        """
        Send a password reset request email asynchronously.

        Args:
            email (str): The recipient's email address.
            reset_link (str): The reset link to be included in the email.
        """
        log.debug(
            f"Rendering password reset template "
            f"'{self._password_email_template_name}' for {email}"
        )

        template = self._env.get_template(self._password_email_template_name)
        html_content = template.render(email=email, reset_link=reset_link)

        log.debug(
            f"Rendered password reset template "
            f"({len(html_content)} chars) for {email}"
        )

        await self._send_email(email, "Password Reset Request", html_content)

    async def send_password_reset_complete_email(
        self,
        email: str,
        login_link: str
    ) -> None:
        """
        Send a password reset completion email asynchronously.

        Args:
            email (str): The recipient's email address.
            login_link (str): The login link to be included in the email.
        """
        log.debug(
            f"Rendering password reset complete template "
            f"'{self._password_complete_email_template_name}' for {email}"
        )

        template = self._env.get_template(
            self._password_complete_email_template_name
        )
        html_content = template.render(email=email, login_link=login_link)

        log.debug(
            f"Rendered password reset complete template "
            f"({len(html_content)} chars) for {email}"
        )

        await self._send_email(
            email,
            "Your Password Has Been Successfully Reset",
            html_content
        )
