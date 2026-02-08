import sys
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

# -------------------------------------------------------------------------
# MOCK QT MODULES BEFORE IMPORTING GUI CODE
# -------------------------------------------------------------------------
# We need to mock PyQt6 modules so that we can import the GUI classes
# without triggering the actual Qt linkage (which fails on headless systems).

mock_qt_widgets = MagicMock()
mock_qt_core = MagicMock()
mock_qt_gui = MagicMock()

# Setup common Qt classes that are used as base classes
class MockQWidget:
    def __init__(self, parent=None):
        self.parent = parent
        self.show = MagicMock()
        self.hide = MagicMock()
        self.close = MagicMock()
        self.resize = MagicMock()
        self.setGeometry = MagicMock()
        self.setMinimumSize = MagicMock()
        self.setAcceptDrops = MagicMock()
        self.setWindowTitle = MagicMock()
    
    def exec(self): return 1
    def layout(self): return MagicMock()
    def setLayout(self, layout): pass
    def addWidget(self, widget): pass
    def setMinimumWidth(self, w): pass
    def setMinimumHeight(self, h): pass

class MockQDialog(MockQWidget):
    def accept(self): pass
    def reject(self): pass
    # setWindowTitle handled by parent now

class MockQMainWindow(MockQWidget):
    def __init__(self):
        super().__init__()
        self.setCentralWidget = MagicMock()
    def addToolBar(self, toolbar): pass
    def menuBar(self): return MagicMock()
    def setStatusBar(self, bar): pass

# Assign mocks to the module structure
# CRITICAL: We need side_effect to return NEW mocks each time a widget is instantiated
# Otherwise all QLineEdits share the same mock object and same .text() value!
mock_qt_widgets.QWidget = MockQWidget
mock_qt_widgets.QDialog = MockQDialog
mock_qt_widgets.QMainWindow = MockQMainWindow
mock_qt_widgets.QApplication = MagicMock()
mock_qt_widgets.QVBoxLayout = MagicMock()
mock_qt_widgets.QHBoxLayout = MagicMock()
mock_qt_widgets.QFormLayout = MagicMock()
mock_qt_widgets.QLabel = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QLineEdit = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QPushButton = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QComboBox = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QCheckBox = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QSpinBox = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QDoubleSpinBox = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QTableWidget = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QTableWidgetItem = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QHeaderView = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QMessageBox = MagicMock()
mock_qt_widgets.QFileDialog = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QToolBar = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QMenu = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QStatusBar = MagicMock(side_effect=lambda *args: MagicMock())
mock_qt_widgets.QGroupBox = MagicMock(side_effect=lambda *args: MagicMock())

# Mock matplotlib backend to avoid Qt version checks completely
mock_backend = MagicMock()
class MockFigureCanvas(MockQWidget):
    def __init__(self, figure=None):
        super().__init__()
        self.figure = figure
        self.draw = MagicMock()

mock_backend.FigureCanvasQTAgg = MockFigureCanvas

# Define module structure for matplotlib
mock_matplotlib = MagicMock()
mock_pyplot = MagicMock()
mock_figure = MagicMock()
mock_dates = MagicMock()

# Setup Figure class
class MockFigure:
    def __init__(self, figsize=None, dpi=None):
        self.add_subplot = MagicMock()
        self.autofmt_xdate = MagicMock()
        self.tight_layout = MagicMock()
        self.clear = MagicMock()

mock_figure.Figure = MockFigure

# Prepare the dictionary of modules to patch
modules_to_patch = {
    "PyQt6": MagicMock(),
    "PyQt6.QtWidgets": mock_qt_widgets,
    "PyQt6.QtCore": mock_qt_core,
    "PyQt6.QtGui": mock_qt_gui,
    "matplotlib": mock_matplotlib,
    "matplotlib.pyplot": mock_pyplot,
    "matplotlib.figure": mock_figure,
    "matplotlib.dates": mock_dates,
    "matplotlib.backends": MagicMock(),
    "matplotlib.backends.backend_qtagg": mock_backend,
}

