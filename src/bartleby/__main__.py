# ABOUTME: Entry point for running bartleby as `python -m bartleby`.
# Delegates to the argparse-based CLI in cli.main.

from bartleby.cli import main

if __name__ == "__main__":
    main()
