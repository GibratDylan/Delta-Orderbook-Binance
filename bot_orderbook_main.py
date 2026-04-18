from __future__ import annotations
import sys

def main() -> None:
    try:
        from bot.app import run
    except ModuleNotFoundError as exc:
        missing = exc.name or "unknown"
        raise SystemExit(
            "Missing dependency: "
            f"{missing}. Install project requirements before running the bot."
        ) from exc

    run()


if __name__ == "__main__":
    main()
