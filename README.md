# Prompt Engineering Dashboard

A web dashboard for managing and deploying your CausalPrompt evaluation system.

## Features
- Create and manage prompt templates
- Run evaluations on video frames
- View detailed evaluation results
- Easily manage your API key

## Directory Structure

```
prompt-engineering-dashboard/
├── app.py                      # Main application entry point
├── causal_prompt_evaluator.py  # Core evaluation logic
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup script
├── docker-compose.yml          # Docker compose configuration
├── Dockerfile                  # Docker container definition
├── README.md                   # This file
├── templates/                  # HTML templates
│   ├── base.html               # Base template layout
│   ├── login.html              # Authentication template
│   ├── dashboard.html          # Main dashboard interface
│   └── ...                     # Other template files
└── static/                     # Static assets
    ├── css/                    # Stylesheets
    └── js/                     # JavaScript files
```

## Installation

### Option 1: Using setup script
1. Clone the repository
2. Run the setup script:
```bash
python setup.py
```

### Option 2: Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/prompt-engineering-dashboard.git
cd prompt-engineering-dashboard

# Build and start the containers
docker-compose up -d
```

### Option 3: Manual Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/prompt-engineering-dashboard.git
cd prompt-engineering-dashboard

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Usage

1. Access the dashboard at `http://localhost:5000`
2. Log in with your credentials
3. Create and compare prompt engineering techniques
4. View evaluation metrics and results

## Features

- Interactive prompt engineering workspace
- Causal evaluation of prompt effectiveness
- Comparative analysis of different prompting techniques
- Visualization of results
- Export and sharing capabilities

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [List any libraries, tools, or references that inspired or helped your project]
