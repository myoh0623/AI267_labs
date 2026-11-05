import pandas as pd


def main() -> None:
    frame = pd.read_csv("data.csv")
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values("date").drop_duplicates("date")
    frame["tickets"] = frame["tickets"].fillna(0).astype(int)
    frame.to_csv("clean-data.csv", index=False)


if __name__ == "__main__":
    main()
