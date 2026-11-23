import sqlite3

from PyQt6 import uic
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
)

from api import RequestThread
from database import Database
from settings import (
    LUNA_MODEL,
    MINI_MODEL,
    NANO_MODEL,
    load_settings,
    resource_path,
    save_settings,
)


# Окно выбора модели и его кнопки
class ModelDialog(QDialog):
    # Подготовка окна выбора модели
    def __init__(self, selected_model, parent=None):
        super().__init__(parent)
        uic.loadUi(resource_path("models.ui"), self)
        self.selected_model = selected_model
        self.miniButton.setText("GPT-4o mini\nНедорогая модель для текстового чата.")
        self.nanoButton.setText("GPT-5 nano\nКомпактная модель для текстового чата.")
        self.liteButton.setText("GPT-6 Luna\nМодель для текстового чата.")
        self.miniButton.setCheckable(True)
        self.nanoButton.setCheckable(True)
        self.liteButton.setCheckable(True)
        self.miniButton.setChecked(selected_model == MINI_MODEL)
        self.nanoButton.setChecked(selected_model == NANO_MODEL)
        self.liteButton.setChecked(selected_model == LUNA_MODEL)
        self.miniButton.clicked.connect(self.choose_mini)
        self.nanoButton.clicked.connect(self.choose_nano)
        self.liteButton.clicked.connect(self.choose_luna)

    # Выбираем модель ChatGPT 4o mini
    def choose_mini(self):
        self.selected_model = MINI_MODEL
        # Закрываем окно
        self.accept()

    # Выбираем модель ChatGPT 5 nano
    def choose_nano(self):
        self.selected_model = NANO_MODEL
        # Закрываем окно
        self.accept()

    # Выбираем модель ChatGPT 6 Luna
    def choose_luna(self):
        self.selected_model = LUNA_MODEL
        # Закрываем окно
        self.accept()


