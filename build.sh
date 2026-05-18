#!/bin/bash
# Build script for GematriaScript using PyInstaller

echo "Building GematriaScript with PyInstaller..."

# Install dependencies if needed
pip install -r requirements.txt

# Build using the spec file
pyinstaller gematriascript.spec

echo "Build complete! Executable is in dist/gematriascript"
