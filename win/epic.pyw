import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QDateTimeEdit, QTextEdit, QMessageBox, QComboBox, QCheckBox
from PyQt5.QtGui import QPalette, QColor, QLinearGradient, QBrush,QPainter, QPixmap, QIcon
from PyQt5.QtCore import Qt
import requests
import json
from datetime import datetime, timedelta
import re

remove_parent_task_checkbox = None
access_token = None
auth_status_label = None
task_link_label = None 
create_epic_checkbox = None 

def authenticate():
    global access_token
    global auth_status_label

    username = username_entry.text()
    password = password_entry.text()

    auth_url = "https://sfera.inno.local/api/auth/login"
    auth_data = {
        "username": username,
        "password": password
    }

    auth_headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            auth_url, data=json.dumps(auth_data), headers=auth_headers, verify=False)
        response.raise_for_status()
        auth_result = response.json()
        access_token = auth_result["access_token"]
        auth_status_label.setText("Авторизован.")
        fill_sprint_combo_box()
        fill_parent_task_combo_box()
    except requests.exceptions.RequestException as e:
        show_message("Ошибка", f": {e}")

def fill_sprint_combo_box():
    sprint_url = "https://sfera.inno.local/app/tasks/api/v0.1/sprints?areaCode=OMNIISRUN&page=0&size=6&statuses=active,planned"
    task_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            sprint_url, headers=task_headers, verify=False)
        response.raise_for_status()
        sprint_data = response.json()["content"]

        sprint_combo_box.clear()

        for sprint in sprint_data:
            name = sprint["name"]
            status = sprint["status"]
            sprint_id = sprint["id"]
            sprint_combo_box.addItem(
                f"{name} ({status})", userData=sprint_id)

    except requests.exceptions.RequestException as e:
        show_message(
            "Ошибка", f"спринт: {e}")

def create_task():
    global task_link_label
    if access_token is None:
        show_message("Ошибка", "Сначала выполните аутентификацию.")
        return
    create_epic = create_epic_checkbox.isChecked()
    area_code = "SUPPOMNIPL" if create_epic else "OMNIISRUN"
    type = "epic" if create_epic else "taskRun"
    selected_sprint_text = sprint_combo_box.currentText()
    selected_sprint_id = sprint_combo_box.currentData()

    sprint_id_value = str(selected_sprint_id)

    name = name_entry.toPlainText().strip()
    description = description_entry.toPlainText().strip()
    estimation_value = estimation_entry.text()
    time_unit = time_units.currentText()
    selected_parent_number = parent_task_combo_box.currentData()

    estimation_in_seconds = convert_to_seconds(estimation_value, time_unit)

    due_date = (
        datetime.now() + timedelta(days=14)
    ) if due_date_checkbox.isChecked() else due_date_edit.date().toPyDate()

    due_date_str = due_date.strftime('%Y-%m-%d')

    no_sprint_selected = no_sprint_checkbox.isChecked()
    if no_sprint_selected:
        sprint_id_value = None
    if remove_parent_task_checkbox.isChecked():
        selected_parent_number = None

    task_url = "https://sfera.inno.local/app/tasks/api/v0.1/entities/"
    task_data = {
        "areaCode": area_code,
        "parent": selected_parent_number,
        "type": type,
        "priority": "average",
        "sprint": sprint_id_value,
        "name": name,
        "description": description,
        "assignee": username_entry.text(),
        "owner": username_entry.text(),
        "dueDate": due_date_str,
        "estimation": estimation_in_seconds,
        #"spent": 1,
        "customFieldsValues": [
            {"code": "streamConsumer", "name": "string",
             "type": "string", "value": "Сопровождение технологической омниканальной платформы"},
            {"code": "streamOwner", "name": "string",
             "type": "string", "value": "Сопровождение технологической омниканальной платформы"},
            {"code": "implementationEndDate", "name": "string",
             "type": "string", "value": due_date_str},
            {"code": "workGroup", "value": "Новая функциональность"},
            {"code": "systems", "value": "1369 Унифицированная интеграционная платформа (УИП)"},
            {
            "code": "projectConsumer",
            "name": "Проект-заказчик",
            "type": "complexDictionary",
            "value": "4bea7141-052a-4923-b1a9-1c2edca582a5",
            "dictionaryId": 14
            },
            {
        "code": "acceptanceCriteria",
        "name": "Критерии приемки",
        "type": "text",
        "value": "Внедрение проведено, документация провалидирована "
    }
        ]
    }
    if not create_epic:
        # Включаем поле estimation только если не создаем эпик
        estimation_value = estimation_entry.text()
        time_unit = time_units.currentText()
        estimation_in_seconds = convert_to_seconds(estimation_value, time_unit)
        task_data["estimation"] = estimation_in_seconds

        # Включаем поле implementationEndDate только если не создаем эпик
        due_date = (
            datetime.now() + timedelta(days=14)
        ) if due_date_checkbox.isChecked() else due_date_edit.date().toPyDate()
        due_date_str = due_date.strftime('%Y-%m-%d')
        task_data["customFieldsValues"].append({
            "code": "implementationEndDate",
            "name": "string",
            "type": "string",
            "value": due_date_str
        })
        task_data["customFieldsValues"] = [
            field for field in task_data.get("customFieldsValues", [])
            if field.get("code") != "acceptanceCriteria"]
    else:
        # Исключаем estimation и implementationEndDate при создании эпика
        task_data.pop("estimation", None)
        task_data["customFieldsValues"] = [
            field for field in task_data.get("customFieldsValues", [])
            if field.get("code") != "implementationEndDate"
        ]

    task_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    print("Тело запроса:", json.dumps(task_data, indent=2))
    try:
        response = requests.post(
            task_url, data=json.dumps(task_data), headers=task_headers, verify=False)
        response.raise_for_status()
        task_result = response.json()
        task_id = task_result.get("id")
        number = task_result.get("number")
        task_link_label.setText(f"<a style='color:#800080;' href='https://sfera.inno.local/tasks/area/OMNIISRUN/task/{number}'>Создана задача - {number}</a>")
    except requests.exceptions.RequestException as e:
        show_message("Ошибка", f"Произошла ошибка при создании задачи: {e}")
        print("Ответ сервера:", response.content)