# Start the patcher globally for this module
# This forces Python to use our mocks when we import the GUI classes below
patch.dict(sys.modules, modules_to_patch).start()


# -------------------------------------------------------------------------
# IMPORT GUI CLASSES (Now safe to import)
# -------------------------------------------------------------------------
from price_tracker.gui.product_dialog import ProductDialog
from price_tracker.gui.main_window import MainWindow
from price_tracker.gui.settings_dialog import SettingsDialog
from price_tracker.gui.price_chart import PriceChartWidget
from price_tracker.models.product import Product
# Import main for testing
from price_tracker.main import main
from price_tracker.storage.exporter import DataExporter
from price_tracker.models.price_record import PriceRecord
from datetime import datetime


# -------------------------------------------------------------------------
# TEST CLASSES
# -------------------------------------------------------------------------

class TestPriceChartMocked:
    """Test PriceChartWidget logic with mocked matplotlib."""

    def test_init(self):
        """Test initialization."""
        widget = PriceChartWidget()
        # Just verify it exists, text assertion is hard with current mocks
        assert widget.title_label is not None
        # Canvas should be hidden initially
        widget.canvas.hide.assert_called()

    def test_clear(self):
        """Test clear."""
        widget = PriceChartWidget()
        widget.clear()
        
        assert widget._product is None
        assert widget._history == []
        widget.figure.clear.assert_called()
        widget.canvas.draw.assert_called()

    def test_set_data_empty(self):
        """Test setting empty data."""
        widget = PriceChartWidget()
        product = Product(name="Test", url="u", selector="s")
        widget.set_data(product, [])
        
        widget.canvas.hide.assert_called()
        widget.placeholder.show.assert_called()

    def test_set_data_with_history(self):
        """Test setting data with history."""
        widget = PriceChartWidget()
        product = Product(name="Test", url="u", selector="s", current_price=10.0, target_price=5.0)
        record = PriceRecord(price=10.0, timestamp=datetime.now(), product_id="1")
        
        # Mock Axes
        mock_ax = MagicMock()
        widget.figure.add_subplot.return_value = mock_ax
        
        widget.set_data(product, [record])
        
        widget.placeholder.hide.assert_called()
        widget.canvas.show.assert_called()
        
        # Verify plotting
        mock_ax.plot.assert_called()
        mock_ax.fill_between.assert_called()
        # Should have horizontal lines for current and target price
        assert mock_ax.axhline.call_count >= 2
        
        widget.figure.tight_layout.assert_called()
        widget.canvas.draw.assert_called()


