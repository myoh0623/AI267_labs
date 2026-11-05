import pandas as pd


def main() -> None:
    frame = pd.read_csv("clean-data.csv", parse_dates=["date"])
    baseline = max(0, round(frame.tail(7)["tickets"].mean()))
    start = frame["date"].max() + pd.Timedelta(days=1)
    forecast = pd.DataFrame(
        {
            "date": pd.date_range(start=start, periods=28, freq="D"),
            "forecast_tickets": [baseline] * 28,
        }
    )
    forecast.to_csv("forecast-data.csv", index=False)


if __name__ == "__main__":
    main()
