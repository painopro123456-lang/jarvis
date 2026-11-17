@echo off
setlocal
py -m pip install --upgrade pip
py -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name JARVIS --paths . --collect-all PySide6 --collect-all pyttsx3 jarvis\__main__.py
if errorlevel 1 (
  echo.
  echo Build failed. See the error above.
  pause
  exit /b 1
)
echo.
echo Build output: dist\JARVIS.exe
pause
