"""
Setup script for the training project
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install all requirements"""
    print("📦 Installing requirements...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def setup_directories():
    """Create necessary directories"""
    print("📁 Setting up directories...")
    
    directories = [
        "datasamples/raw",
        "datasamples/processed", 
        "datasamples/questions",
        "datasamples/answers",
        "datasamples/final_datasets",
        "datamodels/llama_cache",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")

def test_installation():
    """Test the installation"""
    print("🧪 Testing installation...")
    
    try:
        # Test imports
        import torch
        import transformers
        import fastapi
        import aiohttp
        from bs4 import BeautifulSoup
        import pandas
        import numpy
        
        print("✅ All imports successful")
        
        # Test CUDA availability
        if torch.cuda.is_available():
            print(f"✅ CUDA available: {torch.cuda.get_device_name()}")
        else:
            print("ℹ️  CUDA not available (will use CPU)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Training QA Generator...")
    
    success = True
    
    # Install requirements
    if not install_requirements():
        success = False
    
    # Setup directories
    setup_directories()
    
    # Test installation
    if success and not test_installation():
        success = False
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Configure your .env file")
        print("2. Test with: python main.py 'your text here'")
        print("3. Start API server: python api/main_api.py")
    else:
        print("\n❌ Setup encountered errors. Please check the output above.")

if __name__ == "__main__":
    main()
