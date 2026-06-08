import os
import sys

sys.path.append(os.path.dirname(__file__))

def main() -> None:
    from .app import main
    main()