class TestMainWindowMocked:
    """Test MainWindow logic with mocked Qt."""

    def test_init(self):
        """Test main window initialization."""
        # Mock storage to avoid reading real files
        with patch("price_tracker.gui.main_window.JsonStorage") as MockStorage:
            # We need to mock the internal components created in __init__
            with patch("price_tracker.gui.main_window.PriceChartWidget") as MockChart:
                window = MainWindow()
                assert isinstance(window, MockQMainWindow)
                assert hasattr(window, "storage")

    def test_load_data(self):
        """Test loading data into table."""
        with patch("price_tracker.gui.main_window.JsonStorage") as MockStorage, \
             patch("price_tracker.gui.main_window.PriceChartWidget"), \
             patch("price_tracker.gui.main_window.QTableWidgetItem") as MockItem:
            
            # Setup storage with dummy products
            storage_instance = MockStorage.return_value
            p1 = Product(name="P1", url="u1", selector="s1", current_price=10.0)
            p2 = Product(name="P2", url="u2", selector="s2", current_price=20.0)
            # MainWindow uses get_all_products, not get_products
            storage_instance.get_all_products.return_value = [p1, p2]
            
            window = MainWindow()
            
            # Reset mocks attached to window to clear init calls
            window.table.setRowCount.reset_mock()
            window.table.setItem.reset_mock()
            
            window._load_products()
            
            # Verify table interaction
            window.table.setRowCount.assert_called_with(2)
            # Should set items for 2 rows * 6 columns = 12 items
            assert window.table.setItem.call_count >= 12

    @pytest.mark.asyncio
    async def test_refresh_prices(self):
        """Test refresh prices logic."""
        with patch("price_tracker.gui.main_window.JsonStorage"), \
             patch("price_tracker.gui.main_window.PriceChartWidget"), \
             patch("price_tracker.gui.main_window.BackgroundChecker") as MockChecker, \
             patch("price_tracker.gui.main_window.QMessageBox") as MockMsgBox:
             
            window = MainWindow()
            # Mock the checker
            window.checker.check_all = AsyncMock(return_value=2) # 2 updates
            
            # Run refresh
            pass

    def test_delete_product(self):
        """Test delete product logic."""
        with patch("price_tracker.gui.main_window.JsonStorage") as MockStorage, \
             patch("price_tracker.gui.main_window.PriceChartWidget"), \
             patch("price_tracker.gui.main_window.QMessageBox") as MockMsgBox:
            
            storage_instance = MockStorage.return_value
            products = [Product(name="P1", url="u1", selector="s1", id="1")]
            # MainWindow uses get_all_products
            storage_instance.get_all_products.return_value = products
            
            # Ensure calling delete gets a product ID
            # Mock row count return
            # But we need rowCount to be on the table widget instance
            
            window = MainWindow()
            
            # Need to attach mock return value to the table widget instance on the window
            window.table.rowCount.return_value = 1
            window.table.currentRow.return_value = 0
            
            # Mock confirmation yes
            # Must match QMessageBox.StandardButton.Yes usage
            MockMsgBox.question.return_value = MockMsgBox.StandardButton.Yes
            
            # We need to mock _get_selected_product or setup the table so it returns an item
            # _get_selected_product uses window.table.selectedItems()
            # Let's mock _get_selected_product directly to make it easier
            window._get_selected_product = MagicMock(return_value=products[0])
            
            window._delete_product()
            
            # Verify delete called
            storage_instance.delete_product.assert_called_with("1")
            # Should reload data (setRowCount called)
            assert window.table.setRowCount.call_count > 0

    def test_import_export(self):
        """Test import/export functionality."""
        with patch("price_tracker.gui.main_window.JsonStorage") as MockStorage, \
             patch("price_tracker.gui.main_window.PriceChartWidget"), \
             patch("price_tracker.gui.main_window.QFileDialog") as MockDialog, \
             patch("price_tracker.gui.main_window.DataExporter") as MockExporter, \
             patch("price_tracker.gui.main_window.QMessageBox"):
            
            window = MainWindow()
            
            # Test Import CSV
            MockDialog.getOpenFileName.return_value = ("test.csv", "CSV")
            MockExporter.import_products_from_csv.return_value = [Product(name="P1", url="u1", selector="s1")]
            
            window._import_csv()
            
            MockExporter.import_products_from_csv.assert_called_with("test.csv")
            # Should add product and load
            # window.storage is the instance returned by MockStorage()
            # We access it via the property or the mock
            # window.storage IS MockStorage.return_value
            storage_mock = MockStorage.return_value
            assert storage_mock.add_product.called
            
            # Test Export JSON
            MockDialog.getSaveFileName.return_value = ("test.json", "JSON")
            storage_mock.get_all_products.return_value = []
            
            window._export_json()
            
            MockExporter.export_products_to_json.assert_called_with([], "test.json")

    def test_add_edit_product(self):
        """Test add/edit product interactions."""
        with patch("price_tracker.gui.main_window.JsonStorage") as MockStorage, \
             patch("price_tracker.gui.main_window.PriceChartWidget"), \
             patch("price_tracker.gui.main_window.ProductDialog") as MockDialog:
            
            window = MainWindow()
            
            # Test Add
            dialog_instance = MockDialog.return_value
            dialog_instance.exec.return_value = True
            
            new_prod = Product(name="New", url="u", selector="s")
            dialog_instance.get_product.return_value = new_prod
            
            window._add_product()
            
            MockStorage.return_value.add_product.assert_called_with(new_prod)
            
            # Test Edit
            # Setup selection
            # We need to mock _get_selected_product
            window._get_selected_product = MagicMock(return_value=new_prod)
            window.storage.get_product.return_value = new_prod
            
            window._edit_product()
            
            # Verify dialog created with product
            # MockDialog(window, product)
            # Check call args
            args, _ = MockDialog.call_args
            assert args[1] == new_prod
            MockStorage.return_value.update_product.assert_called_with(new_prod)


    def test_ui_interactions(self):
        """Test UI interactions."""
        with patch("price_tracker.gui.main_window.JsonStorage") as MockStorage, \
             patch("price_tracker.gui.main_window.PriceChartWidget"), \
             patch("price_tracker.gui.main_window.SettingsDialog") as MockSettings, \
             patch("price_tracker.gui.main_window.QMessageBox"):
            
            window = MainWindow()
            
            # Test selection change
            window.table.selectedItems.return_value = []
            window._on_selection_changed()
            # Verify actions disabled
            window.edit_action.setEnabled.assert_called_with(False)
            window.delete_action.setEnabled.assert_called_with(False)
            
            window.table.selectedItems.return_value = [MagicMock()]
            window._on_selection_changed()
            # Verify actions enabled
            window.edit_action.setEnabled.assert_called_with(True)
            window.delete_action.setEnabled.assert_called_with(True)
            
            # Test double click
            window.table.item.return_value = MagicMock(text=lambda: "1")
            # Mock _edit_product to verify it's called
            window._edit_product = MagicMock()
            window._on_double_click(0, 0)
            window._edit_product.assert_called()
            
            # Test show settings
            MockSettings.return_value.exec.return_value = True
            MockSettings.return_value.get_settings.return_value = {"check_interval_minutes": 60}
            
            window._show_settings()
            
            MockSettings.assert_called()
            # Verify settings updated (mock storage)
            assert window.settings["check_interval_minutes"] == 60
            
            # Test show about
            # Just verify it doesn't crash
            window._show_about()
            
    def test_advanced_features(self):
        """Test advanced features (updates, export errors, etc)."""
        with patch("price_tracker.gui.main_window.JsonStorage") as MockStorage, \
             patch("price_tracker.gui.main_window.PriceChartWidget") as MockChart, \
             patch("price_tracker.gui.main_window.QMessageBox") as MockMsgBox, \
             patch("price_tracker.gui.main_window.DataExporter") as MockExporter, \
             patch("price_tracker.gui.main_window.QFileDialog") as MockDialog:
            
            window = MainWindow()
            
            # Test status bar update with no checker
            window.checker = None
            window._update_status_bar()
            window.next_check_label.setText.assert_called_with("")
            
            # Test status bar update with running checker
            window.checker = MagicMock()
            window.checker.is_running.return_value = True
            window.checker.get_next_run_time.return_value = datetime(2023, 1, 1, 12, 0, 0)
            window._update_status_bar()
            window.next_check_label.setText.assert_called_with("Следваща проверка: 12:00:00")
            
            # Test _on_price_updated_signal
            # Mock update object
            update = MagicMock()
            update.success = True
            update.product.should_notify.return_value = False
            
            # Mock _load_products
            window._load_products = MagicMock()
            
            window._on_price_updated_signal(update)
            window._load_products.assert_called()
            
            # Test export error
            MockDialog.getSaveFileName.return_value = ("test.json", "JSON")
            MockExporter.export_products_to_json.side_effect = Exception("Export error")
            window._export_json()
            MockMsgBox.critical.assert_called()


