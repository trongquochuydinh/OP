"""
Utility functions for Excel-style range parsing and column mapping
"""
import re
import pandas as pd

def excel_column_to_number(col_str):
    """
    Convert Excel column string to 0-based column index.
    A -> 0, B -> 1, ..., Z -> 25, AA -> 26, AB -> 27, etc.
    """
    col_str = col_str.upper()
    result = 0
    
    for char in col_str:
        result = result * 26 + (ord(char) - ord('A') + 1)
    
    return result - 1  # Convert to 0-based index


def number_to_excel_column(num):
    """
    Convert 0-based column index to Excel column string.
    0 -> A, 1 -> B, ..., 25 -> Z, 26 -> AA, etc.
    """
    result = ""
    num += 1  # Convert to 1-based
    
    while num > 0:
        num -= 1  # Adjust for 0-based modulo
        result = chr(ord('A') + (num % 26)) + result
        num //= 26
    
    return result

# TODO: Make the range parsing more robust to handle various formats and edge cases, such as:
# - 'A2:N28' or 'A2-N28' (traditional rectangular range)
# - 'A' (entire column A)
# - 'A2:A10' (column A, rows 2-10)
# - 'A:C' (columns A through C, all rows)
# - 'A2:A10,C2:C10' (multiple ranges) - not done yet

def parse_excel_range(range_str):
    """
    Parse Excel range string in various formats:
    - 'A2:N28' or 'A2-N28' (traditional rectangular range)
    - 'A' (entire column A)
    - 'A2:A10' (column A, rows 2-10)
    - 'A:C' (columns A through C, all rows)
    Returns dict with start_col, end_col, start_row, end_row (all 0-based)
    """
    # Normalize separators to :
    range_str = range_str.replace('-', ':').upper().strip()
    
    # Case 1: Single column letter (e.g., 'A')
    if re.match(r'^[A-Z]+$', range_str):
        col_num = excel_column_to_number(range_str)
        return {
            'start_col': col_num,
            'end_col': col_num,
            'start_row': 0,  # Start from first row
            'end_row': 1048575,  # Excel max rows - 1 (0-based)
            'start_col_str': range_str,
            'end_col_str': range_str,
            'start_row_str': '1',
            'end_row_str': '1048576'
        }
    
    # Case 2: Column range without row numbers (e.g., 'A:C')
    col_range_match = re.match(r'^([A-Z]+):([A-Z]+)$', range_str)
    if col_range_match:
        start_col_str, end_col_str = col_range_match.groups()
        start_col = excel_column_to_number(start_col_str)
        end_col = excel_column_to_number(end_col_str)
        
        if start_col > end_col:
            raise ValueError(f"Start column {start_col_str} must be <= end column {end_col_str}")
        
        return {
            'start_col': start_col,
            'end_col': end_col,
            'start_row': 0,
            'end_row': 1048575,
            'start_col_str': start_col_str,
            'end_col_str': end_col_str,
            'start_row_str': '1',
            'end_row_str': '1048576'
        }
    
    # Case 3: Traditional range with row numbers (e.g., 'A2:N28')
    full_range_match = re.match(r'^([A-Z]+)(\d+):([A-Z]+)(\d+)$', range_str)
    if full_range_match:
        start_col_str, start_row_str, end_col_str, end_row_str = full_range_match.groups()
        
        start_col = excel_column_to_number(start_col_str)
        end_col = excel_column_to_number(end_col_str)
        start_row = int(start_row_str) - 1  # Convert to 0-based
        end_row = int(end_row_str) - 1      # Convert to 0-based
        
        if start_col > end_col:
            raise ValueError(f"Start column {start_col_str} must be <= end column {end_col_str}")
        
        if start_row > end_row:
            raise ValueError(f"Start row {start_row_str} must be <= end row {end_row_str}")

        return {
            'start_col': start_col,
            'end_col': end_col,
            'start_row': start_row,
            'end_row': end_row,
            'start_col_str': start_col_str,
            'end_col_str': end_col_str,
            'start_row_str': start_row_str,
            'end_row_str': end_row_str
        }
    
    # Case 4: Single cell (e.g., 'A2')
    single_cell_match = re.match(r'^([A-Z]+)(\d+)$', range_str)
    if single_cell_match:
        col_str, row_str = single_cell_match.groups()
        col_num = excel_column_to_number(col_str)
        row_num = int(row_str) - 1  # Convert to 0-based
        
        return {
            'start_col': col_num,
            'end_col': col_num,
            'start_row': row_num,
            'end_row': row_num,
            'start_col_str': col_str,
            'end_col_str': col_str,
            'start_row_str': row_str,
            'end_row_str': row_str
        }
    
    # If none of the patterns match
    raise ValueError(f"Invalid range format: {range_str}. Supported formats: A2:N28, A:C, A, A2")


