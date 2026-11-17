import os
import argparse
import logging
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def load_data(input_path: str) -> pd.DataFrame:
    """Load raw dataset from Excel or CSV file."""
    logger.info(f"Loading data from: {input_path}")

    if input_path.endswith(".xls") or input_path.endswith(".xlsx"):
        df = pd.read_excel(input_path, header=1)
    elif input_path.endswith(".csv"):
        df = pd.read_csv(input_path)
    else:
        raise ValueError(f"Unsupported file format: {input_path}")

    logger.info(f"Dataset loaded — shape: {df.shape}")
    logger.info(f"Columns: {df.columns.tolist()}")
    return df
def basic_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """Drop irrelevant columns and handle data types."""
    logger.info("Step 2: Basic cleaning...")

    if "ID" in df.columns:
        df = df.drop(columns=["ID"])
        logger.info("  - Dropped 'ID' column")

    df = df.rename(columns={"default payment next month": "default"})
    logger.info("  - Renamed target column to 'default'")

    logger.info(f"  - Shape after cleaning: {df.shape}")
    return df


def handle_anomalous_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle invalid categorical values based on dataset documentation:
    - EDUCATION: 1=grad school, 2=university, 3=high school, 4=others
                 values 0, 5, 6 are undocumented → merge into 4 (others)
    - MARRIAGE:  1=married, 2=single, 3=others
                 value 0 is undocumented → merge into 3 (others)
    - PAY_* columns: -2 is undocumented in some versions → keep as valid
    """
    logger.info("Step 3: Handling anomalous values...")

    education_invalid = df["EDUCATION"].isin([0, 5, 6]).sum()
    df["EDUCATION"] = df["EDUCATION"].replace({0: 4, 5: 4, 6: 4})
    logger.info(f"  - EDUCATION: fixed {education_invalid} anomalous values → mapped to 4 (others)")

    marriage_invalid = df["MARRIAGE"].isin([0]).sum()
    df["MARRIAGE"] = df["MARRIAGE"].replace({0: 3})
    logger.info(f"  - MARRIAGE: fixed {marriage_invalid} anomalous values → mapped to 3 (others)")

    pay_cols = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    for col in pay_cols:
        df[col] = df[col].clip(lower=-2)  

    logger.info(f"  - PAY_* columns: clipped to minimum -2")
    return df


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived features to improve model performance."""
    logger.info("Step 4: Feature engineering...")

    bill_cols = ["BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6"]
    pay_amt_cols = ["PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6"]

    df["AVG_BILL_AMT"] = df[bill_cols].mean(axis=1)
    logger.info("  - Created: AVG_BILL_AMT")

    df["AVG_PAY_AMT"] = df[pay_amt_cols].mean(axis=1)
    logger.info("  - Created: AVG_PAY_AMT")

    df["PAY_RATIO"] = df["AVG_PAY_AMT"] / (df["AVG_BILL_AMT"] + 1)
    df["PAY_RATIO"] = df["PAY_RATIO"].clip(lower=0, upper=10) 
    logger.info("  - Created: PAY_RATIO (avg_pay / avg_bill)")

    df["CREDIT_UTIL"] = df["BILL_AMT1"] / (df["LIMIT_BAL"] + 1)
    df["CREDIT_UTIL"] = df["CREDIT_UTIL"].clip(lower=0, upper=5)
    logger.info("  - Created: CREDIT_UTIL (bill_amt1 / limit_bal)")

    pay_status_cols = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    df["LATE_PAYMENT_COUNT"] = (df[pay_status_cols] > 0).sum(axis=1)
    logger.info("  - Created: LATE_PAYMENT_COUNT")

    logger.info(f"  - Shape after feature engineering: {df.shape}")
    return df

