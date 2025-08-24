# BitWit.AI/main.py - Minimal Launcher (Final Version)

import sys
import os
import runpy

print("DEBUG: main.py started.")

# Add the 'src' directory to sys.path so the 'bitwit_ai' package can be found.
# This assumes main.py is in BitWit.AI/ and src/ is a direct subdirectory.
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, 'src'))

print(f"DEBUG: sys.path updated. Current sys.path[0]: {sys.path[0]}")

if __name__ == "__main__":
    try:
        print("DEBUG: Attempting to run bitwit_ai as a module...")
        # Execute the __main__.py from the 'bitwit_ai' package.
        # Python will now find 'bitwit_ai' within the 'src' directory added to sys.path.
        runpy.run_module('bitwit_ai', run_name='__main__', alter_sys=True)
        print("DEBUG: Successfully ran bitwit_ai as a module.")
    except ImportError as e:
        print(f"ERROR: Could not run the main application module. Details: {e}", file=sys.stderr)
        print(f"DEBUG: Current sys.path: {sys.path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    print("DEBUG: main.py finished.")