def toggle_create_epic_checkbox(state):
    remove_parent_task_checkbox.setChecked(state)
    estimation_entry.setDisabled(state)


def convert_to_seconds(value, unit):
    conversion_dict = {"ч": 3600, "д": 28800, "н": 144000}
    try:
        return int(value) * conversion_dict[unit]
    except ValueError:
        show_message("Ошибка", "Введите корректное значение для оценки времени.")
        return 0

def parse_selected_sprint(selected_sprint_text):
    parts = selected_sprint_text.split(" (")
    if len(parts) == 2:
        name, status = parts
        status = status[:-1]
        return {"id": None, "type": "sprint", "name": name, "status": status}
    else:
        return {"id": None, "type": "sprint", "name": "", "status": ""}

def show_message(title, message):
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.exec_()

def toggle_due_date_checkbox(state):
    due_date_edit.setDisabled(state)
    create_without_sprint_checkbox.setDisabled(state)
    remove_parent_task_checkbox.setDisabled(state)
    remove_parent_task_checkbox.setVisible(state)

def extract_number_from_task_text(task_text):
    match = re.search(r'\((\d+)\)', task_text)
    if match:
        return match.group(1)
    return None

def fill_parent_task_combo_box():
    parent_task_url = "https://sfera.inno.local/app/tasks/api/v0.1/entities?areaCode=SUPPOMNIPL&keyword=%D0%A3%D0%98%D0%9F&statusIds=created&statusIds=inProgress&size=1000&page=0&attributesToReturn=directLink,name,assignee,dueDate,actualSprint"

    task_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(parent_task_url, headers=task_headers, verify=False)
        response.raise_for_status()
        tasks_data = response.json()["content"]

        parent_task_combo_box.clear()

        for task in tasks_data:
            name = task.get("name")
            number = task.get("number")

            if name and number:
                parent_task_combo_box.addItem(name)
                parent_task_combo_box.setItemData(parent_task_combo_box.count() - 1, number)
        remove_parent_task_checkbox.setEnabled(True)

    except requests.exceptions.RequestException as e:
        show_message("Ошибка", f"Произошла ошибка при получении данных задач: {e}")

def open_url(url):
    import webbrowser
    webbrowser.open(url)

class GradientWidget(QWidget):
    def __init__(self):
        super().__init__()

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(148, 87, 235))  # Фиолетовый
        gradient.setColorAt(1, QColor(70, 130, 180))  # Голубой
        painter.setBrush(QBrush(gradient))
        painter.drawRect(self.rect())

