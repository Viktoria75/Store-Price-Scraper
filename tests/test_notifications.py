"""Tests for notification modules."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

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
        assert "падна" in subject.lower() or "🔻" in subject

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

        # Test target reached without price drop (same price scenario)
        subject = notifier._create_subject(product, None, 85.0)
        assert "целева" in subject.lower() or "🎯" in subject

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
        assert "падна" in embed["title"].lower() or "🔻" in embed["title"]
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

        # Test target reached without price drop (no old price)
        embed = notifier._create_embed(product, None, 85.0)

        assert embed["color"] == 0xFFD700  # Gold
        assert "целева" in embed["title"].lower() or "🎯" in embed["title"]

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