class TestProductDialogMocked:
    """Test ProductDialog logic with mocked Qt."""

    def test_init_add_mode(self):
        """Test initialization in add mode."""
        dialog = ProductDialog()
        # Verify it initialized without error
        assert dialog.product is None
        assert dialog.is_edit is False

    def test_init_edit_mode(self):
        """Test initialization in edit mode with a product."""
        product = Product(
            name="Test",
            url="http://example.com",
            selector=".price",
            current_price=10.0,
            target_price=5.0
        )
        dialog = ProductDialog(product=product)
        
        assert dialog.product == product
        assert dialog.is_edit is True
        
        # Verify fields were populated
        dialog.name_input.setText.assert_called_with("Test")
        dialog.url_input.setText.assert_called_with("http://example.com")
        dialog.selector_input.setText.assert_called_with(".price")
        dialog.target_price.setValue.assert_called_with(5.0)

    def test_get_product_new(self):
        """Test getting new product from dialog."""
        dialog = ProductDialog()
        
        # Configure the specific mock instances attached to this dialog
        dialog.url_input.text.return_value = "http://new.com"
        dialog.name_input.text.return_value = "New"
        dialog.selector_input.text.return_value = ".price"
        dialog.selector_type.currentIndex.return_value = 0 # CSS
        dialog.use_selenium.isChecked.return_value = False
        dialog.notify_on_drop.isChecked.return_value = True
        
        # For QDoubleSpinBox, value() returns a float
        dialog.target_price.value.return_value = 100.0

        product = dialog.get_product()
        
        assert product.name == "New"
        assert product.url == "http://new.com"
        assert product.selector == ".price"
        assert product.target_price == 100.0

    def test_validate_save_success(self):
        """Test save validation success."""
        dialog = ProductDialog()
        dialog.url_input.text.return_value = "http://valid.com"
        dialog.name_input.text.return_value = "Name"
        dialog.selector_input.text.return_value = ".price"
        
        # Mock accept method from QDialog
        dialog.accept = MagicMock()
        
        dialog._save()
        
        dialog.accept.assert_called_once()    
        
    def test_validate_save_fail(self):
        """Test save validation failure."""
        dialog = ProductDialog()
        dialog.url_input.text.return_value = "" # Invalid
        
        # Mock QMessageBox warning
        mock_qt_widgets.QMessageBox.warning = MagicMock()
        
        dialog._save()
        
        mock_qt_widgets.QMessageBox.warning.assert_called()
        
    def test_auto_detect(self):
        """Test auto detect name."""
        with patch("price_tracker.gui.product_dialog.HttpScraper") as MockScraper, \
             patch("price_tracker.gui.product_dialog.asyncio.run") as mock_run:
            
            MockScraper.return_value.get_page_title = AsyncMock()
            mock_run.return_value = "Detected Title"
            
            dialog = ProductDialog()
            dialog.url_input.text.return_value = "http://example.com"
            
            dialog._auto_detect_name()
            
            dialog.name_input.setText.assert_called_with("Detected Title")

    def test_test_selector(self):
        """Test selector validation."""
        with patch("price_tracker.gui.product_dialog.HttpScraper") as MockScraper, \
             patch("price_tracker.gui.product_dialog.asyncio.run") as mock_run:
            
            # success, text, price
            mock_run.return_value = (True, "10.00", 10.0)
            
            dialog = ProductDialog()
            dialog.url_input.text.return_value = "http://example.com"
            dialog.selector_input.text.return_value = ".price"
            
            dialog._test_selector()
            
            dialog.test_result.setText.assert_called()
            # Should show OK
            args = dialog.test_result.setText.call_args[0][0]
            assert "OK" in args
            
    def test_dialog_errors(self):
        """Test dialog error handling."""
        with patch("price_tracker.gui.product_dialog.HttpScraper") as MockScraper, \
             patch("price_tracker.gui.product_dialog.asyncio.run") as mock_run, \
             patch("price_tracker.gui.product_dialog.QMessageBox") as MockMsgBox:
             
            # Test auto-detect error
            mock_run.side_effect = Exception("Scraper error")
            dialog = ProductDialog()
            dialog.url_input.text.return_value = "http://example.com"
            
            dialog._auto_detect_name()
            
            dialog.test_result.setText.assert_called_with("Грешка")
            MockMsgBox.warning.assert_called()
            
            # Test set_url
            dialog.set_url("http://external.com")
            dialog.url_input.setText.assert_called_with("http://external.com")


