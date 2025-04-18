#!/usr/bin/env python3
"""
Setup script for the Prompt Engineering Dashboard
"""
import os
import secrets
import getpass
import argparse
import json
import datetime
import uuid
import subprocess
import sys

def setup_environment():
    """Create necessary directories and environment file"""
    # Create directories
    directories = ['uploads', 'uploads/frames', 'results', 'prompts', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        secret_key = secrets.token_hex(16)
        
        # Ask for API key
        api_key = getpass.getpass("Enter your Anthropic API key (or leave blank to add later): ")
        
        with open('.env', 'w') as f:
            f.write(f'FLASK_APP=app.py\n')
            f.write(f'FLASK_ENV=development\n')
            f.write(f'SECRET_KEY={secret_key}\n')
            if api_key:
                f.write(f'ANTHROPIC_API_KEY={api_key}\n')
        
        print("✓ Created .env file with configuration")
    else:
        print("⚠ .env file already exists, skipping creation")

def create_example_template():
    """Create an example prompt template"""
    if not os.path.exists('prompts'):
        os.makedirs('prompts', exist_ok=True)
    
    # Check if we already have templates
    templates = [f for f in os.listdir('prompts') if f.endswith('.json')]
    if templates:
        print("⚠ Example templates already exist, skipping creation")
        return
    
    # Create example template
    template_id = str(uuid.uuid4())
    template = {
        "id": template_id,
        "name": "CausalTrace Template",
        "description": "The default CausalTrace prompt template for analyzing causal relationships in video frames.",
        "template": (
            "Analyze the video frames to answer: {question}. "
            "Use the CausalTrace method: "
            "1. Observe raw events without preconceptions. "
            "2. Identify primary actions and their direct effects. "
            "3. Trace backward to confirm the cause precedes the effect. "
            "4. Consider counterfactuals: would the effect occur without the cause? "
            "5. Rule out confounding factors and coincidental correlations. "
            "Provide a clear explanation of the causal chain, avoiding assumptions or statistical correlations."
        ),
        "created_at": datetime.datetime.now().isoformat()
    }
    
    with open(f'prompts/{template_id}.json', 'w') as f:
        json.dump(template, f, indent=2)
    
    print(f"✓ Created example template: CausalTrace Template")

def setup_virtual_env():
    """Setup virtual environment and install dependencies"""
    # Check if venv module is available
    try:
        import venv
    except ImportError:
        print("⚠ Python venv module not available. Please install it first.")
        return False
    
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        try:
            subprocess.check_call([sys.executable, '-m', 'venv', 'venv'])
            print("✓ Created virtual environment")
        except subprocess.CalledProcessError:
            print("❌ Failed to create virtual environment")
            return False
    else:
        print("⚠ Virtual environment already exists, skipping creation")
    
    # Determine the pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = os.path.join('venv', 'Scripts', 'pip')
    else:  # Unix/Linux/Mac
        pip_path = os.path.join('venv', 'bin', 'pip')
    
    # Install requirements
    print("Installing dependencies...")
    try:
        subprocess.check_call([pip_path, 'install', '-r', 'requirements.txt'])
        print("✓ Installed dependencies")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def main():
    parser = argparse.ArgumentParser(description='Setup Prompt Engineering Dashboard')
    parser.add_argument('--skip-venv', action='store_true', help='Skip virtual environment setup')
    parser.add_argument('--skip-examples', action='store_true', help='Skip creating example templates')
    args = parser.parse_args()
    
    print("Setting up Prompt Engineering Dashboard...")
    
    # Setup environment
    setup_environment()
    
    # Setup virtual environment
    if not args.skip_venv:
        setup_virtual_env()
    
    # Create example template
    if not args.skip_examples:
        create_example_template()
    
    print("\nSetup complete! To start the application:")
    if os.name == 'nt':  # Windows
        print("1. Activate the virtual environment: .\\venv\\Scripts\\activate")
    else:  # Unix/Linux/Mac
        print("1. Activate the virtual environment: source venv/bin/activate")
    print("2. Start the server: flask run")
    print("\nThe dashboard will be available at: http://127.0.0.1:5000")
    print("Default login credentials: username=admin, password=admin")

if __name__ == '__main__':
    main()
