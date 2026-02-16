#!/bin/bash
set -e

# ==========================================
# pyCol Linux AppImage Builder
# Run this on a Linux machine (e.g. Ubuntu 22.04)
# ==========================================

echo "🚀 Starting AppImage Build..."

# 1. Create and activate virtual environment
echo "📦 Setting up virtual environment..."
VENV_DIR=".venv_build"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 2. Install Dependencies
echo "📦 Installing build dependencies..."
pip install --upgrade pip
if [ -f "../requirements.txt" ]; then
    pip install -r ../requirements.txt
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txt not found, assuming dependencies are minimal."
fi
pip install pyinstaller

# 1.0 Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# 1.1 Generate Version & Plugins
echo "⚙️  Generating version info..."
python3 scripts/generate_version.py
PLUGIN_ARGS=$(cat build/pyinstaller_args.txt)
echo "🔌 Plugins: $PLUGIN_ARGS"

# 2. Build with PyInstaller
# Ensure we are in the script's directory or handle paths relative to root
# Expected to be run from 'scripts/' or root.
# Let's adjust to be safe.
if [ -d "src" ]; then
    echo "ℹ️  Running from root"
    SRC_DIR="src"
elif [ -d "../src" ]; then
    echo "ℹ️  Running from scripts/"
    cd ..
    SRC_DIR="src"
else
    echo "❌ Error: Cannot find src/ directory"
    exit 1
fi

echo "🔨 Building binary with PyInstaller..."

# Build One-Dir
pyinstaller --noconfirm --onedir --windowed --clean \
    --name "pyCol" \
    --add-data "$SRC_DIR/icon.png:." \
    --icon "$SRC_DIR/icon.png" \
    $PLUGIN_ARGS \
    "$SRC_DIR/main.py"

# 3. Prepare AppDir
echo "📂 Preparing AppDir..."
rm -rf AppDir
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
mkdir -p AppDir/usr/share/applications

# Copy PyInstaller Output
cp -r dist/pyCol/* AppDir/usr/bin/

# Copy Icon
cp "$SRC_DIR/icon.png" AppDir/usr/share/icons/hicolor/256x256/apps/pyCol.png
cp "$SRC_DIR/icon.png" AppDir/pyCol.png

# Create Desktop Entry
cat > AppDir/usr/share/applications/pyCol.desktop <<EOF
[Desktop Entry]
Type=Application
Name=pyCol
Comment=Optical Collimation Tool
Exec=pyCol
Icon=pyCol
Categories=Utility;Science;
Terminal=false
EOF

# Symlink desktop file to AppDir root (required by appimagetool)
ln -sf usr/share/applications/pyCol.desktop AppDir/pyCol.desktop

# Create AppRun (Launcher)
# Sets LD_LIBRARY_PATH so PyInstaller libs are found
cat > AppDir/AppRun <<EOF
#!/bin/bash
HERE="\$(dirname "\$(readlink -f "\${0}")")"
export LD_LIBRARY_PATH="\${HERE}/usr/bin:\${LD_LIBRARY_PATH}"
exec "\${HERE}/usr/bin/pyCol" "\$@"
EOF
chmod +x AppDir/AppRun

# 4. Create AppImage
echo "📥 Downloading appimagetool..."
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    wget -q https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

echo "📦 Packaging AppImage..."
# Use ARCH=x86_64 explicitly
mkdir -p build
ARCH=x86_64 ./appimagetool-x86_64.AppImage AppDir build/pyCol-x86_64.AppImage

echo "✅ Done! 'build/pyCol-x86_64.AppImage' is ready."