def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode categorical features."""
    logger.info("Step 5: Encoding categorical features...")

    categorical_cols = ["SEX", "EDUCATION", "MARRIAGE"]

    df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=False, dtype=int)
    logger.info(f"  - One-hot encoded columns: {categorical_cols}")
    logger.info(f"  - Shape after encoding: {df_encoded.shape}")
    return df_encoded


def split_features_target(df: pd.DataFrame) -> tuple:
    """Separate features (X) from target (y)."""
    logger.info("Step 6: Splitting features and target...")

    X = df.drop(columns=["default"])
    y = df["default"]

    logger.info(f"  - Features shape: {X.shape}")
    logger.info(f"  - Target shape: {y.shape}")
    logger.info(f"  - Target distribution:\n{y.value_counts().to_string()}")
    return X, y


def split_train_test(X: pd.DataFrame, y: pd.Series, test_size: float = 0.2, random_state: int = 42) -> tuple:
    """Split data into training and test sets."""
    logger.info(f"Step 7: Train-test split (test_size={test_size}, random_state={random_state})...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    logger.info(f"  - X_train shape: {X_train.shape}")
    logger.info(f"  - X_test  shape: {X_test.shape}")
    return X_train, X_test, y_train, y_test


def scale_features(X_train: pd.DataFrame, X_test: pd.DataFrame) -> tuple:
    """
    Standardize numerical features using StandardScaler.
    Fit on training data, transform both train and test to prevent data leakage.
    """
    logger.info("Step 8: Scaling numerical features (StandardScaler)...")

    numerical_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
    binary_prefixes = ("SEX_", "EDUCATION_", "MARRIAGE_")
    numerical_cols = [c for c in numerical_cols if not c.startswith(binary_prefixes)]

    scaler = StandardScaler()
    X_train[numerical_cols] = scaler.fit_transform(X_train[numerical_cols])
    X_test[numerical_cols]  = scaler.transform(X_test[numerical_cols])

    logger.info(f"  - Scaled {len(numerical_cols)} numerical columns")
    return X_train, X_test, scaler, numerical_cols


def save_preprocessed_data(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    scaler,
    output_dir: str,
) -> None:
    """Save all preprocessed datasets and scaler to output directory."""
    logger.info(f"Step 9: Saving preprocessed data to '{output_dir}'...")
    os.makedirs(output_dir, exist_ok=True)

    X_train.to_csv(os.path.join(output_dir, "X_train.csv"), index=False)
    X_test.to_csv(os.path.join(output_dir, "X_test.csv"),  index=False)
    y_train.to_csv(os.path.join(output_dir, "y_train.csv"), index=False, header=True)
    y_test.to_csv(os.path.join(output_dir, "y_test.csv"),  index=False, header=True)
    joblib.dump(scaler, os.path.join(output_dir, "scaler.pkl"))

    logger.info(f"  - Saved: X_train.csv  ({X_train.shape})")
    logger.info(f"  - Saved: X_test.csv   ({X_test.shape})")
    logger.info(f"  - Saved: y_train.csv  ({y_train.shape})")
    logger.info(f"  - Saved: y_test.csv   ({y_test.shape})")
    logger.info(f"  - Saved: scaler.pkl")
    logger.info("Preprocessing complete!")


def run_preprocessing(input_path: str, output_dir: str) -> None:
    """Run full preprocessing pipeline."""
    logger.info("=" * 60)
    logger.info("Credit Card Default — Automated Preprocessing Pipeline")
    logger.info(f"Input : {input_path}")
    logger.info(f"Output: {output_dir}")
    logger.info("=" * 60)

    df = load_data(input_path)
    df = basic_cleaning(df)
    df = handle_anomalous_values(df)
    df = feature_engineering(df)
    df = encode_features(df)
    X, y = split_features_target(df)
    X_train, X_test, y_train, y_test = split_train_test(X, y)
    X_train, X_test, scaler, _ = scale_features(X_train, X_test)
    save_preprocessed_data(X_train, X_test, y_train, y_test, scaler, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated preprocessing for Credit Card Default dataset")
    parser.add_argument(
        "--input",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "..", "creditcard_raw.xls"),
        help="Path to raw dataset (.xls or .csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "creditcard_preprocessing"),
        help="Directory to save preprocessed data",
    )
    args = parser.parse_args()
    run_preprocessing(input_path=args.input, output_dir=args.output)
