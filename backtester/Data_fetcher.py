import pandas as pd
from datetime import datetime, timedelta
import time
import math

def fetch_chunk(
    smartApi,
    symboltoken,
    interval,
    from_date,
    to_date
):

    

    params = {
        "exchange": "NSE",
        "symboltoken": symboltoken,
        "interval": interval,
        "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
        "todate": to_date.strftime("%Y-%m-%d %H:%M")
    }

    time.sleep(0.5)

    response = smartApi.getCandleData(params)

    if not response:
        raise Exception("No response from Angel API")

    if not response.get("status", False):
        raise Exception(response)

    candles = response.get("data")

    if not candles:
        return pd.DataFrame(
            columns=[
                "Datetime",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        )

    df = pd.DataFrame(
        candles,
        columns=[
            "Datetime",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]
    )

    df["Datetime"] = pd.to_datetime(df["Datetime"])

    return df


def get_historical_data(
    smartApi,
    symboltoken,
    interval,
    days
):

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    total_chunks = math.ceil(days / 30)
    chunk_no = 1

    all_data = []

    current_start = start_date

    while current_start < end_date:

        print(
            f"Downloading chunk {chunk_no}/{total_chunks}..."
        )

        current_end = min(
            current_start + timedelta(days=30),
            end_date
        )

        for attempt in range(3):

            try:

                df = fetch_chunk(
                    smartApi,
                    symboltoken,
                    interval,
                    current_start,
                    current_end
                )

                break

            except Exception as e:

                print(
                    f"Chunk {chunk_no} failed "
                    f"(Attempt {attempt+1}/3)"
                )

                print(e)

                if attempt == 2:
                    raise

                print("Retrying in 5 seconds...")
                time.sleep(5)

        if not df.empty:
            all_data.append(df)

        time.sleep(1)

        chunk_no += 1

        current_start = current_end

    if not all_data:
        return pd.DataFrame(
            columns=[
                "Datetime",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        )

    df = pd.concat(all_data, ignore_index=True)

    df.drop_duplicates(
        subset="Datetime",
        inplace=True
    )

    df.sort_values(
        "Datetime",
        inplace=True
    )

    df.reset_index(
        drop=True,
        inplace=True
    )

    print(
        f"\nDownloaded {len(df)} candles successfully."
    )

    return df
