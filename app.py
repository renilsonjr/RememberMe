#!/usr/bin/env python3
"""
Web dashboard for RememberMe debt tracker.

Run with: python3 app.py
Then open http://localhost:5000 in your browser.
"""

import os
from src.presentation.app import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, port=port)
