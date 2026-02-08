"""Product model for tracked items."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4


@dataclass
class Product:
    """A product we're tracking the price of."""

    name: str
    url: str
    selector: str  # CSS or XPath selector to find the price
    selector_type: Literal["css", "xpath"] = "css"
    id: str = field(default_factory=lambda: str(uuid4()))
    current_price: Optional[float] = None
    previous_price: Optional[float] = None
    last_checked: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    notify_on_drop: bool = True
    target_price: Optional[float] = None
    use_selenium: bool = False  # Use browser automation for JS-heavy sites

    def to_dict(self) -> dict:
        """Convert to dict for saving to JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "selector": self.selector,
            "selector_type": self.selector_type,
            "current_price": self.current_price,
            "previous_price": self.previous_price,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "created_at": self.created_at.isoformat(),
            "notify_on_drop": self.notify_on_drop,
            "target_price": self.target_price,
            "use_selenium": self.use_selenium,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        """Create a Product from a saved dict."""
        return cls(
            id=data.get("id", str(uuid4())),
            name=data["name"],
            url=data["url"],
            selector=data["selector"],
            selector_type=data.get("selector_type", "css"),
            current_price=data.get("current_price"),
            previous_price=data.get("previous_price"),
            last_checked=(
                datetime.fromisoformat(data["last_checked"])
                if data.get("last_checked")
                else None
            ),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now()
            ),
            notify_on_drop=data.get("notify_on_drop", True),
            target_price=data.get("target_price"),
            use_selenium=data.get("use_selenium", False),
        )

    def has_price_dropped(self) -> bool:
        """True if current price is lower than previous."""
        if self.previous_price is None or self.current_price is None:
            return False
        return self.current_price < self.previous_price

    def is_below_target(self) -> bool:
        """True if price hit or went below the target."""
        if self.target_price is None or self.current_price is None:
            return False
        return self.current_price <= self.target_price

    def should_notify(self) -> bool:
        """Should we send a notification for this product?"""
        if not self.notify_on_drop:
            return False
        return self.has_price_dropped() or self.is_below_target()
