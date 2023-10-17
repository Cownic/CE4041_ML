import numpy as np
import pandas as pd
import gc  # garbage collection


def load_data(file_path , parse_date=None):
    return pd.read_csv(file_path , parse_dates=parse_date)


def merge_data(df1, df2, on_v):
    return pd.merge(df1, df2, how="left", on=on_v)


def drop_dups(df):
    # We are keeping the last entry for those repeated ones
    return df.drop_duplicates(
        subset=["parcelid", "transactiondate"], ignore_index=True, keep="last"
    )


def check_duplicates(housing):
    idsUnique = len(housing[["parcelid", "transactiondate"]].value_counts())
    idsTotal = housing.shape[0]
    idsDupli = idsTotal - idsUnique
    print(
        "There are "
        + str(idsDupli)
        + " duplicate IDs for "
        + str(idsTotal)
        + " total entries"
    )


def print_percent_missing(df):
    missing_percent = []
    total_count = len(df)
    for col in df.columns:
        missing_count = (df[col].isnull()).sum()
        percent_missing = (missing_count / total_count) * 100
        sett = (col, percent_missing)
        missing_percent.append(sett)

    missing_percent.sort(key=lambda x: x[1], reverse=True)

    for feature, m_percent in missing_percent:
        print(f"{feature} : {m_percent:.2f}%\n")

# Add Day, Month, Year and which quarter the transaction was done
def add_dmy_feature(df):
    df["quarter"] = df["transactiondate"].dt.quarter
    df["day"] = df["transactiondate"].dt.day
    df["transaction_year"] = df["transactiondate"].dt.year
    df["transaction_month"] = df["transactiondate"].dt.month
    df.drop(["transactiondate"], inplace=True, axis=1)
    return df


def get_col_to_drop_missing(df, threshold=0.95):
    temp = []
    total_count = len(df)
    for col in df.columns:
        num_missing = df[col].isnull().sum()
        if num_missing == 0:
            continue
        missing_frac = num_missing / float(total_count)
        if missing_frac > threshold:  # Correct the indentation
            temp.append(col)
    print(f"{len(temp)} has been flagged out\n")
    return temp  # Return the list of columns to drop

def get_col_to_drop_non_unique(df):
    temp = []
    for col in df:
        num_uniques = len(df[col].unique())
        if (df[col].isnull().sum()) != 0:
            num_uniques -= 1
        if (num_uniques == 1):
            temp.append(col)
    print(f"{len(temp)} has been flagged out\n")  
    return temp  



