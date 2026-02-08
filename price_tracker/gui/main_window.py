"""Main application window."""

import asyncio
import threading
from datetime import datetime
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QFileDialog,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QMimeData
from PyQt6.QtGui import QAction, QIcon, QDragEnterEvent, QDropEvent

from price_tracker.models.product import Product
from price_tracker.storage.json_storage import JsonStorage
from price_tracker.storage.exporter import DataExporter
from price_tracker.scheduler.background_checker import BackgroundChecker, PriceUpdate
from price_tracker.notifications.email_notifier import EmailNotifier
from price_tracker.notifications.discord_notifier import DiscordNotifier
from price_tracker.gui.product_dialog import ProductDialog
from price_tracker.gui.settings_dialog import SettingsDialog
from price_tracker.gui.price_chart import PriceChartWidget


class MainWindow(QMainWindow):
    """Main application window."""

    price_updated = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()

        self.storage = JsonStorage()
        self.settings = self.storage.get_settings()
        self.checker: Optional[BackgroundChecker] = None
        self.email_notifier = EmailNotifier.from_settings(self.settings)
        self.discord_notifier = DiscordNotifier.from_settings(self.settings)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_status_bar()
        self._setup_checker()
        self._load_products()

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Connect signal
        self.price_updated.connect(self._on_price_updated_signal)

        # Status update timer
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status_bar)
        self._status_timer.start(1000)

    def _setup_ui(self) -> None:
        """Setup main UI components."""
        self.setWindowTitle("Price Tracker - Следене на цени")
        self.setMinimumSize(1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)

        # Create splitter for table and chart
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left side - Product table
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Име",
            "URL",
            "Цена",
            "Промяна",
            "Последна проверка",
            "Статус",
        ])
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_double_click)

        # Set column stretching
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 80)

        left_layout.addWidget(self.table)
        splitter.addWidget(left_widget)

        # Right side - Price chart
        self.chart_widget = PriceChartWidget()
        splitter.addWidget(self.chart_widget)

        # Set stretch factors: table gets more space (2:1 ratio)
        splitter.setStretchFactor(0, 2)  # Table gets 2x stretch
        splitter.setStretchFactor(1, 1)  # Chart gets 1x stretch
        
        # Set initial sizes (60% table, 40% chart)
        splitter.setSizes([600, 400])
        
        # Set minimum width for chart to prevent it from being too small
        self.chart_widget.setMinimumWidth(300)
        self.chart_widget.setMaximumWidth(500)  # Limit chart to max 500px

    def _setup_menu(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()
        assert menubar is not None

        # File menu
        file_menu = menubar.addMenu("Файл")
        assert file_menu is not None

        import_csv_action = QAction("Импорт от CSV...", self)
        import_csv_action.triggered.connect(self._import_csv)
        file_menu.addAction(import_csv_action)

        import_json_action = QAction("Импорт от JSON...", self)
        import_json_action.triggered.connect(self._import_json)
        file_menu.addAction(import_json_action)

        file_menu.addSeparator()

        export_csv_action = QAction("Експорт към CSV...", self)
        export_csv_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_csv_action)

        export_json_action = QAction("Експорт към JSON...", self)
        export_json_action.triggered.connect(self._export_json)
        file_menu.addAction(export_json_action)

        file_menu.addSeparator()

        exit_action = QAction("Изход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Редакция")
        assert edit_menu is not None

        settings_action = QAction("Настройки...", self)
        settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("Помощ")
        assert help_menu is not None

        about_action = QAction("За програмата", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self) -> None:
        """Setup toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.add_action = QAction("➕ Добави", self)
        self.add_action.triggered.connect(self._add_product)
        toolbar.addAction(self.add_action)

        self.edit_action = QAction("✏️ Редактирай", self)
        self.edit_action.triggered.connect(self._edit_product)
        self.edit_action.setEnabled(False)
        toolbar.addAction(self.edit_action)

        self.delete_action = QAction("🗑️ Изтрий", self)
        self.delete_action.triggered.connect(self._delete_product)
        self.delete_action.setEnabled(False)
        toolbar.addAction(self.delete_action)

        toolbar.addSeparator()

        self.refresh_action = QAction("🔄 Обнови", self)
        self.refresh_action.triggered.connect(self._refresh_prices)
        toolbar.addAction(self.refresh_action)

        toolbar.addSeparator()

        self.start_action = QAction("▶️ Старт", self)
        self.start_action.triggered.connect(self._toggle_tracking)
        toolbar.addAction(self.start_action)

    def _setup_status_bar(self) -> None:
        """Setup status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("Готов")
        self.status_bar.addWidget(self.status_label)

        self.next_check_label = QLabel("")
        self.status_bar.addPermanentWidget(self.next_check_label)

    def _setup_checker(self) -> None:
        """Setup background checker."""
        interval = self.settings.get("check_interval_minutes", 60)
        use_selenium = self.settings.get("use_selenium_fallback", True)

        self.checker = BackgroundChecker(
            storage=self.storage,
            interval_minutes=interval,
            use_selenium_fallback=use_selenium,
        )
        self.checker.set_on_price_update(self._on_price_update)
        self.checker.set_on_check_complete(self._on_check_complete)

    def _load_products(self) -> None:
        """Load and display products."""
        products = self.storage.get_all_products()
        self.table.setRowCount(len(products))

        for row, product in enumerate(products):
            self._set_table_row(row, product)

    def _set_table_row(self, row: int, product: Product) -> None:
        """Set table row data for a product."""
        # Name (truncated if too long)
        name = product.name
        if len(name) > 60:
            name = name[:57] + "..."
        name_item = QTableWidgetItem(name)
        name_item.setToolTip(product.name)  # Show full name on hover
        name_item.setData(Qt.ItemDataRole.UserRole, product.id)
        self.table.setItem(row, 0, name_item)

        # URL (truncated)
        url = product.url
        if len(url) > 50:
            url = url[:47] + "..."
        self.table.setItem(row, 1, QTableWidgetItem(url))

        # Price
        price_text = (
            f"{product.current_price:.2f}"
            if product.current_price
            else "—"
        )
        self.table.setItem(row, 2, QTableWidgetItem(price_text))

        # Change
        change_text = "—"
        if product.current_price and product.previous_price:
            diff = product.current_price - product.previous_price
            percent = (diff / product.previous_price) * 100
            sign = "+" if diff > 0 else ""
            change_text = f"{sign}{percent:.1f}%"
        change_item = QTableWidgetItem(change_text)
        if product.has_price_dropped():
            change_item.setForeground(Qt.GlobalColor.darkGreen)
        self.table.setItem(row, 3, change_item)

        # Last checked
        last_checked_text = (
            product.last_checked.strftime("%d.%m.%Y %H:%M")
            if product.last_checked
            else "Никога"
        )
        self.table.setItem(row, 4, QTableWidgetItem(last_checked_text))

        # Status
        status = "✓" if product.current_price else "?"
        self.table.setItem(row, 5, QTableWidgetItem(status))

    def _get_selected_product(self) -> Optional[Product]:
        """Get currently selected product."""
        selected = self.table.selectedItems()
        if not selected:
            return None

        row = selected[0].row()
        name_item = self.table.item(row, 0)
        if not name_item:
            return None

        product_id = name_item.data(Qt.ItemDataRole.UserRole)
        return self.storage.get_product(product_id)

    def _on_selection_changed(self) -> None:
        """Handle selection change."""
        product = self._get_selected_product()
        has_selection = product is not None

        self.edit_action.setEnabled(has_selection)
        self.delete_action.setEnabled(has_selection)

        if product:
            history = self.storage.get_price_history(product.id, limit=50)
            self.chart_widget.set_data(product, history)
        else:
            self.chart_widget.clear()

    def _on_double_click(self, row: int, column: int) -> None:
        """Handle double click on table row."""
        self._edit_product()

    def _add_product(self) -> None:
        """Show add product dialog."""
        dialog = ProductDialog(self)
        if dialog.exec():
            product = dialog.get_product()
            self.storage.add_product(product)
            self._load_products()
            self.status_label.setText(f"Добавен: {product.name}")

    def _edit_product(self) -> None:
        """Show edit product dialog."""
        product = self._get_selected_product()
        if not product:
            return

        dialog = ProductDialog(self, product)
        if dialog.exec():
            updated = dialog.get_product()
            self.storage.update_product(updated)
            self._load_products()
            self.status_label.setText(f"Обновен: {updated.name}")

    def _delete_product(self) -> None:
        """Delete selected product."""
        product = self._get_selected_product()
        if not product:
            return

        reply = QMessageBox.question(
            self,
            "Потвърждение",
            f"Сигурни ли сте, че искате да изтриете '{product.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.storage.delete_product(product.id)
            self._load_products()
            self.chart_widget.clear()
            self.status_label.setText(f"Изтрит: {product.name}")

    def _refresh_prices(self) -> None:
        """Manually refresh all prices."""
        if not self.checker:
            return

        self.status_label.setText("Обновяване на цените...")
        self.refresh_action.setEnabled(False)

        # Run in background thread to avoid blocking UI
        def run_refresh():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.checker.check_all_products())
            finally:
                loop.close()
            # Signal completion back to main thread
            QTimer.singleShot(0, self._on_refresh_complete)

        thread = threading.Thread(target=run_refresh, daemon=True)
        thread.start()

    def _on_refresh_complete(self) -> None:
        """Called when refresh is complete."""
        self._load_products()
        self.refresh_action.setEnabled(True)
        self.status_label.setText("Обновяването завърши")

    def _toggle_tracking(self) -> None:
        """Start or stop automatic tracking."""
        if not self.checker:
            return

        if self.checker.is_running():
            self.checker.stop()
            self.start_action.setText("▶️ Старт")
            self.status_label.setText("Автоматичното следене е спряно")
            self.next_check_label.setText("")
        else:
            self.checker.start()
            self.start_action.setText("⏹️ Стоп")
            self.status_label.setText("Автоматичното следене е активно")

    def _on_price_update(self, update: PriceUpdate) -> None:
        """Handle price update from background checker."""
        # Emit signal to ensure GUI update on main thread
        self.price_updated.emit(update)

    def _on_price_updated_signal(self, update: PriceUpdate) -> None:
        """Handle price update signal on main thread."""
        if update.success and update.product.should_notify():
            # Send notifications in background thread
            def send_notifications():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._send_notifications(update))
                finally:
                    loop.close()

            thread = threading.Thread(target=send_notifications, daemon=True)
            thread.start()

        self._load_products()

    async def _send_notifications(self, update: PriceUpdate) -> None:
        """Send email and Discord notifications."""
        if self.email_notifier.is_configured():
            await self.email_notifier.send_price_alert(
                update.product,
                update.old_price,
                update.new_price,
            )

        if self.discord_notifier.is_configured():
            await self.discord_notifier.send_price_alert(
                update.product,
                update.old_price,
                update.new_price,
            )

    def _on_check_complete(self, success: int, total: int) -> None:
        """Handle check completion."""
        self.status_label.setText(
            f"Проверени: {success}/{total} продукта"
        )

    def _update_status_bar(self) -> None:
        """Update status bar with next check time."""
        if self.checker and self.checker.is_running():
            next_run = self.checker.get_next_run_time()
            if next_run:
                time_str = next_run.strftime("%H:%M:%S")
                self.next_check_label.setText(f"Следваща проверка: {time_str}")
        else:
            self.next_check_label.setText("")

    def _import_csv(self) -> None:
        """Import products from CSV."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт от CSV",
            "",
            "CSV файлове (*.csv)",
        )
        if filepath:
            try:
                products = DataExporter.import_products_from_csv(filepath)
                for product in products:
                    self.storage.add_product(product)
                self._load_products()
                self.status_label.setText(
                    f"Импортирани {len(products)} продукта"
                )
            except (FileNotFoundError, ValueError) as e:
                QMessageBox.warning(self, "Грешка", str(e))

    def _import_json(self) -> None:
        """Import products from JSON."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт от JSON",
            "",
            "JSON файлове (*.json)",
        )
        if filepath:
            try:
                products = DataExporter.import_products_from_json(filepath)
                for product in products:
                    self.storage.add_product(product)
                self._load_products()
                self.status_label.setText(
                    f"Импортирани {len(products)} продукта"
                )
            except (FileNotFoundError, ValueError) as e:
                QMessageBox.warning(self, "Грешка", str(e))

    def _export_csv(self) -> None:
        """Export products to CSV."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Експорт към CSV",
            "products.csv",
            "CSV файлове (*.csv)",
        )
        if filepath:
            try:
                products = self.storage.get_all_products()
                DataExporter.export_products_to_csv(products, filepath)
                self.status_label.setText(
                    f"Експортирани {len(products)} продукта"
                )
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Успешно експортирани {len(products)} продукта",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Грешка",
                    f"Грешка при експорт: {str(e)}",
                )

    def _export_json(self) -> None:
        """Export products to JSON."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Експорт към JSON",
            "products.json",
            "JSON файлове (*.json)",
        )
        if filepath:
            try:
                products = self.storage.get_all_products()
                DataExporter.export_products_to_json(products, filepath)
                self.status_label.setText(
                    f"Експортирани {len(products)} продукта"
                )
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Успешно експортирани {len(products)} продукта",
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Грешка",
                    f"Грешка при експорт: {str(e)}",
                )

    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec():
            self.settings = dialog.get_settings()
            self.storage.save_settings(self.settings)

            # Update components
            self.email_notifier = EmailNotifier.from_settings(self.settings)
            self.discord_notifier = DiscordNotifier.from_settings(self.settings)

            if self.checker:
                self.checker.set_interval(
                    self.settings.get("check_interval_minutes", 60)
                )

            self.status_label.setText("Настройките са запазени")

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "За Price Tracker",
            """<h2>Price Tracker</h2>
            <p>Версия 1.0.0</p>
            <p>Приложение за следене на цени от онлайн магазини.</p>
            <p><b>Функции:</b></p>
            <ul>
                <li>Следене на цени от различни магазини</li>
                <li>Автоматична проверка на цени</li>
                <li>Известия по имейл и Discord</li>
                <li>История на цените с графики</li>
                <li>Импорт/Експорт на данни</li>
            </ul>
            """,
        )

    # Drag and drop support
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        mime_data = event.mimeData()
        if mime_data and (mime_data.hasUrls() or mime_data.hasText()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event."""
        mime_data = event.mimeData()
        if not mime_data:
            return

        url = ""
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                url = urls[0].toString()
        elif mime_data.hasText():
            text = mime_data.text()
            if text and text.startswith(("http://", "https://")):
                url = text

        if url:
            dialog = ProductDialog(self)
            dialog.set_url(url)
            if dialog.exec():
                product = dialog.get_product()
                self.storage.add_product(product)
                self._load_products()
                self.status_label.setText(f"Добавен: {product.name}")

    def closeEvent(self, event) -> None:
        """Handle window close."""
        if self.checker:
            self.checker.stop()
        event.accept()
