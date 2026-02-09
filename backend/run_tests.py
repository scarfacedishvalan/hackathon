"""
Runner script for recipe interpreter tests
Usage: python run_tests.py
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.recipe_interpreter.test_validator import run_tests

if __name__ == "__main__":
    print("Running recipe interpreter tests...")
    run_tests()
