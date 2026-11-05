import os

import boto3
import pandas as pd


def main() -> None:
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["AWS_S3_ENDPOINT"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        verify=False,
    )
    client.download_file(os.environ["AWS_S3_BUCKET"], "data/support-cases.csv", "support-cases.csv")
    source = pd.read_csv("support-cases.csv")
    daily = source.groupby("date", as_index=False).size().rename(columns={"size": "tickets"})
    daily.to_csv("data.csv", index=False)


if __name__ == "__main__":
    main()
