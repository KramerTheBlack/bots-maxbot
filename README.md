# MAX Bot with Mistral AI

Чат-бот для мессенджера MAX с интеграцией Mistral AI.

## Структура проекта

```
maxbot1/
├── bot.py              # Основной код бота
├── bot.conf            # Конфигурация (пути к токенам, API ключи)
├── token.txt           # Токен доступа MAX (JWT)
├── Dockerfile          # Для сборки Docker образа
├── docker-compose.yml  # Для запуска контейнера
├── requirements.txt    # Python зависимости
└── aboutmax.txt        # Документация по MAX Bot API
```

## Конфигурация

Файл `bot.conf` содержит:
- `token_file` - путь к файлу с токеном MAX
- `mistral_api_key` - API ключ Mistral AI
- `LLMADD` - дополнительные условия для LLM (стиль ответов)

## Сборка и запуск

### 1. Сборка Docker образа

```bash
docker build -t mxbot:latest .
```

### 2. Запуск через docker-compose

```bash
docker-compose up -d
```

Для остановки:
```bash
docker-compose down
```

### 3. Прямой запуск контейнера

```bash
docker run -d \
  -v ./bot.conf:/app/config/bot.conf:ro \
  -v ./token.txt:/app/config/token.txt:ro \
  --name max_bot \
  mxbot:latest
```

## Логика работы

1. Бот подключается к MAX Bot API через long polling
2. В групповых чатах при попытке 新消щения:
   - Сообщение отправляется в Mistral AI API
   - К запросу добавляется строка из переменной LLMADD
   - Ответ от AI отправляется обратно в чат
3. В личных чатах сообщения игнорируются

## Пример ответа

При сообщении "Привет" бот ответит в стиле:
```
*Разворачивается в пёстром мундире с пердимоноклем на носу, щёлкая каблуками*
Здравствуйте, милейший! Какой у вас к нам дело?
```

## Требования

- Docker Desktop (Windows)
- Python 3.11+
- Tокен MAX Bot API (получить через @MasterBot)
- API ключ Mistral AI
