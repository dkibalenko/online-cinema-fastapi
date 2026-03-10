from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from logger_config import get_logger
from notifications.exceptions import BaseEmailError

log = get_logger()


class SMTPClient:
    def __init__(
        self,
        hostname: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        from_email: str
    ):
        self.hostname = hostname  # SMTP_SERVER
        self.port = port  # SMTP_PORT
        self.username = username  # SMTP_USERNAME
        self.password = password  # SMTP_PASSWORD
        self.use_tls = use_tls
        self.from_email = from_email or username or "noreply@cinema.local"

    async def send(self, recipient: str, subject: str, html: str) -> None:
        """Asynchronously send an email using the SMTP server.

        Args:
            recipient (str): The recipient's email address.
            subject (str): The email subject.
            html (str): The email content in HTML format.

        """
        message = MIMEMultipart()
        message["From"] = self.from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(html, "html"))

        log.info(
                f"Connecting to SMTP {self.hostname}:{self.port} "
                f"(use_tls={self.use_tls})"
            )

        smtp = aiosmtplib.SMTP(
            hostname=self.hostname,  # SMTP_SERVER
            port=self.port,  # SMTP_PORT
            start_tls=self.use_tls,
        )
        try:
            await smtp.connect()
            log.info(f"Connected to SMTP server {self.hostname}:{self.port}")

            log.debug(f"Authenticating as {self.username}")
            # MailHog(plain SMTP) ignores this, no error
            await smtp.login(self.username, self.password)

            log.info(f"Sending email to {recipient}")
            await smtp.sendmail(
                self.from_email, [recipient], message.as_string()
            )

            await smtp.quit()

            log.info(f"✅ Email sent to {recipient}")
        except aiosmtplib.SMTPException as e:
            log.error(f"❌ Failed to send email to {recipient}: {e}")
            raise BaseEmailError(
                f"❌ Failed to send email to {recipient}: {e}",
            ) from e
