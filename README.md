# demo railway bot

Готовый Flask-бот под Railway.

## Локально

```bash
python -m pip install -r requirements.txt
python app.py
```

Открой: http://127.0.0.1:5000

## Railway

1. Загрузи проект в GitHub.
2. В Railway: New Project -> Deploy from GitHub Repo.
3. Выбери этот репозиторий.
4. Start Command:

```bash
gunicorn app:app
```

## Файлы

- `app.py` — сервер и логика
- `requirements.txt` — зависимости
- `Procfile` — команда запуска
- `templates/` — HTML
- `static/` — CSS и JS
- `knowledge.json` — база знаний
- `memory.json` — память
- `dialog_memory.json` — история диалога
