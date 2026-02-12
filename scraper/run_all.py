import sys

from scraper.standings import main as standings_main
from scraper.scorers import main as scorers_main
from scraper.assists import main as assists_main
from scraper.palmares import main as palmares_main


def main():
    print("Run all scrapers...")
    standings_main()
    scorers_main()
    assists_main()
    palmares_main()
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"run_all failed: {e}", file=sys.stderr)
        raise
