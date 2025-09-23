import sys

from sc_utility import ExcelReader

EXCEL_FILE = "tests/test_excel.xlsx"


def sum_list_values(data: list[dict]) -> float:
    """
    Helper function to sum values in a dictionary.

    Args:
        data (dict): The data to sum values from.

    Returns:
        int: The sum of all numeric values in the dictionary.
    """
    sum_value = sum(
        value
        for row in data
        for value in row.values()
        if isinstance(value, (int, float))
    )
    return sum_value


def test_load_sheet():
    """Test the ExcelReader class reading from a workheet."""
    # Create an instance of ExcelReader
    excel_reader = ExcelReader(EXCEL_FILE)

    # Read a specific sheet
    try:
        sheet_data = excel_reader.extract_data(source_name="Sheet", source_type="sheet")
        print(f"Extracted sheet data: {sheet_data}")
    except ImportError as e:
        print(f"Error reading sheet: {e}")
        sys.exit(1)
    else:
        assert isinstance(sheet_data, list), "Sheet data should be a list"
        assert len(sheet_data) > 0, "Sheet data should not be empty"
        assert sum_list_values(sheet_data) == 42, "Sum of values in the sheet should be 42"


def test_load_table():
    """Test the ExcelReader class reading from a table."""
    # Create an instance of ExcelReader
    excel_reader = ExcelReader(EXCEL_FILE)

    # Read a specific sheet
    try:
        sheet_data = excel_reader.extract_data(source_name="Table1", source_type="table")
        print(f"Extracted table data: {sheet_data}")
    except ImportError as e:
        print(f"Error reading sheet: {e}")
        sys.exit(1)
    else:
        assert isinstance(sheet_data, list), "Sheet data should be a list"
        assert len(sheet_data) > 0, "Sheet data should not be empty"
        assert sum_list_values(sheet_data) == 42, "Sum of values in the sheet should be 42"


def test_load_range():
    """Test the ExcelReader class reading from a range."""
    # Create an instance of ExcelReader
    excel_reader = ExcelReader(EXCEL_FILE)

    # Read a specific sheet
    try:
        sheet_data = excel_reader.extract_data(source_name="RangeTable1", source_type="range")
        print(f"Extracted range data: {sheet_data}")
    except ImportError as e:
        print(f"Error reading sheet: {e}")
        sys.exit(1)
    else:
        assert isinstance(sheet_data, list), "Sheet data should be a list"
        assert len(sheet_data) > 0, "Sheet data should not be empty"
        assert sum_list_values(sheet_data) == 42, "Sum of values in the sheet should be 42"


# test_load_sheet()
# test_load_table()
# test_load_range()