if __name__ == "__main__":
    app = QApplication(sys.argv)

    
    window = GradientWidget()
    window.setGeometry(100, 100, 640, 620)  
    window.setWindowTitle("Визард")

    palette = QPalette()
    base_color = QColor(100, 100, 150)
    palette.setColor(QPalette.Window, base_color)
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, base_color)  
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))  
    palette.setColor(QPalette.Base, QColor(50, 50, 75))
    palette.setColor(QPalette.AlternateBase, QColor(75, 75, 100))
    palette.setColor(QPalette.Highlight, QColor(255, 0, 0))
    palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
    window.setPalette(palette)

   
    text_input_style = "color: white; background-color: {}".format(QColor(75, 75, 100).name())

    username_label = QLabel("Логин:", window)
    username_label.move(20, 20)

    username_entry = QLineEdit(window)
    username_entry.setGeometry(120, 20, 200, 30)
    username_entry.setStyleSheet(text_input_style)

    password_label = QLabel("Пароль:", window)
    password_label.move(20, 60)

    password_entry = QLineEdit(window)
    password_entry.setGeometry(120, 60, 200, 30)
    password_entry.setEchoMode(QLineEdit.Password)
    password_entry.setStyleSheet(text_input_style)

    auth_button = QPushButton("Авторизация", window)
    auth_button.setGeometry(20, 100, 300, 30)
    auth_button.clicked.connect(authenticate)
    auth_button.setStyleSheet(text_input_style) 

    auth_status_label = QLabel("", window)
    auth_status_label.setGeometry(129, 123, 300, 20)
    auth_status_label.setStyleSheet("color: white")

    name_label = QLabel("Название задачи:", window)
    name_label.move(20, 150)

    name_entry = QTextEdit(window)
    name_entry.setGeometry(20, 180, 300, 60)
    name_entry.setStyleSheet(text_input_style)

    description_label = QLabel("Описание задачи:", window)
    description_label.move(20, 260)

    description_entry = QTextEdit(window)
    description_entry.setGeometry(20, 290, 300, 80)
    description_entry.setStyleSheet(text_input_style)

    description_label = QLabel("Выбери дату выполнения:", window)
    description_label.move(340, 290)
    due_date_checkbox = QCheckBox(" 14 дней", window)
    due_date_checkbox.move(350, 306)
    due_date_checkbox.setChecked(True)

    description_label = QLabel("Или:", window)
    description_label.move(340, 340)

    due_date_edit = QDateTimeEdit(window)
    due_date_edit.setGeometry(370, 330, 150, 30)
    due_date_edit.setDisplayFormat("yyyy-MM-dd")
    due_date_edit.setDateTime(datetime.now())
    due_date_edit.setCalendarPopup(True)
    due_date_edit.setDisabled(True)

    estimation_label = QLabel("Оценка времени:", window)
    estimation_label.move(20, 376)

    estimation_entry = QLineEdit(window)
    estimation_entry.setGeometry(20, 400, 200, 30)
    estimation_entry.setPlaceholderText("Введите оценку времени")
    estimation_entry.setStyleSheet(text_input_style)

    time_units = QComboBox(window)
    time_units.setGeometry(230, 400, 90, 30)
    time_units.addItems(["ч", "д", "н"])
    time_units.setStyleSheet(text_input_style)  

    estimation_label = QLabel("Спринт:", window)
    estimation_label.move(20, 460)
    sprint_combo_box = QComboBox(window)
    sprint_combo_box.setGeometry(20, 480, 300, 30)
    sprint_combo_box.setStyleSheet(text_input_style)  

    parent_task_label = QLabel("Эпик:", window)
    parent_task_label.move(340, 460)

    parent_task_combo_box = QComboBox(window)
    parent_task_combo_box.setGeometry(340, 480, 300, 30)
    parent_task_combo_box.setStyleSheet(text_input_style)  

    no_sprint_checkbox = QCheckBox("В бэклог", window)
    no_sprint_checkbox.setGeometry(20, 530, 300, 30)

    remove_parent_task_checkbox = QCheckBox("Без эпика", window)
    remove_parent_task_checkbox.setGeometry(340, 530, 300, 30)
    create_epic_checkbox = QCheckBox("Создать эпик", window)
    create_epic_checkbox.setGeometry(20, 560, 300, 30)
    create_epic_checkbox.stateChanged.connect(toggle_create_epic_checkbox)


    create_task_button = QPushButton("Создать задачу", window)
    create_task_button.setGeometry(180, 570, 300, 30)
    create_task_button.clicked.connect(create_task)
    create_task_button.setStyleSheet(text_input_style)  
    due_date_checkbox.stateChanged.connect(
        lambda state: due_date_edit.setDisabled(state))

    task_link_label = QLabel("", window) 
    task_link_label.setGeometry(220, 600, 300, 20)
    task_link_label.setOpenExternalLinks(True)
    

    pixmap = QPixmap("C:/Users/1/Desktop/scripts/vizard/win/omni.ico") 
    image_label = QLabel(window) 
    image_label.setGeometry(580, 5, 100, 100)  
    image_label.setPixmap(pixmap)
    app_icon = QIcon("C:/Users/1/Desktop/scripts/vizard/win/omni.ico")  
    app.setWindowIcon(app_icon)

    window.resize(690, 650)
    window.show()
    sys.exit(app.exec_())
