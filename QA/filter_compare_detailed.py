#!/usr/bin/env python3
import pandas as pd
import os
import sys
from datetime import datetime

def filter_and_compare_single_file(file_num):
    """Process a single file number"""
    input_dir = "/Users/niranjgaurav/Desktop/Parquet_to_CSV/Inmobi_queries/queries-hashed.snappy"
    
    # File paths
    input_file = os.path.join(input_dir, f"queries-hashed.snappy_part_{file_num}.csv")
    result_file = os.path.join(input_dir, f"queries-hashed.snappy_part_{file_num}_result.csv")
    filtered_file = os.path.join(input_dir, f"queries-hashed.snappy_part_{file_num}_filtered.csv")
    final_file = os.path.join(input_dir, f"queries-hashed.snappy_part_{file_num}_final.csv")
    
    print(f"\n📋 Processing file {file_num}:")
    
    # Check if files exist
    if not os.path.exists(input_file):
        return False, f"Input file not found: {os.path.basename(input_file)}"
    
    if not os.path.exists(result_file):
        return False, f"Result file not found: {os.path.basename(result_file)}"
    
    try:
        # Step 1: Read and filter the input file
        print("   Reading input file...")
        df = pd.read_csv(input_file)
        print(f"   Total rows: {len(df)}")
        
        # Check if required columns exist
        required_cols = ['statement_type', 'client_application', 'execution_status', 'query_Hash']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return False, f"Missing required columns: {missing_cols}"
        
        # Apply filters
        filtered_df = df[
            (df['statement_type'] == 'SELECT') &
            (df['client_application'] == 'PowerBI') &
            (df['execution_status'] == 'FINISHED')
        ]
        
        print(f"   Filtered rows: {len(filtered_df)}")
        
        if len(filtered_df) == 0:
            return False, "No rows matched the filter criteria"
        
        # Save only unique query_Hash values from filtered data
        unique_hashes_df = filtered_df[['query_Hash']].drop_duplicates()
        unique_hashes_df.to_csv(filtered_file, index=False)
        print(f"   ✓ Saved filtered file: {os.path.basename(filtered_file)}")
        print(f"   Total executions: {len(filtered_df)}, Unique queries: {len(unique_hashes_df)}")
        
        # Step 2: Read result file and compare
        print("   Reading result file...")
        result_df = pd.read_csv(result_file)
        
        # Check if result file has required columns
        if 'original_query' not in result_df.columns:
            return False, "Result file missing 'original_query' column"
        
        # Get query hashes from filtered data
        filtered_hashes = set(unique_hashes_df['query_Hash'].dropna())
        print(f"   Unique query hashes to match: {len(filtered_hashes)}")
        
        # Extract hash from result file's original_query column
        result_df['extracted_hash'] = result_df['original_query'].str.extract(r'inmobi::([a-f0-9]{64})')
        matching_results = result_df[result_df['extracted_hash'].isin(filtered_hashes)]
        print(f"   Matching records in result file: {len(matching_results)}")
        
        # Keep only matching records from result file (all columns)
        final_df = matching_results.copy()
        
        # Save final data
        if len(final_df) > 0:
            final_df.to_csv(final_file, index=False)
            print(f"   ✓ Saved final file: {os.path.basename(final_file)}")
            print(f"   ✓ Total records in final file: {len(final_df)}")
            return True, "Success"
        else:
            return False, "No matching records found between filtered and result files"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    if len(sys.argv) != 3:
        print("Usage: python filter_compare_detailed.py <start_num> <end_num>")
        print("Example: python filter_compare_detailed.py 140 145")
        return
    
    try:
        start_num = int(sys.argv[1])
        end_num = int(sys.argv[2])
        
        if start_num > end_num:
            print("Error: Starting number must be less than or equal to ending number")
            return
        
        print(f"Processing files from {start_num} to {end_num}")
        print("=" * 60)
        
        success_count = 0
        failed_files = []
        
        for num in range(start_num, end_num + 1):
            success, message = filter_and_compare_single_file(num)
            if success:
                success_count += 1
            else:
                failed_files.append((num, message))
        
        # Summary
        print("\n" + "=" * 60)
        print(f"Summary: {success_count}/{end_num - start_num + 1} files processed successfully")
        
        if failed_files:
            print(f"\n❌ Failed files ({len(failed_files)}):")
            for file_num, reason in failed_files:
                print(f"   File {file_num}: {reason}")
        
        # Save detailed report
        report_file = f"processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(f"Processing Report\n")
            f.write(f"Range: {start_num} to {end_num}\n")
            f.write(f"Success: {success_count}/{end_num - start_num + 1}\n\n")
            
            if failed_files:
                f.write("Failed Files:\n")
                for file_num, reason in failed_files:
                    f.write(f"File {file_num}: {reason}\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
    except ValueError:
        print("Error: Please provide valid numbers")

if __name__ == "__main__":
    main()