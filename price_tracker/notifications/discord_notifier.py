"""Discord notifications via webhooks."""

from typing import Optional
from dataclasses import dataclass

import aiohttp

from price_tracker.models.product import Product


@dataclass
class DiscordConfig:
    """Just needs the webhook URL from Discord server settings."""

    webhook_url: str


class DiscordNotifier:
    """Posts price alerts to a Discord channel."""

    def __init__(self, config: Optional[DiscordConfig] = None):
        self.config = config

    def is_configured(self) -> bool:
        """True if we have a webhook URL."""
        if not self.config:
            return False
        return bool(self.config.webhook_url)

    @classmethod
    def from_settings(cls, settings: dict) -> "DiscordNotifier":
        """Create from app settings dict, with env var fallback."""
        import os
        
        discord_settings = settings.get("discord", {})
        enabled = discord_settings.get("enabled", False)
        webhook_url = discord_settings.get("webhook_url", "").strip()
        
        # Check environment variable if webhook is missing or empty
        env_webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
        
        # If enabled in settings OR we have an env var, we try to configure it
        if not enabled and not env_webhook:
            return cls(None)
            
        # Env var takes precedence if it exists, otherwise use settings
        final_webhook = env_webhook if env_webhook else webhook_url
        
        if not final_webhook:
             return cls(None)

        return cls(DiscordConfig(webhook_url=final_webhook))

    async def send_price_alert(
        self, product: Product, old_price: Optional[float], new_price: float
    ) -> bool:
        """Send price change to Discord. Returns True if sent."""
        if not self.is_configured():
            return False

        assert self.config is not None

        embed = self._create_embed(product, old_price, new_price)
        payload = {"embeds": [embed]}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url, json=payload
                ) as response:
                    return response.status in (200, 204)
        except aiohttp.ClientError:
            return False

    def _create_embed(
        self, product: Product, old_price: Optional[float], new_price: float
    ) -> dict:
        """Build the Discord embed message."""
        if old_price and new_price < old_price:
            color = 0x00FF00  # Green
            title = "🔻 Цената падна!"
        elif product.target_price and new_price <= product.target_price:
            color = 0xFFD700  # Gold
            title = "🎯 Достигната целева цена!"
        else:
            color = 0x3498DB  # Blue
            title = "📊 Промяна на цена"

        fields = [
            {"name": "Продукт", "value": product.name, "inline": False},
        ]

        if old_price:
            fields.append({
                "name": "Предишна цена",
                "value": f"~~{old_price:.2f} лв.~~",
                "inline": True,
            })

        fields.append({
            "name": "Нова цена",
            "value": f"**{new_price:.2f} лв.**",
            "inline": True,
        })

        if old_price:
            diff = new_price - old_price
            percent = (diff / old_price) * 100
            sign = "+" if diff > 0 else ""
            fields.append({
                "name": "Промяна",
                "value": f"{sign}{diff:.2f} лв. ({sign}{percent:.1f}%)",
                "inline": True,
            })

        if product.target_price:
            status = "✅ Достигната!" if new_price <= product.target_price else f"{product.target_price:.2f} лв."
            fields.append({
                "name": "Целева цена",
                "value": status,
                "inline": True,
            })

        return {
            "title": title,
            "color": color,
            "fields": fields,
            "url": product.url,
            "footer": {"text": "Price Tracker"},
        }

    async def send_test_message(self) -> tuple[bool, str]:
        """Send a test message to check if webhook works."""
        if not self.is_configured():
            return False, "Discord webhook is not configured"

        assert self.config is not None

        payload = {
            "embeds": [
                {
                    "title": "🧪 Price Tracker - Тест",
                    "description": "Това е тестово съобщение. Discord известяванията работят!",
                    "color": 0x00FF00,
                }
            ]
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url, json=payload
                ) as response:
                    if response.status in (200, 204):
                        return True, "Тестовото съобщение е изпратено успешно!"
                    return False, f"Discord върна код: {response.status}"
        except aiohttp.ClientError as e:
            return False, f"Грешка при връзка: {str(e)}"