# Главное окно чата
class ChatWindow(QMainWindow):
    # Главное окно
    def __init__(self):
        super().__init__()
        # Разметка хранится отдельно: её можно редактировать в Qt Designer
        uic.loadUi(resource_path("main.ui"), self)
        self.settings = load_settings()
        self.database = Database()
        self.chat_id = None
        self.worker = None
        self.response_label = None
        self.pending_message_id = None
        self.model = self.settings["model"]
        self.busy = False
        self.connect_buttons()
        chats = self.database.list_chats()
        # При запуске открываем пустой «Новый чат», сохраняя старые в списке
        chat_id = None
        for chat in chats:
            if not self.database.get_messages(chat["id"]):
                chat_id = chat["id"]
                break
        if chat_id is None:
            chat_id = self.database.create_chat(self.model)
        self.refresh_chat_list(chat_id)

    # Связывание кнопок и полей ввода с обработчиками
    def connect_buttons(self):
        self.newChatButton.clicked.connect(self.new_chat)
        self.modelButton.clicked.connect(self.select_model)
        self.chatTitleEdit.returnPressed.connect(self.rename_current_chat)
        self.chatsList.currentItemChanged.connect(self.open_chat)
        self.sendButton.clicked.connect(self.send_message)
        # У QTextEdit нет обработчика Enter: клавиша просто добавляет строку

    # Перерисовка списка чатов и выделение нужного чата
    def refresh_chat_list(self, selected_id):
        self.chatsList.blockSignals(True)
        self.chatsList.clear()
        selected_item = None
        for chat in self.database.list_chats():
            item = QListWidgetItem(chat["title"])
            item.setData(Qt.ItemDataRole.UserRole, chat["id"])
            item.setToolTip(chat["title"])
            self.chatsList.addItem(item)
            if chat["id"] == selected_id:
                selected_item = item
        self.chatsList.setCurrentItem(selected_item)
        self.chatsList.blockSignals(False)
        if selected_item:
            self.open_chat(selected_item)

    # Открывает чат и его сообщения
    def open_chat(self, item, previous=None):
        if item is None:
            return
        self.chat_id = item.data(Qt.ItemDataRole.UserRole)
        chat = self.database.get_chat(self.chat_id)
        self.model = chat["model"]
        self.modelButton.setText("Модель")
        self.chatTitleEdit.setText(chat["title"])
        self.inputEdit.clear()
        self.render_messages()

    # Новый чат
    def new_chat(self):
        if not self.database.get_messages(self.chat_id):
            self.inputEdit.setFocus()
            return
        chat_id = self.database.create_chat(self.model)
        self.refresh_chat_list(chat_id)
        self.inputEdit.setFocus()

    # Переименование чата сверху
    def rename_current_chat(self):
        title = self.chatTitleEdit.text().strip()
        if not title:
            self.chatTitleEdit.setText(self.database.get_chat(self.chat_id)["title"])
            return
        self.database.rename_chat(self.chat_id, title)
        self.chatTitleEdit.setText(title)
        item = self.chatsList.currentItem()
        item.setText(title)
        item.setToolTip(title)
        self.inputEdit.setFocus()

    # Открывает выбор моделей
    def select_model(self):
        dialog = ModelDialog(self.model, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.model = dialog.selected_model
            self.database.set_model(self.chat_id, self.model)
            self.settings["model"] = self.model
            self.save_current_settings()
            self.modelButton.setText("Модель")

    # Записывает настройки и показывает предупреждение при ошибке (это дело ИИ)
    def save_current_settings(self):
        try:
            save_settings(self.settings)
        except OSError:
            QMessageBox.warning(self, "Настройки", "Не удалось записать settings.json.")

    # Заново выводит на экран сообщения открытого чата (это дело ИИ)
    def render_messages(self):
        while self.messagesLayout.count():
            item = self.messagesLayout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        messages = self.database.get_messages(self.chat_id)
        self.messagesLayout.addStretch()
        for message in messages:
            self.add_bubble(
                message["role"], message["text"], message["status"]
            )
        self.scroll_to_bottom()

    # Создаёт блок сообщения справа для пользователя или слева для модели (это дело ИИ)
    def add_bubble(self, role, text, status="ok"):
        row = QFrame()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 5, 4, 5)
        bubble = QFrame()
        bubble.setMaximumWidth(740)
        color = "#242424" if role == "user" else "#141414"
        bubble.setObjectName("messageBubble")
        bubble.setStyleSheet(
            "QFrame#messageBubble {background: " + color + "; border: 1px solid #333333; border-radius: 7px;}"
            "QLabel {color: #ffffff; background: transparent; border: none;}"
        )
        content = QVBoxLayout(bubble)
        author = QLabel("Вы" if role == "user" else "Нейросеть")
        author.setStyleSheet("font-weight: bold; color: #d8d8d8; background: transparent;")
        content.addWidget(author)
        body = QLabel(text)
        body.setTextFormat(Qt.TextFormat.PlainText)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.setMinimumWidth(180)
        if status == "error" and role == "assistant":
            body.setStyleSheet("color: #ff9494; background: transparent;")
        else:
            body.setStyleSheet("color: #ffffff; background: transparent;")
        content.addWidget(body)
        if role == "user":
            row_layout.addStretch()
        row_layout.addWidget(bubble)
        if role == "assistant":
            row_layout.addStretch()
        # Растяжение (это дело ИИ)
        position = self.messagesLayout.count() - 1
        self.messagesLayout.insertWidget(position, row)
        return body

    # Прокрутка
    def scroll_to_bottom(self):
        # Однократный вызов после пересчёта размеров, это не анимация
        QTimer.singleShot(0, self.move_scrollbar)

    # Опускает полосу прокрутки в самый низ чата (это дело ИИ)
    def move_scrollbar(self):
        scrollbar = self.messagesScroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # Отключает основные кнопки на время запроса и снова включает после ответа
    def set_busy(self, busy):
        self.busy = busy
        for widget in [
            self.sendButton,
            self.newChatButton,
            self.modelButton,
            self.chatTitleEdit,
            self.chatsList,
        ]:
            widget.setEnabled(not busy)

    # Сохраняет текст пользователя и делает запрос к RouterAI (50 на 50)
    def send_message(self):
        text = self.inputEdit.toPlainText().strip()
        if self.busy or not text:
            return
        if len(text) > 16000:
            QMessageBox.warning(
                self, "Сообщение", "Сократите сообщение до 16 000 символов."
            )
            return
        if not self.settings["api_key"]:
            QMessageBox.warning(
                self, "API-ключ", "Добавьте ключ RouterAI в файл settings.json."
            )
            return
        try:
            self.pending_message_id = self.database.add_message(
                self.chat_id, "user", text, status="pending"
            )
            chat = self.database.get_chat(self.chat_id)
            if chat["title"] == "Новый чат":
                title = " ".join(text.split())[:38]
                self.database.rename_chat(self.chat_id, title)
            # Перерисовка читает уже сохранённое сообщение из SQLite (это дело ИИ)
            self.refresh_chat_list(self.chat_id)
            self.response_label = self.add_bubble("assistant", "Нейросеть думает…")
            self.scroll_to_bottom()
            self.set_busy(True)
            self.worker = RequestThread(
                self.settings["api_key"],
                self.model,
                self.database.get_context(self.chat_id),
                self,
            )
            self.worker.answered.connect(self.on_answer)
            self.worker.failed.connect(self.on_failure)
            self.worker.finished.connect(self.request_finished)
            self.worker.start()
        except (OSError, sqlite3.Error) as error:
            self.set_busy(False)
            QMessageBox.warning(self, "Не удалось отправить", str(error))

    # Сохраняет ответ модели и заменяет надпись об ожидании
    def on_answer(self, text):
        self.database.set_message_status(self.pending_message_id, "ok")
        self.database.add_message(self.chat_id, "assistant", text)
        # Замена текста QLabel на ответ нейросети
        self.response_label.setText(text)
        self.scroll_to_bottom()

    # Показывает текст ошибки вместо ответа модели (это дело ИИ)
    def on_failure(self, text):
        self.database.set_message_status(self.pending_message_id, "error")
        self.database.add_message(self.chat_id, "assistant", text, status="error")
        self.response_label.setText(text)
        self.response_label.setStyleSheet("color: #ff9494; background: transparent;")
        self.scroll_to_bottom()

    # Освобождает завершённый поток и снова включает кнопки (это дело ИИ)
    def request_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_busy(False)

    # Закрывает базу при выходе или ждёт завершения текущего запроса (это дело ИИ)
    def closeEvent(self, event):
        if self.busy:
            QMessageBox.information(
                self, "Запрос выполняется", "Дождитесь ответа или сообщения об ошибке."
            )
            event.ignore()
            return
        self.database.close()
        event.accept()
