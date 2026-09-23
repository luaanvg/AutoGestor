@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD=py"
where py >nul 2>nul || set "PYTHON_CMD=python"

if not exist "venv\Scripts\python.exe" (
    echo Criando o ambiente virtual...
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 goto :erro
)

call "venv\Scripts\activate.bat"
echo Instalando ou conferindo as dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 goto :erro

echo Preparando o banco de dados...
python manage.py migrate
if errorlevel 1 goto :erro

echo Abrindo o AutoGestor em http://127.0.0.1:8000/
start "" http://127.0.0.1:8000/
python manage.py runserver
goto :fim

:erro
echo.
echo Nao foi possivel iniciar. Confira se o Python 3.12 ou mais recente esta instalado.
pause

:fim
endlocal
