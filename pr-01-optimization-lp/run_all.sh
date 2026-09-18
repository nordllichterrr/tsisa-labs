#!/bin/bash
echo "========================================"
echo "Создание виртуального окружения"
echo "========================================"
python3 -m venv venv
source venv/bin/activate

echo
echo "========================================"
echo "Установка зависимостей"
echo "========================================"
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "========================================"
echo "Запуск решений задач"
echo "========================================"
echo
python3 task1.py
echo
python3 task2.py
echo
python3 task3.py
