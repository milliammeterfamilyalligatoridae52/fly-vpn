import sys

from dotenv import load_dotenv


def main() -> None:
    """Entry-point for the CLI."""

    load_dotenv()

    if "--watchdog" in sys.argv:
        from flyexit.watchdog import run_watchdog

        run_watchdog()
        return

    from flyexit.app import FlyVPNApp

    app = FlyVPNApp()
    app.run()


if __name__ == "__main__":
    main()
