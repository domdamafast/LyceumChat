from datetime import datetime
import sqlite3

from settings import DATABASE_FILE, DEFAULT_MODEL


class Database:
    # Открывает базу данных и подготавливает таблицы
    def __init__(self, path=DATABASE_FILE):
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    # Создаёт таблицы чатов и сообщений при первом запуске
    def create_tables(self):
        # Один чат содержит много сообщений: messages.chat_id -> chats.id
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS chats ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, model TEXT NOT NULL, "
            "created_at TEXT NOT NULL)"
        )
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "chat_id INTEGER NOT NULL, "
            "role TEXT NOT NULL CHECK (role IN ('user', 'assistant')), "
            "text TEXT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'ok' "
            "CHECK (status IN ('ok', 'pending', 'error')), "
            "created_at TEXT NOT NULL, "
            "FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE)"
        )
        # Если программу закрыли во время запроса, он не считается успешным
        self.connection.execute(
            "UPDATE messages SET status = 'error' WHERE status = 'pending'"
        )
        self.connection.commit()

    # Добавляет новый чат и возвращает его номер
    def create_chat(self, model=DEFAULT_MODEL):
        cursor = self.connection.execute(
            "INSERT INTO chats (title, model, created_at) VALUES (?, ?, ?)",
            ("Новый чат", model, datetime.now().isoformat(timespec="seconds")),
        )
        self.connection.commit()
        return cursor.lastrowid

    # Возвращает все чаты для списка слева
    def list_chats(self):
        return self.connection.execute(
            "SELECT * FROM chats ORDER BY id DESC"
        ).fetchall()

    # Находит один чат по его номеру
    def get_chat(self, chat_id):
        return self.connection.execute(
            "SELECT * FROM chats WHERE id = ?", (chat_id,)
        ).fetchone()

    # Сохраняет новое название чата
    def rename_chat(self, chat_id, title):
        self.connection.execute(
            "UPDATE chats SET title = ? WHERE id = ?", (title, chat_id)
        )
        self.connection.commit()

    # Сохраняет выбранную для чата модель
    def set_model(self, chat_id, model):
        self.connection.execute(
            "UPDATE chats SET model = ? WHERE id = ?", (model, chat_id)
        )
        self.connection.commit()

    # Записывает сообщение в базу и возвращает его номер
    def add_message(self, chat_id, role, text, status="ok"):
        cursor = self.connection.execute(
            "INSERT INTO messages "
            "(chat_id, role, text, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                chat_id,
                role,
                text,
                status,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        self.connection.commit()
        return cursor.lastrowid

    # Отмечает, удалось ли отправить сообщение
    def set_message_status(self, message_id, status):
        self.connection.execute(
            "UPDATE messages SET status = ? WHERE id = ?", (status, message_id)
        )
        self.connection.commit()

    # Возвращает сообщения чата в порядке отправки
    def get_messages(self, chat_id):
        rows = self.connection.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,)
        ).fetchall()
        messages = []
        for row in rows:
            messages.append(dict(row))
        return messages

    # Готовит недавнюю историю чата для следующего запроса к модели
    def get_context(self, chat_id):
        # Ошибки и неотправленные сообщения в контекст нейросети не попадают
        messages = []
        for message in self.get_messages(chat_id):
            if message["status"] == "ok" or message["status"] == "pending":
                messages.append(message)
        # Для экономии отправляем последние 10 пар «вопрос — ответ»
        messages = messages[-21:]
        while messages and messages[0]["role"] != "user":
            messages.pop(0)
        return messages

    # Закрывает соединение с базой данных
    def close(self):
        self.connection.close()
