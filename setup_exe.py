"""
Setup script for creating Training QA Generator EXE
"""

import os
import sys
import subprocess
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("📦 Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_exe.txt"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "auto-py-to-exe", "pyinstaller"])

def build_exe():
    """Build the EXE file using PyInstaller directly"""
    print("🔨 Building EXE file...")
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "TrainingQAGenerator",
        "--add-data", ".env;.",
        "--add-data", "config;config",
        "--add-data", "core;core", 
        "--add-data", "utils;utils",
        "--add-data", "integrations;integrations",
        "--hidden-import", "torch",
        "--hidden-import", "transformers",
        "--hidden-import", "aiohttp",
        "--hidden-import", "aiofiles",
        "--hidden-import", "PyPDF2",
        "--hidden-import", "youtube_transcript_api",
        "--hidden-import", "yt_dlp",
        "--hidden-import", "moviepy",
        "--hidden-import", "speech_recognition",
        "--collect-all", "torch",
        "--collect-all", "transformers",
        "gui_app.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("✅ Build completed successfully!")
        print("📁 EXE file location: dist/TrainingQAGenerator.exe")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    
    return True

def main():
    """Main setup function"""
    print("🚀 Training QA Generator - EXE Builder")
    print("=" * 50)
    
    # Check if we're in the right directory
    required_files = ["gui_app.py", "main.py", "config", "core", "utils"]
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ Missing required files/folders: {missing_files}")
        print("Please run this script from the training project root directory.")
        return
    
    try:
        # Install requirements
        install_requirements()
        
        # Build EXE
        if build_exe():
            print("\n🎉 Setup completed successfully!")
            print("You can now distribute the EXE file to other computers.")
            print("The EXE includes all dependencies and doesn't require Python to be installed.")
        else:
            print("\n❌ Setup failed during build process.")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    main()
