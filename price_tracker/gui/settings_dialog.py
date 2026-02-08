"""Settings dialog for application configuration."""

import asyncio
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QTabWidget,
    QWidget,
    QMessageBox,
)

from price_tracker.notifications.email_notifier import EmailNotifier, EmailConfig
from price_tracker.notifications.discord_notifier import DiscordNotifier, DiscordConfig


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, parent=None, settings: dict = None) -> None:
        super().__init__(parent)

        self.settings = settings or {}
        self._setup_ui()
        self._populate_fields()

    def _setup_ui(self) -> None:
        """Setup dialog UI."""
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # General tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        general_group = QGroupBox("Общи настройки")
        general_form = QFormLayout(general_group)

        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 1440)
        self.interval_input.setSuffix(" мин.")
        self.interval_input.setValue(60)
        general_form.addRow("Интервал на проверка:", self.interval_input)

        self.selenium_fallback = QCheckBox("Използвай Selenium ако HTTP не работи")
        self.selenium_fallback.setChecked(True)
        general_form.addRow("", self.selenium_fallback)

        general_layout.addWidget(general_group)
        general_layout.addStretch()

        tabs.addTab(general_tab, "Общи")

        # Email tab
        email_tab = QWidget()
        email_layout = QVBoxLayout(email_tab)

        email_group = QGroupBox("Email настройки")
        email_form = QFormLayout(email_group)

        self.email_enabled = QCheckBox("Активирай email известия")
        email_form.addRow("", self.email_enabled)

        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("smtp.gmail.com")
        email_form.addRow("SMTP сървър:", self.smtp_server)

        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        email_form.addRow("Порт:", self.smtp_port)

        self.email_username = QLineEdit()
        self.email_username.setPlaceholderText("email@gmail.com")
        email_form.addRow("Потребител:", self.email_username)

        self.email_password = QLineEdit()
        self.email_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.email_password.setPlaceholderText("Парола или App Password")
        email_form.addRow("Парола:", self.email_password)

        self.email_from = QLineEdit()
        self.email_from.setPlaceholderText("email@gmail.com")
        email_form.addRow("От:", self.email_from)

        self.email_to = QLineEdit()
        self.email_to.setPlaceholderText("recipient@example.com")
        email_form.addRow("До:", self.email_to)

        # Test button
        test_email_btn = QPushButton("Изпрати тестов имейл")
        test_email_btn.clicked.connect(self._test_email)
        email_form.addRow("", test_email_btn)

        email_layout.addWidget(email_group)
        email_layout.addStretch()

        tabs.addTab(email_tab, "Email")

        # Discord tab
        discord_tab = QWidget()
        discord_layout = QVBoxLayout(discord_tab)

        discord_group = QGroupBox("Discord настройки")
        discord_form = QFormLayout(discord_group)

        self.discord_enabled = QCheckBox("Активирай Discord известия")
        discord_form.addRow("", self.discord_enabled)

        self.discord_webhook = QLineEdit()
        self.discord_webhook.setPlaceholderText("https://discord.com/api/webhooks/...")
        discord_form.addRow("Webhook URL:", self.discord_webhook)

        # Test button
        test_discord_btn = QPushButton("Изпрати тестово съобщение")
        test_discord_btn.clicked.connect(self._test_discord)
        discord_form.addRow("", test_discord_btn)

        discord_layout.addWidget(discord_group)
        discord_layout.addStretch()

        tabs.addTab(discord_tab, "Discord")

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Отказ")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Запази")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self) -> None:
        """Populate fields from settings."""
        self.interval_input.setValue(
            self.settings.get("check_interval_minutes", 60)
        )
        self.selenium_fallback.setChecked(
            self.settings.get("use_selenium_fallback", True)
        )

        # Email settings
        email = self.settings.get("email", {})
        self.email_enabled.setChecked(email.get("enabled", False))
        self.smtp_server.setText(email.get("smtp_server", ""))
        self.smtp_port.setValue(email.get("smtp_port", 587))
        self.email_username.setText(email.get("username", ""))
        self.email_password.setText(email.get("password", ""))
        self.email_from.setText(email.get("from_address", ""))
        self.email_to.setText(email.get("to_address", ""))

        # Discord settings
        discord = self.settings.get("discord", {})
        self.discord_enabled.setChecked(discord.get("enabled", False))
        self.discord_webhook.setText(discord.get("webhook_url", ""))

    def get_settings(self) -> dict:
        """Get settings from dialog fields."""
        return {
            "check_interval_minutes": self.interval_input.value(),
            "use_selenium_fallback": self.selenium_fallback.isChecked(),
            "email": {
                "enabled": self.email_enabled.isChecked(),
                "smtp_server": self.smtp_server.text().strip(),
                "smtp_port": self.smtp_port.value(),
                "username": self.email_username.text().strip(),
                "password": self.email_password.text(),
                "from_address": self.email_from.text().strip(),
                "to_address": self.email_to.text().strip(),
            },
            "discord": {
                "enabled": self.discord_enabled.isChecked(),
                "webhook_url": self.discord_webhook.text().strip(),
            },
        }

    def _test_email(self) -> None:
        """Send test email."""
        config = EmailConfig(
            smtp_server=self.smtp_server.text().strip(),
            smtp_port=self.smtp_port.value(),
            username=self.email_username.text().strip(),
            password=self.email_password.text(),
            from_address=self.email_from.text().strip(),
            to_address=self.email_to.text().strip(),
        )

        notifier = EmailNotifier(config)

        try:
            loop = asyncio.get_event_loop()
            success, message = loop.run_until_complete(notifier.send_test_email())

            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.warning(self, "Грешка", message)
        except Exception as e:
            QMessageBox.warning(self, "Грешка", str(e))

    def _test_discord(self) -> None:
        """Send test Discord message."""
        config = DiscordConfig(
            webhook_url=self.discord_webhook.text().strip(),
        )

        notifier = DiscordNotifier(config)

        try:
            loop = asyncio.get_event_loop()
            success, message = loop.run_until_complete(notifier.send_test_message())

            if success:
                QMessageBox.information(self, "Успех", message)
            else:
                QMessageBox.warning(self, "Грешка", message)
        except Exception as e:
            QMessageBox.warning(self, "Грешка", str(e))
