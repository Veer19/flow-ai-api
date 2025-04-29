import io
import logging
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)

async def read_and_parse_csv(content: bytes, file_size: int, filename: str) -> Tuple[pd.DataFrame, List[Dict], List[str], Dict[str, str]]:
    """
    Read and parse a CSV file with proper encoding detection and error handling.
    
    Args:
        content: The raw bytes of the CSV file
        file_size: Size of the file in bytes
        filename: Name of the file for logging
        
    Returns:
        Tuple containing:
        - DataFrame of the parsed CSV
        - Sample data as list of dicts
        - Column names list
        - Column types dict
    """
    logger.info(f"Parsing CSV file: {filename} ({file_size} bytes)")
    
    def read_csv_with_encoding(content, encodings_to_try):
        """Try reading CSV with different encodings until one works"""
        for encoding in encodings_to_try:
            try:
                logger.debug(f"Trying encoding: {encoding}")
                return pd.read_csv(io.BytesIO(content), encoding=encoding)
            except UnicodeDecodeError:
                logger.debug(f"Encoding {encoding} failed")
                continue
            except Exception as e:
                # If it's not an encoding error, re-raise
                if not isinstance(e, UnicodeDecodeError):
                    logger.error(f"Non-encoding error with {encoding}: {str(e)}")
                    raise
        
        logger.error("Failed to read CSV")
        raise ValueError("Failed to read CSV")
    
    # Try common encodings in order of likelihood
    encodings = ['utf-8', 'latin1', 'cp1252', 'ISO-8859-1']
    
    df = read_csv_with_encoding(content, encodings)
    
    logger.info(f"Successfully parsed CSV with {len(df)} rows and {len(df.columns)} columns")
    
    # Convert sample data to JSON-safe values
    sample_data = df.head(5).replace({
        np.nan: None,  # Replace NaN with None
        np.inf: None,  # Replace infinity with None
        -np.inf: None  # Replace negative infinity with None
    }).to_dict(orient='records')
    
    # Convert NumPy types to Python native types in sample data
    from app.utils.json_encoders import convert_numpy_types
    sample_data = convert_numpy_types(sample_data)
    
    # Handle column types (pandas dtypes aren't directly JSON serializable)
    column_names = df.columns.tolist()
    column_types = {}
    for col, dtype in df.dtypes.items():
        column_types[col] = str(dtype)
    
    return df, sample_data, column_names, column_types 