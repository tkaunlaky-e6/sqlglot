import typing as t
import re
import os
import sys
import json
import glob
import sqlglot
import logging
from datetime import datetime
import pandas as pd
import argparse

# Add the project root to Python path to find the apis module
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)
from sqlglot.optimizer.qualify_columns import quote_identifiers
from sqlglot import parse_one
from tqdm.auto import tqdm  # Import tqdm
from apis.utils.helpers import (
    strip_comment,
    unsupported_functionality_identifiers,
    extract_functions_from_query,
    categorize_functions,
    add_comment_to_query,
    replace_struct_in_query,
    ensure_select_from_values,
    extract_udfs,
    load_supported_functions,
    extract_db_and_Table_names,
    extract_joins_from_query,
    extract_cte_n_subquery_list,
    normalize_unicode_spaces,
    transform_table_part,
    set_cte_names_case_sensitively,
)

if t.TYPE_CHECKING:
    from sqlglot._typing import E

if t.TYPE_CHECKING:
    from sqlglot._typing import E

def convert_query_and_get_stats(query: str, from_sql: str, to_sql: str = "e6", feature_flags: dict = {}):
    """
    This function takes a SQL query and converts it to a specified dialect,
    returning a dictionary of statistics.
    """
    timestamp = datetime.now().isoformat()
    to_sql = to_sql.lower()

    if not query or not query.strip():
        return {
            "original_query": query, "converted_query": "",
            "supported_functions": [], "unsupported_functions": [],
            "udf_list": [], "unsupported_functions_after_transpilation": [],
            "executable": "NO", "tables_list": [],
            "joins_list": [], "cte_values_subquery_list": [],
            "error": True, "error_message": "Empty query received",
        }

    try:
        query = normalize_unicode_spaces(query)
        item = "condenast"
        query, comment = strip_comment(query, item)

        # Step 1: Parse the Original Query
        original_ast = parse_one(query, read=from_sql)
        tables_list = extract_db_and_Table_names(original_ast)

        supported_functions_in_e6 = load_supported_functions(to_sql)
        functions_as_keywords = ["LIKE", "ILIKE", "RLIKE", "AT TIME ZONE", "||", "DISTINCT", "QUALIFY"]
        exclusion_list = ["AS", "AND", "THEN", "OR", "ELSE", "WHEN", "WHERE", "FROM", "JOIN", "OVER", "ON", "ALL", "NOT", "BETWEEN", "UNION", "SELECT", "BY", "GROUP", "EXCEPT", "SETS"]
        function_pattern = r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\("
        keyword_pattern = r"\b(?:" + "|".join([re.escape(func) for func in functions_as_keywords]) + r")\b"

        all_functions = extract_functions_from_query(query, function_pattern, keyword_pattern, exclusion_list)
        supported, unsupported = categorize_functions(all_functions, supported_functions_in_e6, functions_as_keywords)
        from_dialect_function_list = load_supported_functions(from_sql)
        udf_list, unsupported = extract_udfs(unsupported, from_dialect_function_list)
        supported, unsupported = unsupported_functionality_identifiers(original_ast, unsupported, supported)

        values_ensured_ast = ensure_select_from_values(original_ast)
        cte_names_equivalence_ast = set_cte_names_case_sensitively(values_ensured_ast)
        query = cte_names_equivalence_ast.sql(from_sql)

        # Step 2: Transpile the Query
        tree = sqlglot.parse_one(query, read=from_sql, error_level=None)
        if feature_flags.get("USE_TWO_PHASE_QUALIFICATION_SCHEME", False):
            tree = transform_table_part(tree)
        tree2 = quote_identifiers(tree, dialect=to_sql)
        double_quotes_added_query = tree2.sql(dialect=to_sql, from_dialect=from_sql, pretty=feature_flags.get("PRETTY_PRINT", True))
        double_quotes_added_query = replace_struct_in_query(double_quotes_added_query)
        double_quotes_added_query = add_comment_to_query(double_quotes_added_query, comment)

        all_functions_converted_query = extract_functions_from_query(double_quotes_added_query, function_pattern, keyword_pattern, exclusion_list)
        supported_functions_in_converted_query, unsupported_functions_in_converted_query = categorize_functions(all_functions_converted_query, supported_functions_in_e6, functions_as_keywords)
        double_quote_ast = parse_one(double_quotes_added_query, read=to_sql)
        supported_in_converted, unsupported_in_converted = unsupported_functionality_identifiers(double_quote_ast, unsupported_functions_in_converted_query, supported_functions_in_converted_query)

        joins_list = extract_joins_from_query(original_ast)
        cte_values_subquery_list = extract_cte_n_subquery_list(original_ast)
        executable = "NO" if unsupported_in_converted else "YES"

        return {
            "original_query": query, "converted_query": double_quotes_added_query,
            "supported_functions": list(set(supported)), "unsupported_functions": list(set(unsupported)),
            "udf_list": list(set(udf_list)), "unsupported_functions_after_transpilation": list(set(unsupported_in_converted)),
            "executable": executable, "tables_list": list(set(tables_list)),
            "joins_list": joins_list, "cte_values_subquery_list": cte_values_subquery_list,
            "error": False, "error_message": "",
        }
    except Exception as e:
        return {
            "original_query": query, "converted_query": "",
            "supported_functions": [], "unsupported_functions": [],
            "udf_list": [], "unsupported_functions_after_transpilation": [],
            "executable": "NO", "tables_list": [], "joins_list": [],
            "cte_values_subquery_list": [], "error": True, "error_message": str(e),
        }

def main():
    parser = argparse.ArgumentParser(description="Convert CSV files in directory range.")
    parser.add_argument("--directory", required=True, help="Path to the directory containing CSV files.")
    parser.add_argument("--start", type=int, required=True, help="Start file number.")
    parser.add_argument("--end", type=int, required=True, help="End file number.")
    
    args = parser.parse_args()

    # Fixed parameters
    query_column = "QUERY_TEXT"
    from_sql = "databricks"
    to_sql = "e6"
    feature_flags = {}

    # Check if directory exists
    if not os.path.isdir(args.directory):
        print(f"❌ Error: Directory '{args.directory}' does not exist.")
        return

    # Get all CSV files in the directory
    all_csv_files = glob.glob(os.path.join(args.directory, '*.csv'))
    files_to_process = [f for f in all_csv_files if '_result.csv' not in os.path.basename(f)]
    
    if not files_to_process:
        print(f"No CSV files found in '{args.directory}'.")
        return

    print(f"Found {len(files_to_process)} CSV files in directory.")
    
    # Validate start and end parameters
    if args.start < 1:
        print(f"❌ Error: Start number must be >= 1.")
        return
    
    if args.start > len(files_to_process):
        print(f"❌ Error: Start number ({args.start}) is greater than total files ({len(files_to_process)}).")
        return
    
    if args.end > len(files_to_process):
        print(f"⚠️  Warning: End number ({args.end}) is greater than total files ({len(files_to_process)}). Using {len(files_to_process)} as end.")
        args.end = len(files_to_process)
    
    if args.start > args.end:
        print(f"❌ Error: Start number ({args.start}) is greater than end number ({args.end}).")
        return

    # Sort files for consistent numbering (handle numeric parts properly)
    # This ensures part_1 comes before part_10, part_2 before part_20, etc.
    import re
    def natural_sort_key(filename):
        # Extract numbers from filename and convert to int for proper sorting
        parts = re.split(r'(\d+)', filename)
        return [int(part) if part.isdigit() else part.lower() for part in parts]
    
    files_to_process.sort(key=natural_sort_key)
    
    # Filter out files that already have result files
    files_to_process_filtered = []
    skipped_files = []
    
    for file_path in files_to_process:
        base, ext = os.path.splitext(file_path)
        result_file_path = f"{base}_result{ext}"
        
        if os.path.exists(result_file_path):
            skipped_files.append(os.path.basename(file_path))
        else:
            files_to_process_filtered.append(file_path)
    
    if skipped_files:
        print(f"Skipping {len(skipped_files)} files that already have result files:")
        for skipped in skipped_files:
            print(f"  - {skipped}")
    
    if not files_to_process_filtered:
        print("All files already have result files. Nothing to process.")
        return
    
    # Get the files in the specified range (convert to 0-based indexing)
    selected_files = files_to_process_filtered[args.start-1:args.end] if args.end <= len(files_to_process_filtered) else files_to_process_filtered[args.start-1:]
    
    print(f"Processing files {args.start} to {min(args.end, len(files_to_process_filtered))} (out of {len(files_to_process_filtered)} eligible files)")
    
    # Show the order of files to be processed
    print("\nFiles will be processed in this order:")
    for idx, file_path in enumerate(selected_files, start=args.start):
        print(f"  {idx}. {os.path.basename(file_path)}")
    
    total_processed_count = 0

    # Process each selected file
    for i, file_path in enumerate(selected_files, start=args.start):
        print(f"\n{'='*60}")
        print(f"Processing file {i}/{len(files_to_process_filtered)}: {os.path.basename(file_path)}")
        print(f"{'='*60}")
        
        # Double-check result file doesn't exist (in case it was created since we started)
        base, ext = os.path.splitext(file_path)
        result_file_path = f"{base}_result{ext}"
        
        if os.path.exists(result_file_path):
            print(f"⚠️  Skipping: Result file already exists: {os.path.basename(result_file_path)}")
            continue
        
        try:
            input_df = pd.read_csv(file_path)

            if query_column not in input_df.columns:
                print(f"⚠️  Skipping: Query column '{query_column}' not found.")
                continue

            results = []
            for index, row in tqdm(input_df.iterrows(), total=input_df.shape[0], desc="Converting Queries"):
                query = row[query_column]
                if query and isinstance(query, str) and query.strip():
                    result = convert_query_and_get_stats(query, from_sql, to_sql, feature_flags)
                    results.append(result)
            
            if not results:
                print("No queries found or processed in this file.")
                continue

            # Generate output file path and save the results
            df = pd.DataFrame(results)
            df.to_csv(result_file_path, index=False)
            print(f"✅ Successfully converted {len(results)} queries.")
            print(f"   Result saved to: {os.path.basename(result_file_path)}")
            total_processed_count += 1

        except FileNotFoundError:
            print(f"❌ Error: Input file not found at {file_path}")
        except Exception as e:
            print(f"❌ An unexpected error occurred while processing {os.path.basename(file_path)}: {e}")

    print(f"\n{'='*60}")
    print(f"--- ALL TASKS COMPLETED ---")
    print(f"{'='*60}")
    print(f"Total files processed: {total_processed_count}")


if __name__ == "__main__":
    main()