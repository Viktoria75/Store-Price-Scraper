"""Main entry point for Price Tracker application."""

import sys
import asyncio
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from price_tracker.gui.main_window import MainWindow


def main() -> int:
    """Main application entry point.

    Returns:
        Exit code.
    """
    # Create event loop for async operations
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Price Tracker")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("PriceTracker")

    # Apply stylesheet
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTableWidget {
            background-color: white;
            alternate-background-color: #f9f9f9;
            gridline-color: #ddd;
        }
        QTableWidget::item:selected {
            background-color: #0078d7;
            color: white;
        }
        QHeaderView::section {
            background-color: #e0e0e0;
            padding: 5px;
            border: 1px solid #ccc;
            font-weight: bold;
        }
        QToolBar {
            background-color: #f0f0f0;
            border: none;
            spacing: 5px;
            padding: 5px;
        }
        QToolBar QToolButton {
            padding: 5px 10px;
        }
        QPushButton {
            padding: 6px 12px;
            background-color: #0078d7;
            color: white;
            border: none;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #006cc1;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #0078d7;
        }
    """)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
