@echo off
REM Build script for GematriaScript using PyInstaller (Windows)

echo Building GematriaScript with PyInstaller...

REM Install dependencies if needed
pip install -r requirements.txt

REM Build using the spec file
pyinstaller gematriascript.spec

echo Build complete! Executable is in dist\gematriascript.exe
