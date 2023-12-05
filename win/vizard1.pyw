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
        show_message("Ошибка", f"Произошла ошибка при аутентификации: {e}")

def fill_sprint_combo_box():
    sprint_url = "https://sfera.inno.local/app/tasks/api/v0.1/sprints?areaCode=PPTS&page=0&size=6&statuses=active,planned"
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
            "Ошибка", f"Произошла ошибка при получении данных спринтов: {e}")

def create_task():
    if access_token is None:
        show_message("Ошибка", "Сначала выполните аутентификацию.")
        return

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
        "areaCode": "OMNIISRUN",
        "parent": selected_parent_number,
        "type": "taskRun",
        "priority": "average",
        "sprint": sprint_id_value,
        "name": name,
        "description": description,
        "assignee": username_entry.text(),
        "owner": username_entry.text(),
        "dueDate": due_date_str,
        "estimation": estimation_in_seconds,
        "spent": 1,
        "customFieldsValues": [
            {"code": "streamConsumer", "name": "string",
             "type": "string", "value": "Сопровождение технологической омниканальной платформы"},
            {"code": "streamOwner", "name": "string",
             "type": "string", "value": "Сопровождение технологической омниканальной платформы"},
            {"code": "implementationEndDate", "name": "string",
             "type": "string", "value": due_date_str},
            {"code": "workGroup", "value": "Сопровождение"},
            {"code": "systems", "value": "1369 Унифицированная интеграционная платформа (УИП)"}
        ]
    }

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
    except requests.exceptions.RequestException as e:
        show_message("Ошибка", f"Произошла ошибка при создании задачи: {e}")

    task_link_label = QLabel(
        f"<a href='https://sfera.inno.local/tasks/area/OMNIISRUN/task/{number}'>Ссылка на задачу</a>", window)
    task_link_label.setGeometry(20, 600, 300, 20)
    task_link_label.setOpenExternalLinks(True)
    task_link_label.linkActivated.connect(
        lambda: open_url(f'https://sfera.inno.local/tasks/area/OMNIISRUN/task/{number}'))

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
        gradient.setColorAt(0, QColor(148, 87, 235))  
        gradient.setColorAt(1, QColor(70, 130, 180))  
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
    auth_status_label.setStyleSheet("color: green")

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

    create_task_button = QPushButton("Создать задачу", window)
    create_task_button.setGeometry(180, 570, 300, 30)
    create_task_button.clicked.connect(create_task)
    create_task_button.setStyleSheet(text_input_style)  
    due_date_checkbox.stateChanged.connect(
        lambda state: due_date_edit.setDisabled(state))
    task_link_label = QLabel(f"<a href='https://sfera.inno.local/tasks/area/OMNIISRUN/task/{number}'>Ссылка на задачу</a>", window)
    task_link_label.setGeometry(200, 600, 300, 20)
    task_link_label.setOpenExternalLinks(True)
    task_link_label.linkActivated.connect(lambda: open_url('https://sfera.inno.local/tasks/area/OMNIISRUN/task/{number}'))

    task_link_label = QLabel("", window)  
    task_link_label.setGeometry(20, 600, 300, 20)
    task_link_label.setOpenExternalLinks(True)

    pixmap = QPixmap("C:/Users/1/Desktop/scripts/vizard/win/omni.png") 
    image_label = QLabel(window) 
    image_label.setGeometry(580, 5, 100, 100) 
    image_label.setPixmap(pixmap)
    app_icon = QIcon("C:/Users/1/Desktop/scripts/vizard/win/omni.png") 
    app.setWindowIcon(app_icon)

    window.resize(690, 650)
    window.show()
    sys.exit(app.exec_())
