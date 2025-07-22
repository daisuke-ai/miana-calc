import sys
import os
from streamlit.web import cli as stcli

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    # This will run the Streamlit application located at frontend/home.py
    sys.argv = ["streamlit", "run", "frontend/home.py"]
    stcli.main() 