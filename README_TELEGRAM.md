# 🚀 Быстрый запуск Telegram бота

## Шаг 1: Настройка окружения

Отредактируйте файл `.env` (уже существует):

```env
# Fill these values in your local `.env` (do NOT commit `.env`)
TELEGRAM_BOT_TOKEN=replace-with-your-telegram-bot-token
TELEGRAM_MODE=polling
TELEGRAM_ADMIN_CHAT_IDS=123456789
```

> **Как узнать свой chat_id:**  
> Напишите боту [@userinfobot](https://t.me/userinfobot) в Telegram

## Шаг 2: Запуск бота

```bash
python manage.py run_telegram_bot
```

Бот запущен! Теперь можно тестировать.

---

## Тестирование

### Для клиента:
1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Выполните `/register` и следуйте инструкциям
4. После подтверждения админом используйте `/order`

### Для водителя:
1. Сгенерируйте код:
   ```bash
   python manage.py generate_driver_code 1
   ```
2. В боте выполните `/driver_login`
3. Введите код
4. Используйте `/my_deliveries`

### Для админа:
- Подтверждайте регистрации в Django Admin
- Назначайте водителей на заказы
- Получайте уведомления в Telegram

---

## Команды бота

**Клиенты:**
- `/start` - Начать
- `/register` - Регистрация
- `/catalog` - Каталог
- `/order` - Заказать
- `/myorders` - Мои заказы

**Водители:**
- `/driver_login` - Войти
- `/my_deliveries` - Доставки

---

## Документация

📖 Подробная инструкция: [TELEGRAM_BOT_GUIDE.md](TELEGRAM_BOT_GUIDE.md)
