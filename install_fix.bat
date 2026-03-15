@echo off
echo Fixing Python package installation issues...

REM Activate virtual environment
call C:\Python\hackathon\.venv\Scripts\activate.bat

REM Upgrade pip, setuptools, and wheel to get latest pre-built packages
python -m pip install --upgrade pip setuptools wheel

REM Install packages one by one, using binary wheels only (no compilation)
python -m pip install --only-binary :all: numpy pandas scikit-learn scipy

REM Install the rest of requirements
pip install -r requirements.txt

echo.
echo Installation complete!
pause
