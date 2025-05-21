from datetime import datetime


def to_datetime(date_str: str):
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
