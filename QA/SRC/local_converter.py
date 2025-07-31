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
    parser = argparse.ArgumentParser(description="Convert all SQL query files in subdirectories.")
    parser.add_argument("--input-dir", required=True, help="Path to the input directory containing subdirectories with CSV files.")
    parser.add_argument("--query-column", default="SQL_QUERY", help="The name of the column containing the SQL queries.")
    parser.add_argument("--from", dest="from_sql", default="snowflake", help="The source SQL dialect.")
    parser.add_argument("--to", dest="to_sql", default="e6", help="The target SQL dialect.")
    parser.add_argument("--feature-flags", help="JSON string of feature flags.")
    
    args = parser.parse_args()

    feature_flags = {}
    if args.feature_flags:
        try:
            feature_flags = json.loads(args.feature_flags)
        except json.JSONDecodeError as je:
            print(f"Error decoding feature flags: {je}")
            return

    # Check if input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"❌ Error: Input directory '{args.input_dir}' does not exist.")
        return

    # Get all subdirectories
    subdirs = []
    for item in os.listdir(args.input_dir):
        item_path = os.path.join(args.input_dir, item)
        if os.path.isdir(item_path):
            subdirs.append(item_path)

    if not subdirs:
        print(f"No subdirectories found in '{args.input_dir}'.")
        return

    print(f"Found {len(subdirs)} subdirectories to process.")
    
    # Filter out directories that already have result files
    eligible_dirs = []
    skipped_dirs = []
    
    for subdir in subdirs:
        subdir_name = os.path.basename(subdir)
        # Check if any *_result.csv files exist in this subdirectory
        result_files = glob.glob(os.path.join(subdir, '*_result.csv'))
        if result_files:
            skipped_dirs.append(subdir_name)
        else:
            eligible_dirs.append(subdir)

    print(f"  - Eligible for processing: {len(eligible_dirs)}")
    print(f"  - Skipped (already have result files): {len(skipped_dirs)}")
    
    if skipped_dirs:
        print("Skipped directories:")
        for dir_name in skipped_dirs:
            print(f"  - {dir_name}")

    if not eligible_dirs:
        print("No directories eligible for processing. All directories already have result files.")
        return

    total_processed_count = 0
    total_successful_dirs = 0

    # Process each eligible subdirectory
    for subdir in eligible_dirs:
        subdir_name = os.path.basename(subdir)
        print(f"\n{'='*60}")
        print(f"Processing subdirectory: {subdir_name}")
        print(f"{'='*60}")
        
        # Find all CSV files in the subdirectory, excluding ones that are already results.
        all_csv_files = glob.glob(os.path.join(subdir, '*.csv'))
        files_to_process = [f for f in all_csv_files if '_result.csv' not in os.path.basename(f)]

        if not files_to_process:
            print(f"⚠️  No non-result CSV files found in '{subdir_name}'.")
            continue

        print(f"Found {len(files_to_process)} file(s) to process in {subdir_name}.")
        dir_processed_count = 0

        # Process each file in the subdirectory
        for file_path in files_to_process:
            print(f"\n--- Processing file: {os.path.basename(file_path)} ---")
            try:
                input_df = pd.read_csv(file_path)

                if args.query_column not in input_df.columns:
                    print(f"⚠️  Skipping: Query column '{args.query_column}' not found.")
                    continue

                results = []
                for index, row in tqdm(input_df.iterrows(), total=input_df.shape[0], desc="Converting Queries"):
                    query = row[args.query_column]
                    if query and isinstance(query, str) and query.strip():
                        result = convert_query_and_get_stats(query, args.from_sql, args.to_sql, feature_flags)
                        results.append(result)
                
                if not results:
                    print("No queries found or processed in this file.")
                    continue

                # Generate output file path and save the results.
                base, ext = os.path.splitext(file_path)
                output_file_path = f"{base}_result{ext}"

                df = pd.DataFrame(results)
                df.to_csv(output_file_path, index=False)
                print(f"✅ Successfully converted {len(results)} queries.")
                print(f"   Result saved to: {os.path.basename(output_file_path)}")
                dir_processed_count += 1
                total_processed_count += 1

            except FileNotFoundError:
                print(f"❌ Error: Input file not found at {file_path}")
            except Exception as e:
                print(f"❌ An unexpected error occurred while processing {os.path.basename(file_path)}: {e}")

        if dir_processed_count > 0:
            total_successful_dirs += 1
            print(f"\n✅ Completed processing {subdir_name}: {dir_processed_count} files processed")
        else:
            print(f"\n⚠️  No files were successfully processed in {subdir_name}")

    print(f"\n{'='*60}")
    print(f"--- ALL TASKS COMPLETED ---")
    print(f"{'='*60}")
    print(f"Total subdirectories processed: {total_successful_dirs}")
    print(f"Total files processed: {total_processed_count}")
    print(f"Directories skipped (already had result files): {len(skipped_dirs)}")


if __name__ == "__main__":
    main()