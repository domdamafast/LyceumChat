from PyQt6.QtCore import QThread, pyqtSignal
import requests

API_URL = "https://routerai.ru/api/v1/chat/completions"


# Преобразует сообщения из базы в формат запроса RouterAI
def build_input(messages):
    # RouterAI получает историю как список ролей и текстов сообщений
    result = []
    for message in messages:
        result.append({"role": message["role"], "content": message["text"]})
    return result


# Достаёт текст ответа из данных, полученных от RouterAI
def response_text(data):
    choices = data.get("choices", [])
    if not choices:
        raise ValueError("Модель не вернула ответ. Попробуйте другую модель.")

    message = choices[0].get("message", {})
    text = message.get("content")
    if not text:
        text = message.get("refusal")

    if isinstance(text, list):
        parts = []
        for part in text:
            parts.append(part.get("text", ""))
        text = "\n".join(parts)

    if not isinstance(text, str):
        text = ""
    text = text.strip()
    if not text:
        raise ValueError("Модель не вернула текст. Попробуйте другую модель.")
    return text


# Отправляет запрос в отдельном потоке и передаёт результат сигналом
class RequestThread(QThread):
    # результат в главное окно *безопасным* способом
    answered = pyqtSignal(str)
    failed = pyqtSignal(str)

    # Запоминает ключ, модель и историю сообщений для запроса
    def __init__(self, api_key, model, messages, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model = model
        self.messages = messages

    # Отправляет запрос в отдельном потоке и сообщает результат через сигнал (50/50)
    def run(self):
        try:
            payload = {
                "model": self.model,
                "messages": build_input(self.messages),
                "max_tokens": 2048,
                "stream": False,
            }
            if self.model == "openai/gpt-5-nano":
                payload["reasoning"] = {"effort": "low"}
                payload["max_tokens"] = 4096
            headers = {
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            }
            # ИИ, доделать ИИ
            with requests.post(
                API_URL, headers=headers, json=payload, timeout=(15, 90)
            ) as response:
                status = response.status_code
                if status == 400:
                    raise ValueError("Модель не приняла запрос. Попробуйте другую модель.")
                if status == 401:
                    raise ValueError("Ключ RouterAI неверный или отозван.")
                if status == 402:
                    raise ValueError("Недостаточно средств или исчерпан лимит ключа.")
                if status == 403:
                    raise ValueError("Нет доступа к модели. Проверьте RouterAI.")
                if status == 404:
                    raise ValueError("Эта модель недоступна. Выберите другую.")
                if status == 429:
                    raise ValueError("Лимит запросов исчерпан. Попробуйте позже.")
                if status != 200:
                    raise ValueError("Ошибка RouterAI. Код: " + str(status))
                data = response.json()
            if data.get("error"):
                raise ValueError("RouterAI не выполнил запрос. Попробуйте позже.")
            self.answered.emit(response_text(data))
        except requests.Timeout:
            self.failed.emit("Время ожидания истекло. Проверьте интернет и повторите.")
        except requests.RequestException:
            self.failed.emit("Нет соединения с RouterAI. Проверьте интернет.")
        except (ValueError, OSError) as error:
            # Не выводим тело сетевой ошибки или заголовки с ключом
            self.failed.emit(str(error))
        except Exception:
            self.failed.emit("Не удалось обработать ответ модели.")
