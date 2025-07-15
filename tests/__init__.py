"""
Test suite initialization file.
"""
import pytest
import sys
import os

# Add the parent directory to the Python path so we can import vagents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Version info for test reports
__version__ = "0.1.0"
