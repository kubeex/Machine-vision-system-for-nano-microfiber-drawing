@echo off

set PYTHON_URL=https://www.python.org/ftp/python/3.10.0/python-3.10.0-amd64.exe
set PYTHON_INSTALLER=python_installer.exe
set PIP_URL=https://bootstrap.pypa.io/get-pip.py

echo Downloading Python installer...
curl -o %PYTHON_INSTALLER% %PYTHON_URL%

echo Installing Python...
start /wait %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1

echo Downloading get-pip.py...
curl -o get-pip.py %PIP_URL%

echo Installing pip...
python get-pip.py

echo Cleaning up...
del %PYTHON_INSTALLER% get-pip.py

echo Python and pip installation completed.
echo Installing libraries...
pip install -r requirements.txt
pause