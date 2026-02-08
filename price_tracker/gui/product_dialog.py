"""Product add/edit dialog."""

import asyncio
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QPushButton,
    QLabel,
    QGroupBox,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt

from price_tracker.models.product import Product
from price_tracker.scraper.http_scraper import HttpScraper
from price_tracker.scraper.selenium_scraper import SeleniumScraper


class ProductDialog(QDialog):
    """Dialog for adding or editing a product."""

    def __init__(
        self,
        parent=None,
        product: Optional[Product] = None,
    ) -> None:
        super().__init__(parent)

        self.product = product
        self.is_edit = product is not None
        self._http_scraper = HttpScraper()
        self._selenium_scraper: Optional[SeleniumScraper] = None

        self._setup_ui()

        if product:
            self._populate_fields(product)

    def _setup_ui(self) -> None:
        """Setup dialog UI."""
        title = "Редактиране на продукт" if self.is_edit else "Добавяне на продукт"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Basic info group
        basic_group = QGroupBox("Основна информация")
        basic_layout = QFormLayout(basic_group)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/product")
        basic_layout.addRow("URL:", self.url_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Име на продукта")
        basic_layout.addRow("Име:", self.name_input)

        # Auto-detect button
        detect_btn = QPushButton("Открий име автоматично")
        detect_btn.clicked.connect(self._auto_detect_name)
        basic_layout.addRow("", detect_btn)

        layout.addWidget(basic_group)

        # Selector group
        selector_group = QGroupBox("Селектор за цена")
        selector_layout = QFormLayout(selector_group)

        self.selector_type = QComboBox()
        self.selector_type.addItems(["CSS Selector", "XPath"])
        selector_layout.addRow("Тип:", self.selector_type)

        self.selector_input = QLineEdit()
        self.selector_input.setPlaceholderText(".price, #product-price, [data-price]")
        selector_layout.addRow("Селектор:", self.selector_input)

        # Test button and result
        test_layout = QHBoxLayout()
        test_btn = QPushButton("Тествай селектора")
        test_btn.clicked.connect(self._test_selector)
        test_layout.addWidget(test_btn)

        self.test_result = QLabel("")
        test_layout.addWidget(self.test_result, 1)

        selector_layout.addRow("", test_layout)

        self.use_selenium = QCheckBox("Използвай Selenium (за динамични сайтове)")
        selector_layout.addRow("", self.use_selenium)

        layout.addWidget(selector_group)

        # Notification group
        notify_group = QGroupBox("Известяване")
        notify_layout = QFormLayout(notify_group)

        self.notify_on_drop = QCheckBox("Известявай при промяна на цена")
        self.notify_on_drop.setChecked(True)
        notify_layout.addRow("", self.notify_on_drop)

        self.target_price = QDoubleSpinBox()
        self.target_price.setRange(0, 999999)
        self.target_price.setDecimals(2)
        self.target_price.setSuffix("")
        self.target_price.setSpecialValueText("Не е зададена")
        notify_layout.addRow("Целева цена:", self.target_price)

        layout.addWidget(notify_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Отказ")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Запази")
        save_btn.clicked.connect(self._save)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self, product: Product) -> None:
        """Populate fields with product data."""
        self.url_input.setText(product.url)
        self.name_input.setText(product.name)
        self.selector_input.setText(product.selector)

        if product.selector_type == "xpath":
            self.selector_type.setCurrentIndex(1)
        else:
            self.selector_type.setCurrentIndex(0)

        self.use_selenium.setChecked(product.use_selenium)
        self.notify_on_drop.setChecked(product.notify_on_drop)

        if product.target_price:
            self.target_price.setValue(product.target_price)

    def _get_scraper(self):
        """Get the appropriate scraper based on checkbox state."""
        if self.use_selenium.isChecked():
            if self._selenium_scraper is None:
                self._selenium_scraper = SeleniumScraper(headless=True)
            return self._selenium_scraper
        return self._http_scraper

    def _auto_detect_name(self) -> None:
        """Auto-detect product name from page title."""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Грешка", "Моля, въведете URL адрес")
            return

        use_selenium = self.use_selenium.isChecked()
        if use_selenium:
            self.test_result.setText("Зареждане (Selenium)...")
        else:
            self.test_result.setText("Зареждане...")
        self.test_result.setStyleSheet("color: gray;")
        QApplication.processEvents()  # Force UI update

        try:
            scraper = self._get_scraper()
            title = asyncio.run(scraper.get_page_title(url))
            if title:
                self.name_input.setText(title)
                self.test_result.setText("OK: Намерено име")
                self.test_result.setStyleSheet("color: green;")
            else:
                hint = " (опитайте Selenium)" if not use_selenium else ""
                self.test_result.setText(f"Грешка: Не можа да се открие име{hint}")
                self.test_result.setStyleSheet("color: red;")
        except Exception as e:
            self.test_result.setText("Грешка")
            self.test_result.setStyleSheet("color: red;")
            QMessageBox.warning(self, "Грешка", str(e))

    def _test_selector(self) -> None:
        """Test the selector on the URL."""
        url = self.url_input.text().strip()
        selector = self.selector_input.text().strip()

        if not url or not selector:
            self.test_result.setText("Въведете URL и селектор")
            return

        use_selenium = self.use_selenium.isChecked()
        if use_selenium:
            self.test_result.setText("⏳ Тестване (Selenium)...")
        else:
            self.test_result.setText("⏳ Тестване...")
        self.test_result.setStyleSheet("color: gray;")
        QApplication.processEvents()  # Force UI update

        selector_type = "xpath" if self.selector_type.currentIndex() == 1 else "css"

        try:
            scraper = self._get_scraper()
            success, text, price = asyncio.run(
                scraper.test_selector(url, selector, selector_type)
            )

            if success and price is not None:
                self.test_result.setText(f"OK: {price:.2f}")
                self.test_result.setStyleSheet("color: green;")
            elif success and text:
                self.test_result.setText(f"Намерено: {text[:30]}...")
                self.test_result.setStyleSheet("color: orange;")
            else:
                hint = " (опитайте Selenium)" if not use_selenium else ""
                self.test_result.setText(f"❌ Не е намерено{hint}")
                self.test_result.setStyleSheet("color: red;")
        except Exception as e:
            self.test_result.setText(f"❌ Грешка: {str(e)[:30]}")
            self.test_result.setStyleSheet("color: red;")

    def _save(self) -> None:
        """Validate and save product."""
        url = self.url_input.text().strip()
        name = self.name_input.text().strip()
        selector = self.selector_input.text().strip()

        if not url:
            QMessageBox.warning(self, "Грешка", "Моля, въведете URL адрес")
            return

        if not name:
            QMessageBox.warning(self, "Грешка", "Моля, въведете име на продукта")
            return

        if not selector:
            QMessageBox.warning(self, "Грешка", "Моля, въведете селектор за цена")
            return

        self.accept()

    def get_product(self) -> Product:
        """Get product from dialog fields."""
        selector_type = "xpath" if self.selector_type.currentIndex() == 1 else "css"
        target = self.target_price.value() if self.target_price.value() > 0 else None

        if self.product:
            # Update existing product
            self.product.url = self.url_input.text().strip()
            self.product.name = self.name_input.text().strip()
            self.product.selector = self.selector_input.text().strip()
            self.product.selector_type = selector_type
            self.product.use_selenium = self.use_selenium.isChecked()
            self.product.notify_on_drop = self.notify_on_drop.isChecked()
            self.product.target_price = target
            return self.product
        else:
            # Create new product
            return Product(
                url=self.url_input.text().strip(),
                name=self.name_input.text().strip(),
                selector=self.selector_input.text().strip(),
                selector_type=selector_type,
                use_selenium=self.use_selenium.isChecked(),
                notify_on_drop=self.notify_on_drop.isChecked(),
                target_price=target,
            )

    def set_url(self, url: str) -> None:
        """Set URL from external source (e.g., drag and drop)."""
        self.url_input.setText(url)
        self._auto_detect_name()