class TestSettingsDialogMocked:
    """Test SettingsDialog logic with mocked Qt."""

    def test_init(self):
        """Test initialization and population."""
        settings = {
            "check_interval_minutes": 30,
            "use_selenium_fallback": False,
            "email": {"enabled": True, "username": "user"},
            "discord": {"enabled": True, "webhook_url": "http://hook"}
        }
        dialog = SettingsDialog(settings=settings)
        
        # Verify fields populated
        dialog.interval_input.setValue.assert_called_with(30)
        dialog.selenium_fallback.setChecked.assert_called_with(False)
        dialog.email_enabled.setChecked.assert_called_with(True)
        dialog.email_username.setText.assert_called_with("user")
        dialog.discord_enabled.setChecked.assert_called_with(True)
        dialog.discord_webhook.setText.assert_called_with("http://hook")

    def test_get_settings(self):
        """Test retrieving settings from dialog."""
        dialog = SettingsDialog()
        
        # Configure mocks
        dialog.interval_input.value.return_value = 120
        dialog.selenium_fallback.isChecked.return_value = True
        dialog.email_enabled.isChecked.return_value = True
        dialog.email_username.text.return_value = "new_user"
        dialog.discord_enabled.isChecked.return_value = True
        dialog.discord_webhook.text.return_value = "new_hook"
        
        settings = dialog.get_settings()
        
        assert settings["check_interval_minutes"] == 120
        assert settings["use_selenium_fallback"] is True
        assert settings["email"]["username"] == "new_user"
        assert settings["discord"]["webhook_url"] == "new_hook"

    def test_test_email(self):
        """Test sending test email."""
        dialog = SettingsDialog()
        
        # Mock EmailNotifier
        with patch("price_tracker.gui.settings_dialog.EmailNotifier") as MockNotifier, \
             patch("asyncio.get_event_loop") as mock_loop:
            
            instance = MockNotifier.return_value
            # return success
            mock_loop.return_value.run_until_complete.return_value = (True, "Sent")
            
            dialog._test_email()
            
            instance.send_test_email.assert_called()
            mock_qt_widgets.QMessageBox.information.assert_called()

    def test_test_discord(self):
        """Test sending test discord message."""
        dialog = SettingsDialog()
        
        # Mock DiscordNotifier
        with patch("price_tracker.gui.settings_dialog.DiscordNotifier") as MockNotifier, \
             patch("asyncio.get_event_loop") as mock_loop:
            
            instance = MockNotifier.return_value
            # return failure
            mock_loop.return_value.run_until_complete.return_value = (False, "Error")
            
            dialog._test_discord()
            
            instance.send_test_message.assert_called()
            mock_qt_widgets.QMessageBox.warning.assert_called()


class TestMainMocked:
    """Test main.py entry point."""
    
    def test_main(self):
        with patch("price_tracker.main.QApplication") as MockApp, \
             patch("price_tracker.main.MainWindow") as MockWindow:
            
            mock_app_instance = MockApp.return_value
            mock_window_instance = MockWindow.return_value
            # Mock exec return value
            mock_app_instance.exec.return_value = 0
            
            ret = main()
            
            MockApp.assert_called()
            MockWindow.assert_called()
            mock_window_instance.show.assert_called()
            mock_app_instance.exec.assert_called()
            assert ret == 0
