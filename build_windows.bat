@echo off
REM ============================================================
REM  Genera CyberPet.exe (requiere tener Python 3 instalado)
REM  Doble clic en este archivo y espera a que termine.
REM  El ejecutable queda en:  dist\CyberPet.exe
REM ============================================================
py -m pip install --upgrade pyinstaller
py -m PyInstaller --onefile --noconsole --name CyberPet cyber_pet.py
echo.
echo ============================================
echo  Listo! Tu ejecutable esta en: dist\CyberPet.exe
echo ============================================
pause
