Project: water_delivery_crm — Copilot instructions for contributors

Quick summary
- **Type:** Django 4.2 monorepo with a single app `crm` that contains the web UI, data models, and an integrated Telegram bot.
- **Primary integrations:** Telegram (python-telegram-bot v20+ and a lightweight HTTP fallback), REST API via DRF, SQLite by default, file uploads to `media/`.

Key files to read first
- `water_delivery_crm/settings.py`: env-driven configuration (loads `.env`), important keys: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_MODE`, `TELEGRAM_ADMIN_CHAT_IDS`, `DATABASES`, timezone and language.
- `crm/models.py`: canonical domain model (Client, Driver, Order, Product, Route, LoyaltyProgram). Phone validation expects +992 / 992 / 9-digit formats.
- `crm/telegram_bot.py`: builds the bot Application (async python-telegram-bot) and contains an HTTP `getUpdates` fallback. See `create_application()` and usage example.
- `crm/bot_handlers.py`: Telegram conversation handlers and state constants (e.g. `REGISTRATION_NAME`, `ORDER_PRODUCT`). Update both this file and `telegram_bot.py` when changing conversation wiring.
- `crm/telegram_helpers.py`: low-level Telegram API HTTP calls (`send_notification`) — patch this when you need to stub/mute outgoing messages in tests.
- `crm/bot_keyboards.py`: keyboard layout helpers used pervasively by handlers.

Big-picture architecture and patterns
- Single Django app (`crm`) contains web views, websocket consumers, a Telegram bot integration and domain logic. The Telegram bot uses Django ORM from async handlers by calling `asgiref.sync.sync_to_async` (pattern: call DB ops through `sync_to_async`).
- Bot code is purposely split:
  - `telegram_bot.py` — wiring: application creation, handler registration, polling fallback.
  - `bot_handlers.py` — user-facing logic and conversation state constants.
  - `telegram_helpers.py` — low-level sends to Telegram REST API (synchronous `requests.post`).
  This separation keeps handler logic testable and the Application-building isolated.
- Notifications and cross-service communication: when orders/clients are created the code calls `notify_admins_new_order`, `notify_driver_new_order` which live in `telegram_helpers.py`/`telegram_bot.py` and call `send_notification` (HTTP). Tests should patch `requests.post` or `send_notification` directly.

Developer workflows (how to run & debug)
- Setup (recommended):
  - Create venv and install: `python -m venv .venv` then `& .\\.venv\\Scripts\\Activate.ps1; pip install -r requirements.txt` (PowerShell).
  - Create `.env` at the project root (settings reads it). Set: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_MODE=polling`, `TELEGRAM_ADMIN_CHAT_IDS=12345,67890`.
  - Apply migrations: `python manage.py migrate`.
  - Run Django server: `python manage.py runserver`.
- Running the Telegram bot (polling):
  - Option A (quick): run a small runner from Django shell or a management command:
    ```python
    from crm.telegram_bot import create_application
    app = create_application()
    app.run_polling()
    ```
  - Option B: set `TELEGRAM_MODE=polling` and use the project's management command if present (search `crm/management/commands`). If no command exists, the snippet above is the supported usage (also present as docstring in `telegram_bot.py`).
- Tests: `python manage.py test`. To avoid external Telegram calls in tests, patch `crm.telegram_helpers.send_notification` or `requests.post`.

Project-specific conventions
- Async handlers + sync ORM: All Telegram handlers are async. When touching the DB inside handlers, use `asgiref.sync.sync_to_async` (see `bot_handlers.py` and `telegram_bot.py`) — avoid calling Django ORM directly from async code without sync wrappers.
- Conversation states: constants are defined in `crm/bot_handlers.py` and are imported into `telegram_bot.py` when wiring ConversationHandler states — keep them stable or update both files.
- Phone numbers: `Client.phone` enforces Tajikistan formats via `phone_regex` — tests and UI expect these formats.
- Languages/timezone: `LANGUAGE_CODE` is `ru-ru` and `TIME_ZONE` is `Asia/Dushanbe`. Text in handlers is Russian; when changing copy update handlers and tests accordingly.
- Telegram admin IDs: stored in `TELEGRAM_ADMIN_CHAT_IDS` as comma-separated ints in the env and converted in settings.

Integration points and external dependencies to watch
- Telegram API: `crm/telegram_helpers.py` uses `requests.post` to call Telegram; failures are logged and return False.
- python-telegram-bot v20+ async API: `telegram_bot.py` lazily imports `telegram` objects to avoid import-time side-effects. If changing version, inspect import points and `ApplicationBuilder` usage.
- Data/analysis libs: `pandas`, `numpy`, `openpyxl` — used in views/exports. Large dataset operations may appear in `crm/views/exports.py`.

Editing guidelines and common change patterns
- When editing models, run `python manage.py makemigrations` and commit generated migration files in `crm/migrations/` (project already contains many migrations).
- When modifying bot flows (states, callback_data prefixes like `status_`, `qty_`, `simple_confirm_`), update both the handler that produces the callback and the code that parses it in `telegram_bot.py`/`bot_handlers.py`.
- To mute external Telegram traffic in local dev/tests: set an empty `TELEGRAM_BOT_TOKEN` or patch `send_notification` to a no-op in test setup.

Examples (copy-paste when editing)
- Create & run bot in a script/management command:
  ```python
  from crm.telegram_bot import create_application
  app = create_application()
  app.run_polling()
  ```
- Patch notifications in tests:
  ```python
  from unittest.mock import patch

  @patch('crm.telegram_helpers.send_notification')
  def test_order_creates_notification(mock_send, client):
      # ... create order ...
      mock_send.assert_called()
  ```

If anything in these notes is unclear or you want me to expand a section (examples for migrations, management commands, or tests), tell me which part and I'll iterate.
