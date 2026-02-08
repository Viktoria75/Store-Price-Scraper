"""Price history chart widget."""

from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from price_tracker.models.product import Product
from price_tracker.models.price_record import PriceRecord


class PriceChartWidget(QWidget):
    """Widget for displaying price history chart."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._product: Optional[Product] = None
        self._history: list[PriceRecord] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup chart UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        self.title_label = QLabel("История на цените")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)

        # Matplotlib figure
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Placeholder text
        self.placeholder = QLabel("Изберете продукт за да видите историята на цените")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.placeholder)

        self.canvas.hide()

    def set_data(self, product: Product, history: list[PriceRecord]) -> None:
        """Set chart data.

        Args:
            product: Product to display.
            history: List of price records.
        """
        self._product = product
        self._history = history

        self.title_label.setText(f"История на цените: {product.name}")

        if not history:
            self.canvas.hide()
            self.placeholder.setText("Няма налична история на цените")
            self.placeholder.show()
            return

        self.placeholder.hide()
        self.canvas.show()
        self._draw_chart()

    def clear(self) -> None:
        """Clear the chart."""
        self._product = None
        self._history = []
        self.title_label.setText("История на цените")
        self.figure.clear()
        self.canvas.draw()
        self.canvas.hide()
        self.placeholder.setText("Изберете продукт за да видите историята на цените")
        self.placeholder.show()

    def _draw_chart(self) -> None:
        """Draw the price chart."""
        self.figure.clear()

        # Sort by timestamp
        records = sorted(self._history, key=lambda r: r.timestamp)

        if not records:
            return

        # Extract data
        dates = [r.timestamp for r in records]
        prices = [r.price for r in records]

        # Create subplot
        ax = self.figure.add_subplot(111)

        # Plot line
        ax.plot(dates, prices, "b-o", linewidth=2, markersize=6)

        # Fill under line
        ax.fill_between(dates, prices, alpha=0.2)

        # Mark current price
        if self._product and self._product.current_price:
            ax.axhline(
                y=self._product.current_price,
                color="green",
                linestyle="--",
                alpha=0.5,
                label=f"Текуща: {self._product.current_price:.2f}",
            )

        # Mark target price
        if self._product and self._product.target_price:
            ax.axhline(
                y=self._product.target_price,
                color="red",
                linestyle="--",
                alpha=0.5,
                label=f"Целева: {self._product.target_price:.2f}",
            )

        # Format axes
        ax.set_xlabel("Дата")
        ax.set_ylabel("Цена")

        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.figure.autofmt_xdate()

        # Add grid
        ax.grid(True, alpha=0.3)

        # Add legend if needed
        if self._product and (
            self._product.current_price or self._product.target_price
        ):
            ax.legend(loc="upper right", fontsize="small")

        # Calculate statistics
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)

            # Add stats text
            stats_text = (
                f"Мин: {min_price:.2f} | "
                f"Макс: {max_price:.2f} | "
                f"Ср.: {avg_price:.2f}"
            )
            ax.set_title(stats_text, fontsize=9, color="gray")

        self.figure.tight_layout()
        self.canvas.draw()
