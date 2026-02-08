"""Price history record - stores a single price snapshot."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass
class PriceRecord:
    """One price reading for a product at a specific time."""

    product_id: str
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        """Convert to dict for JSON storage."""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PriceRecord":
        """Load from saved dict."""
        return cls(
            id=data.get("id", str(uuid4())),
            product_id=data["product_id"],
            price=data["price"],
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if data.get("timestamp")
                else datetime.now()
            ),
        )
