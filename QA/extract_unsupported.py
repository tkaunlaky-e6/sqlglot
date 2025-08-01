#!/usr/bin/env python3
import pandas as pd
import os
import sys
from datetime import datetime

def process_final_file(file_num):
    """Extract records with unsupported functions from _final files"""
    input_dir = "/Users/niranjgaurav/Desktop/Parquet_to_CSV/Inmobi_queries/queries-hashed.snappy"
    
    # File paths
    final_file = os.path.join(input_dir, f"queries-hashed.snappy_part_{file_num}_final.csv")
    unsupported_file = os.path.join(input_dir, f"queries-hashed.snappy_part_{file_num}_final_unsupported.csv")
    
    print(f"\n📋 Processing final file {file_num}:")
    
    # Check if final file exists
    if not os.path.exists(final_file):
        return False, f"Final file not found: {os.path.basename(final_file)}"
    
    try:
        # Read the final file
        print("   Reading final file...")
        df = pd.read_csv(final_file)
        print(f"   Total records: {len(df)}")
        
        # Check if unsupported_functions column exists
        if 'unsupported_functions' not in df.columns:
            return False, "Column 'unsupported_functions' not found"
        
        # Filter for records with unsupported functions
        # Check for non-empty unsupported_functions (not null, not empty string, not just '[]')
        unsupported_df = df[
            df['unsupported_functions'].notna() & 
            (df['unsupported_functions'] != '') & 
            (df['unsupported_functions'] != '[]') &
            (df['unsupported_functions'].str.strip() != '[]')
        ]
        
        print(f"   Records with unsupported functions: {len(unsupported_df)}")
        
        if len(unsupported_df) == 0:
            print("   ✓ No unsupported functions found - all queries are supported!")
            return True, "No unsupported functions"
        
        # Save records with unsupported functions
        unsupported_df.to_csv(unsupported_file, index=False)
        print(f"   ✓ Saved unsupported records: {os.path.basename(unsupported_file)}")
        
        # Show sample of unsupported functions
        unique_unsupported = unsupported_df['unsupported_functions'].unique()
        print(f"   Unique unsupported function patterns: {len(unique_unsupported)}")
        
        # Show top 3 most common unsupported functions
        if len(unique_unsupported) > 0:
            print("   Most common unsupported functions:")
            for i, func in enumerate(unique_unsupported[:3]):
                count = len(unsupported_df[unsupported_df['unsupported_functions'] == func])
                print(f"     {i+1}. {func} (appears {count} times)")
        
        return True, f"Found {len(unsupported_df)} unsupported records"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    if len(sys.argv) != 3:
        print("Usage: python extract_unsupported.py <start_num> <end_num>")
        print("Example: python extract_unsupported.py 140 145")
        return
    
    try:
        start_num = int(sys.argv[1])
        end_num = int(sys.argv[2])
        
        if start_num > end_num:
            print("Error: Starting number must be less than or equal to ending number")
            return
        
        print(f"Extracting unsupported functions from files {start_num} to {end_num}")
        print("=" * 70)
        
        success_count = 0
        failed_files = []
        total_unsupported = 0
        files_with_unsupported = 0
        
        for num in range(start_num, end_num + 1):
            success, message = process_final_file(num)
            if success:
                success_count += 1
                if "Found" in message and "unsupported records" in message:
                    # Extract number from message like "Found 25 unsupported records"
                    count = int(message.split()[1])
                    total_unsupported += count
                    files_with_unsupported += 1
            else:
                failed_files.append((num, message))
        
        # Summary
        print("\n" + "=" * 70)
        print(f"Summary: {success_count}/{end_num - start_num + 1} files processed successfully")
        print(f"Files with unsupported functions: {files_with_unsupported}")
        print(f"Total records with unsupported functions: {total_unsupported}")
        
        if failed_files:
            print(f"\n❌ Failed files ({len(failed_files)}):")
            for file_num, reason in failed_files:
                print(f"   File {file_num}: {reason}")
        
        # Save detailed report
        report_file = f"unsupported_extraction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(f"Unsupported Functions Extraction Report\n")
            f.write(f"Range: {start_num} to {end_num}\n")
            f.write(f"Success: {success_count}/{end_num - start_num + 1}\n")
            f.write(f"Files with unsupported functions: {files_with_unsupported}\n")
            f.write(f"Total unsupported records: {total_unsupported}\n\n")
            
            if failed_files:
                f.write("Failed Files:\n")
                for file_num, reason in failed_files:
                    f.write(f"File {file_num}: {reason}\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
    except ValueError:
        print("Error: Please provide valid numbers")

if __name__ == "__main__":
    main()