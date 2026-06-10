import sys


def main() -> None:
    hello, world = sys.argv[1], sys.argv[2]
    print(f"{hello} {world}!")


if __name__ == "__main__":
    main()
