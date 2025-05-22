import pandas as pd
import logging

# Set up logging
logger = logging.getLogger(__name__)


def execute_pandas_code(code: str, dataframes: dict[str, pd.DataFrame]):
    """
    Execute the pandas code
    """
    # Execute the generated code
    try:
        # Create namespace for execution
        namespace = {}
        exec(code, namespace)
        get_result = namespace.get('main')

        if not get_result:
            raise ValueError(f"Code did not define main function")

        # Run the analysis
        result = get_result(dataframes)
        return result
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}")
        raise e
