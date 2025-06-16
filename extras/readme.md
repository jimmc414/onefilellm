# Extras

This folder contains additional tools, examples, and experimental features for OneFileLLM.

## web_app.py

A Flask-based web interface for OneFileLLM that provides a graphical alternative to the command-line interface.

### Features
- Web-based GUI for processing URLs and files
- Real-time processing with visual feedback
- Copy-to-clipboard functionality
- Support for all OneFileLLM input types (GitHub repos, ArXiv papers, YouTube videos, etc.)

### Usage
```bash
# Install Flask if not already installed
pip install flask

# Run the web app
python extras/web_app.py

# Access at http://localhost:5000
```

### Status
**Note**: This web interface is provided as an example implementation and is not actively maintained. It demonstrates how OneFileLLM can be integrated into web applications. Feel free to use it as a starting point for your own implementations.

### Requirements
- Flask
- All OneFileLLM dependencies
- Modern web browser

## Contributing

If you build upon these extras or create your own integrations, consider submitting a pull request to share with the community!