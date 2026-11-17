@echo off
setlocal
py -m pip install --upgrade pip
py -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --windowed --name JARVIS --collect-all PySide6 --collect-all pyttsx3 -m jarvis
echo.
echo Build output: dist\JARVIS\JARVIS.exe
pause
