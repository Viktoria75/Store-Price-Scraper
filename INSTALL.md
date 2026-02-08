# Инструкции за инсталация - Price Tracker

## Системни изисквания

- **Операционна система:** Windows 10+, macOS 10.15+, или Linux
- **Python:** 3.10 или по-нова версия
- **Браузър:** Google Chrome (за Selenium функционалност)

## Стъпка по стъпка инсталация

### 1. Проверете версията на Python

```bash
python --version
```

Ако Python не е инсталиран, изтеглете от: https://www.python.org/downloads/

### 2. Клонирайте или изтеглете проекта

```bash
git clone <repository-url>
cd Project
```

### 3. Създайте виртуална среда (препоръчително)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Инсталирайте зависимостите

**Основни зависимости:**
```bash
pip install -r requirements.txt
```

**За разработка (тестове, linting, type checking):**
```bash
pip install -r requirements-dev.txt
```

**Или чрез pyproject.toml:**
```bash
pip install -e .
pip install -e ".[dev]"
```

### 5. Стартирайте приложението

```bash
python -m price_tracker.main
```

## Отстраняване на проблеми

### PyQt6 не се инсталира

Ако имате проблеми с инсталацията на PyQt6:

```bash
pip install --upgrade pip
pip install PyQt6
```

### Selenium изисква Chrome WebDriver

WebDriver се изтегля автоматично чрез `webdriver-manager`. Уверете се, че имате интернет връзка.

### Грешка при импорт на lxml

**Windows:**
```bash
pip install lxml
```

Ако не работи, инсталирайте предварително компилиран пакет:
```bash
pip install lxml --only-binary=:all:
```

### SSL грешки

Ако получавате SSL грешки при scraping:

```bash
pip install certifi
```

## Проверка на инсталацията

Изпълнете тестовете за да проверите, че всичко работи:

```bash
pytest tests/ -v
```

