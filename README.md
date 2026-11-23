# Лицей Чат

Учебный текстовый чат на Python, PyQt6 и SQLite. Сообщения отправляются через RouterAI.ru. Главное окно и окно выбора модели созданы в Qt Designer (`main.ui` и `models.ui`).

## Что нужно

- Windows и обычный Python 3.14 x64 с [python.org](https://www.python.org/downloads/windows/) для запуска исходников
- [Visual Studio Code](https://code.visualstudio.com/download) и [расширение Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) для редактирования
- Ключ RouterAI и интернет для получения ответов модели

Для запуска готового `LyceumChat.exe` Python и VS Code не нужны.

## Запуск в VS Code

1. Скачайте репозиторий и откройте его папку в VS Code.
2. Скопируйте `settings.example.json` в `settings.json` и впишите свой ключ после `api_key`. Не публикуйте этот файл.
3. Откройте терминал VS Code и выполните команды по одной:

```powershell
py -3.14 -m pip install --user -r requirements.txt
py -3.14 main.py
```

При следующем запуске достаточно второй команды. Для запуска EXE откройте `LyceumChat.exe` двойным щелчком после создания `settings.json` рядом с ним.

## Возможности

- Несколько чатов с сохранением истории в локальной SQLite-базе
- Три модели, выбор модели для текущего чата
- Переименование чата через поле вверху
- Многострочный ввод: Enter переносит строку, кнопка «Отправить» посылает запрос
- Ответ выполняется в отдельном потоке, окно не зависает

При первом запуске создаётся `chats.sqlite3`. Файл с перепиской и `settings.json` исключены из Git. Перед защитой смотрите `ТЗ.txt`, `Пояснительная_записка.txt` и `Защита.txt`.

## Сборка EXE

```powershell
py -3.14 -m pip install --user pyinstaller==6.22.3
py -3.14 -m PyInstaller --onefile --noconsole --name LyceumChat --add-data "main.ui;." --add-data "models.ui;." main.py
```
