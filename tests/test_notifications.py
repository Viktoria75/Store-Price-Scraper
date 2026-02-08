"""Tests for notification modules."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
import aiosmtplib

from price_tracker.models.product import Product
from price_tracker.notifications.email_notifier import EmailNotifier, EmailConfig
from price_tracker.notifications.discord_notifier import DiscordNotifier, DiscordConfig


class TestEmailNotifier:
    """Test cases for email notifier."""

    def test_notifier_not_configured(self) -> None:
        """Test notifier without configuration."""
        notifier = EmailNotifier(None)
        assert notifier.is_configured() is False

    def test_notifier_with_incomplete_config(self) -> None:
        """Test notifier with incomplete configuration."""
        config = EmailConfig(
            smtp_server="",
            smtp_port=587,
            username="",
            password="",
            from_address="",
            to_address="",
        )
        notifier = EmailNotifier(config)
        assert notifier.is_configured() is False

    def test_notifier_with_full_config(self) -> None:
        """Test notifier with full configuration."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)
        assert notifier.is_configured() is True

    def test_create_subject_price_drop(self) -> None:
        """Test email subject for price drop."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
        )

        subject = notifier._create_subject(product, 100.0, 80.0)
        assert "падна" in subject.lower() or "Price" in subject or "🔻" in subject

    def test_create_subject_target_reached(self) -> None:
        """Test email subject for target price reached."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
            target_price=90.0,
        )

        subject = notifier._create_subject(product, None, 85.0)
        assert "целева" in subject.lower() or "Target" in subject or "🎯" in subject

    def test_from_settings_disabled(self) -> None:
        """Test creating notifier from settings when disabled."""
        settings = {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
            }
        }

        notifier = EmailNotifier.from_settings(settings)
        assert notifier.is_configured() is False

    def test_from_settings_enabled(self) -> None:
        """Test creating notifier from settings when enabled."""
        settings = {
            "email": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "user@gmail.com",
                "password": "password",
                "from_address": "user@gmail.com",
                "to_address": "recipient@example.com",
            }
        }

        notifier = EmailNotifier.from_settings(settings)
        assert notifier.is_configured() is True

    def test_from_settings_no_email_key(self) -> None:
        """Test creating notifier from settings with no email key."""
        settings = {}
        notifier = EmailNotifier.from_settings(settings)
        assert notifier.is_configured() is False

    def test_create_html_body(self) -> None:
        """Test email HTML body creation."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
            target_price=50.0,
        )

        body = notifier._create_html_body(product, 100.0, 80.0)
        assert "Test Product" in body
        assert "100" in body
        assert "80" in body

    def test_create_html_body_target_reached(self) -> None:
        """Test email HTML body when target is reached."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
            target_price=100.0,
        )

        body = notifier._create_html_body(product, 120.0, 80.0)
        assert "целевата" in body or "target" in body.lower()

    @pytest.mark.asyncio
    async def test_send_price_alert_not_configured(self) -> None:
        """Test send_price_alert when not configured."""
        notifier = EmailNotifier(None)
        product = Product(name="Test", url="https://example.com", selector=".price")
        
        result = await notifier.send_price_alert(product, 100.0, 80.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_price_alert_success(self) -> None:
        """Test send_price_alert success with mocked aiosmtplib."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)
        product = Product(name="Test", url="https://example.com", selector=".price")
        
        with patch('price_tracker.notifications.email_notifier.aiosmtplib.send', new_callable=AsyncMock) as mock_send:
            result = await notifier.send_price_alert(product, 100.0, 80.0)
        
        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_price_alert_smtp_error(self) -> None:
        """Test send_price_alert when SMTP fails."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)
        product = Product(name="Test", url="https://example.com", selector=".price")
        
        with patch('price_tracker.notifications.email_notifier.aiosmtplib.send', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = aiosmtplib.SMTPException("SMTP error")
            result = await notifier.send_price_alert(product, 100.0, 80.0)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_send_test_email_success(self) -> None:
        """Test send_test_email success."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)
        
        with patch('price_tracker.notifications.email_notifier.aiosmtplib.send', new_callable=AsyncMock) as mock_send:
            success, message = await notifier.send_test_email()
        
        assert success is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_email_smtp_error(self) -> None:
        """Test send_test_email failure."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            from_address="user@gmail.com",
            to_address="recipient@example.com",
        )
        notifier = EmailNotifier(config)
        
        with patch('price_tracker.notifications.email_notifier.aiosmtplib.send', new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = aiosmtplib.SMTPException("SMTP error")
            success, message = await notifier.send_test_email()
        
        assert success is False
        assert "SMTP" in message

    @pytest.mark.asyncio
    async def test_send_test_email_not_configured(self) -> None:
        """Test send_test_email when not configured."""
        notifier = EmailNotifier(None)
        success, message = await notifier.send_test_email()
        assert success is False


class TestDiscordNotifier:
    """Test cases for Discord notifier."""

    def test_notifier_not_configured(self) -> None:
        """Test notifier without configuration."""
        notifier = DiscordNotifier(None)
        assert notifier.is_configured() is False

    def test_notifier_with_empty_webhook(self) -> None:
        """Test notifier with empty webhook URL."""
        config = DiscordConfig(webhook_url="")
        notifier = DiscordNotifier(config)
        assert notifier.is_configured() is False

    def test_notifier_with_webhook(self) -> None:
        """Test notifier with valid webhook URL."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)
        assert notifier.is_configured() is True

    def test_create_embed_price_drop(self) -> None:
        """Test Discord embed for price drop."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
        )

        embed = notifier._create_embed(product, 100.0, 80.0)

        assert embed["color"] == 0x00FF00  # Green
        assert "падна" in embed["title"].lower() or "Price" in embed["title"] or "🔻" in embed["title"]
        assert len(embed["fields"]) >= 3

    def test_create_embed_target_reached(self) -> None:
        """Test Discord embed for target price reached."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
            target_price=90.0,
        )

        embed = notifier._create_embed(product, None, 85.0)

        assert embed["color"] == 0xFFD700  # Gold
        assert "целева" in embed["title"].lower() or "Target" in embed["title"] or "🎯" in embed["title"]

    def test_from_settings_disabled(self) -> None:
        """Test creating notifier from settings when disabled."""
        settings = {
            "discord": {
                "enabled": False,
                "webhook_url": "https://discord.com/api/webhooks/123/abc",
            }
        }

        notifier = DiscordNotifier.from_settings(settings)
        assert notifier.is_configured() is False

    def test_from_settings_enabled(self) -> None:
        """Test creating notifier from settings when enabled."""
        settings = {
            "discord": {
                "enabled": True,
                "webhook_url": "https://discord.com/api/webhooks/123/abc",
            }
        }

        notifier = DiscordNotifier.from_settings(settings)
        assert notifier.is_configured() is True

    def test_from_settings_no_discord_key(self) -> None:
        """Test creating notifier from settings with no discord key."""
        settings = {}
        notifier = DiscordNotifier.from_settings(settings)
        assert notifier.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_price_alert_not_configured(self) -> None:
        """Test send_price_alert when not configured."""
        notifier = DiscordNotifier(None)
        product = Product(name="Test", url="https://example.com", selector=".price")
        
        result = await notifier.send_price_alert(product, 100.0, 80.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_test_message_not_configured(self) -> None:
        """Test send_test_message when not configured."""
        notifier = DiscordNotifier(None)
        success, message = await notifier.send_test_message()
        assert success is False

    def test_create_embed_price_increase(self) -> None:
        """Test Discord embed for price increase (else branch)."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
        )

        # Price went up, should use blue color
        embed = notifier._create_embed(product, 80.0, 100.0)

        assert embed["color"] == 0x3498DB  # Blue
        assert "📊" in embed["title"]

    def test_create_embed_with_target_not_reached(self) -> None:
        """Test Discord embed when target is set but not reached."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
            target_price=50.0,  # Target not yet reached
        )

        # Price dropped but not to target
        embed = notifier._create_embed(product, 100.0, 80.0)

        assert embed["color"] == 0x00FF00  # Green (price dropped)
        # Should have target field showing the target price
        target_field = next((f for f in embed["fields"] if f["name"] == "Целева цена"), None)
        assert target_field is not None
        assert "50.00" in target_field["value"]

    def test_create_embed_no_old_price_no_target(self) -> None:
        """Test Discord embed with no old price and no target."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        product = Product(
            name="Test Product",
            url="https://example.com",
            selector=".price",
        )

        embed = notifier._create_embed(product, None, 100.0)

        assert embed["color"] == 0x3498DB  # Blue (no comparison available)
        # Should only have product name and new price fields
        assert len(embed["fields"]) == 2

    @pytest.mark.asyncio
    async def test_send_price_alert_success(self) -> None:
        """Test send_price_alert success with mocked aiohttp."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)
        product = Product(name="Test", url="https://example.com", selector=".price")

        # Mock the context manager chain: ClientSession() -> post() -> response
        mock_response = AsyncMock()
        mock_response.status = 204
        
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value = mock_response
        mock_post.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        # session.post is NOT async, it returns a context manager synchronously
        mock_session.post = MagicMock(return_value=mock_post)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier.send_price_alert(product, 100.0, 80.0)
            
        assert result is True

    @pytest.mark.asyncio
    async def test_send_price_alert_failure(self) -> None:
        """Test send_price_alert failure (network error)."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)
        product = Product(name="Test", url="https://example.com", selector=".price")

        mock_session = AsyncMock()
        # session.post raises the error when called or entered?
        # aiohttp usage: async with session.post(...)
        # So calling post returns CM, entering CM raises exception? Or calling post raises?
        # Usually connection error happens during __aenter__ (request sending).
        mock_post = AsyncMock()
        mock_post.__aenter__.side_effect = aiohttp.ClientError("Network Error")
        mock_post.__aexit__.return_value = None
        
        mock_session.post = MagicMock(return_value=mock_post)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier.send_price_alert(product, 100.0, 80.0)
            
        assert result is False

    @pytest.mark.asyncio
    async def test_send_test_message_success(self) -> None:
        """Test send_test_message success."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        # Mock the context manager chain
        mock_response = AsyncMock()
        mock_response.status = 204
        
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value = mock_response
        mock_post.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_post)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            success, msg = await notifier.send_test_message()
            
        assert success is True
        assert "успешно" in msg

    @pytest.mark.asyncio
    async def test_send_test_message_failure_status(self) -> None:
        """Test send_test_message failure (bad status code)."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        # Mock response with error status
        mock_response = AsyncMock()
        mock_response.status = 400
        
        mock_post = AsyncMock()
        mock_post.__aenter__.return_value = mock_response
        mock_post.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_post)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            success, msg = await notifier.send_test_message()
            
        assert success is False
        assert "400" in msg

    @pytest.mark.asyncio
    async def test_send_test_message_failure_network(self) -> None:
        """Test send_test_message failure (network error)."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        notifier = DiscordNotifier(config)

        mock_post = AsyncMock()
        mock_post.__aenter__.side_effect = aiohttp.ClientError("Network Error")
        mock_post.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_post)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch('aiohttp.ClientSession', return_value=mock_session):
            success, msg = await notifier.send_test_message()
            
        assert success is False
        assert "Грешка" in msg