def parse_multiple_excel_ranges(range_str):
    """
    Parse multiple Excel ranges separated by commas
    e.g., 'A2:A10,C2:C10' or 'A1:B5,D1:E5' or 'B,D' (simple column list)
    Returns list of range info dicts
    """
    # Split by comma and clean up whitespace
    range_parts = [part.strip() for part in range_str.split(',')]
    
    if len(range_parts) == 1:
        # Single range, use existing function
        return [parse_excel_range(range_parts[0])]
    
    # Multiple ranges - check if they're simple column letters
    ranges = []
    for part in range_parts:
        # Check if it's just a column letter (e.g., 'A', 'B', 'AA')
        if re.match(r'^[A-Z]+$', part.upper()):
            # Convert simple column letter to full column range
            col_letter = part.upper()
            ranges.append(parse_excel_range(col_letter))  # This will use the 'A' format
        else:
            # Regular range format
            ranges.append(parse_excel_range(part))
    
    return ranges


def apply_range_to_dataframe(df, range_info):
    """
    Apply Excel range selection to a pandas DataFrame
    Returns subset of the DataFrame based on the range
    """
    start_row = range_info['start_row']
    end_row = range_info['end_row']
    start_col = range_info['start_col']
    end_col = range_info['end_col']
    
    # Select the specified range
    # iloc uses [row_start:row_end+1, col_start:col_end+1] for inclusive ranges
    subset_df = df.iloc[start_row:end_row+1, start_col:end_col+1]
    
    return subset_df


def apply_multiple_ranges_to_dataframe(df, ranges):
    """
    Apply multiple Excel range selections and combine them
    Returns DataFrame with selected columns from different ranges
    """
    parts = []
    names = []
    excel_cols = []

    # Total number of columns/rows in the dataframe for bounds checking
    total_cols = len(df.columns)
    total_rows = len(df)

    for range_info in ranges:
        start_col = range_info['start_col']
        end_col = range_info['end_col']
        start_row = range_info.get('start_row', 0)
        end_row = range_info.get('end_row', total_rows - 1)

        # Clamp row indices to dataframe bounds
        if start_row < 0:
            start_row = 0
        if end_row >= total_rows:
            end_row = total_rows - 1
        if end_row < start_row:
            # nothing to extract from this range
            continue

        for col_idx in range(start_col, end_col + 1):
            if col_idx < 0 or col_idx >= total_cols:
                # skip columns outside dataframe
                continue

            # Extract column by absolute Excel index (map to df.columns)
            col_name = df.columns[col_idx]

            # Extract the slice of rows and reset index so different ranges align by row position
            series = df.iloc[start_row:end_row + 1, col_idx].reset_index(drop=True)

            parts.append(series)
            names.append(str(col_name))
            excel_cols.append(number_to_excel_column(col_idx))

    if parts:
        # Concatenate side-by-side. Different lengths are allowed; shorter series become NaN-padded.
        combined_df = pd.concat(parts, axis=1)
        combined_df.columns = names
        return combined_df, excel_cols
    else:
        return pd.DataFrame(), []


def get_range_preview(df, range_str, max_preview_rows=5):
    """
    Get a preview of the data within the specified Excel range
    """
    try:
        range_info = parse_excel_range(range_str)
        subset_df = apply_range_to_dataframe(df, range_info)
        
        # Get preview rows
        preview_df = subset_df.head(max_preview_rows)
        
        return {
            'success': True,
            'data': preview_df,
            'range_info': range_info,
            'total_rows': len(subset_df),
            'total_cols': len(subset_df.columns)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# Test the functions
if __name__ == "__main__":
    # Test column conversion
    print("Column tests:")
    print(f"A -> {excel_column_to_number('A')}")  # Should be 0
    print(f"Z -> {excel_column_to_number('Z')}")  # Should be 25
    print(f"AA -> {excel_column_to_number('AA')}")  # Should be 26
    print(f"AB -> {excel_column_to_number('AB')}")  # Should be 27
    
    print(f"0 -> {number_to_excel_column(0)}")  # Should be A
    print(f"25 -> {number_to_excel_column(25)}")  # Should be Z
    print(f"26 -> {number_to_excel_column(26)}")  # Should be AA
    
    # Test range parsing
    print("\nRange tests:")
    print(parse_excel_range("A1:C3"))
    print(parse_excel_range("A2-N28"))
