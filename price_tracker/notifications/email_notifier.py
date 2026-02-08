"""Email notifications for price changes."""

import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dataclasses import dataclass

import aiosmtplib

from price_tracker.models.product import Product


@dataclass
class EmailConfig:
    """SMTP settings for sending emails."""

    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_address: str
    to_address: str
    use_tls: bool = True


class EmailNotifier:
    """Sends price alert emails when products change."""

    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config

    def is_configured(self) -> bool:
        """True if we have all the settings needed to send email."""
        if not self.config:
            return False
        return bool(
            self.config.smtp_server
            and self.config.username
            and self.config.password
            and self.config.to_address
        )

    @classmethod
    def from_settings(cls, settings: dict) -> "EmailNotifier":
        """Create from app settings dict."""
        email_settings = settings.get("email", {})
        if not email_settings.get("enabled", False):
            return cls(None)

        config = EmailConfig(
            smtp_server=email_settings.get("smtp_server", ""),
            smtp_port=email_settings.get("smtp_port", 587),
            username=email_settings.get("username", ""),
            password=email_settings.get("password", ""),
            from_address=email_settings.get("from_address", ""),
            to_address=email_settings.get("to_address", ""),
            use_tls=email_settings.get("use_tls", True),
        )
        return cls(config)

    async def send_price_alert(
        self, product: Product, old_price: Optional[float], new_price: float
    ) -> bool:
        """Send email about price change. Returns True if sent."""
        if not self.is_configured():
            return False

        assert self.config is not None

        subject = self._create_subject(product, old_price, new_price)
        body = self._create_html_body(product, old_price, new_price)

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.config.from_address or self.config.username
        message["To"] = self.config.to_address

        html_part = MIMEText(body, "html", "utf-8")
        message.attach(html_part)

        try:
            await aiosmtplib.send(
                message,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                username=self.config.username,
                password=self.config.password,
                start_tls=self.config.use_tls,
            )
            return True
        except (aiosmtplib.SMTPException, OSError):
            return False

    def _create_subject(
        self, product: Product, old_price: Optional[float], new_price: float
    ) -> str:
        """Build the email subject line."""
        if old_price and new_price < old_price:
            change = ((old_price - new_price) / old_price) * 100
            return f"🔻 Цената падна! {product.name} (-{change:.1f}%)"
        if product.target_price and new_price <= product.target_price:
            return f"🎯 Достигната целева цена! {product.name}"
        return f"📊 Промяна на цена: {product.name}"

    def _create_html_body(
        self, product: Product, old_price: Optional[float], new_price: float
    ) -> str:
        """Build the HTML email content."""
        price_change = ""
        if old_price:
            diff = new_price - old_price
            percent = (diff / old_price) * 100
            color = "green" if diff < 0 else "red"
            sign = "+" if diff > 0 else ""
            price_change = f"""
            <p style="color: {color}; font-size: 18px;">
                Промяна: {sign}{diff:.2f} ({sign}{percent:.1f}%)
            </p>
            """

        target_info = ""
        if product.target_price:
            if new_price <= product.target_price:
                target_info = """
                <p style="color: green; font-weight: bold;">
                    ✅ Цената е под целевата!
                </p>
                """
            else:
                target_info = f"""
                <p>Целева цена: {product.target_price:.2f}</p>
                """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #f5f5f5; padding: 20px; border-radius: 10px;">
                <h2 style="color: #333;">{product.name}</h2>

                <div style="background: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <p style="font-size: 14px; color: #666;">Предишна цена:</p>
                    <p style="font-size: 20px; color: #999; text-decoration: line-through;">
                        {old_price:.2f}
                    </p>

                    <p style="font-size: 14px; color: #666;">Нова цена:</p>
                    <p style="font-size: 28px; color: #333; font-weight: bold;">
                        {new_price:.2f}
                    </p>

                    {price_change}
                    {target_info}
                </div>

                <p>
                    <a href="{product.url}"
                       style="display: inline-block; background: #007bff; color: white;
                              padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Виж продукта
                    </a>
                </p>

                <p style="font-size: 12px; color: #999; margin-top: 20px;">
                    Това съобщение е изпратено от Price Tracker.
                </p>
            </div>
        </body>
        </html>
        """

    async def send_test_email(self) -> tuple[bool, str]:
        """Send a test email to verify settings work."""
        if not self.is_configured():
            return False, "Email is not configured"

        assert self.config is not None

        message = MIMEMultipart("alternative")
        message["Subject"] = "🧪 Price Tracker - Тестово съобщение"
        message["From"] = self.config.from_address or self.config.username
        message["To"] = self.config.to_address

        body = """
        <html>
        <body>
            <h2>Price Tracker</h2>
            <p>Това е тестово съобщение. Ако го получавате, email известяванията работят правилно!</p>
        </body>
        </html>
        """
        html_part = MIMEText(body, "html", "utf-8")
        message.attach(html_part)

        try:
            await aiosmtplib.send(
                message,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                username=self.config.username,
                password=self.config.password,
                start_tls=self.config.use_tls,
            )
            return True, "Тестовият имейл е изпратен успешно!"
        except aiosmtplib.SMTPException as e:
            return False, f"SMTP грешка: {str(e)}"
        except OSError as e:
            return False, f"Мрежова грешка: {str(e)}"
