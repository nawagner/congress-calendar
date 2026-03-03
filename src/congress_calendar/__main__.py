"""Entry point for running the Congress Calendar server."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "congress_calendar.app:create_app",
        host="0.0.0.0",
        port=8000,
        factory=True,
    )


if __name__ == "__main__":
    main()
