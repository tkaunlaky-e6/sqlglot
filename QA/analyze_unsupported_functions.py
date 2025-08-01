#!/usr/bin/env python3
import pandas as pd
import os
import sys
import json
import re
from collections import defaultdict
from datetime import datetime

def parse_unsupported_functions(func_string):
    """Parse the unsupported_functions string and extract individual functions"""
    if pd.isna(func_string) or func_string == '' or func_string == '[]':
        return []
    
    try:
        # Try to parse as JSON list
        if func_string.startswith('[') and func_string.endswith(']'):
            # Remove extra quotes and parse
            cleaned = func_string.replace("'", '"')
            functions = json.loads(cleaned)
            return functions if isinstance(functions, list) else [functions]
        else:
            # Handle other formats
            return [func_string.strip()]
    except:
        # Fallback: extract functions manually
        # Remove brackets and split by comma
        cleaned = func_string.strip('[]').replace("'", "").replace('"', '')
        if cleaned:
            return [f.strip() for f in cleaned.split(',') if f.strip()]
        return []

def analyze_unsupported_files(start_num, end_num):
    """Analyze all unsupported function files in the given range"""
    input_dir = "/Users/niranjgaurav/Desktop/Parquet_to_CSV/Inmobi_queries/queries-hashed.snappy"
    
    # Dictionary to store function counts: {function_name: {'total_count': int, 'chunks': set}}
    function_stats = defaultdict(lambda: {'total_count': 0, 'chunks': set()})
    
    processed_files = 0
    total_unsupported_records = 0
    
    print(f"Analyzing unsupported functions from files {start_num} to {end_num}")
    print("=" * 70)
    
    for file_num in range(start_num, end_num + 1):
        unsupported_file = os.path.join(input_dir, f"queries-hashed.snappy_part_{file_num}_final_unsupported.csv")
        
        if not os.path.exists(unsupported_file):
            continue
        
        try:
            # Read the unsupported file
            df = pd.read_csv(unsupported_file)
            
            if 'unsupported_functions' not in df.columns:
                print(f"   ⚠ File {file_num}: Missing 'unsupported_functions' column")
                continue
            
            processed_files += 1
            file_records = len(df)
            total_unsupported_records += file_records
            
            print(f"   📁 File {file_num}: {file_records} records with unsupported functions")
            
            # Process each record
            for _, row in df.iterrows():
                functions = parse_unsupported_functions(row['unsupported_functions'])
                
                for func in functions:
                    if func:  # Skip empty functions
                        function_stats[func]['total_count'] += 1
                        function_stats[func]['chunks'].add(file_num)
            
        except Exception as e:
            print(f"   ✗ Error processing file {file_num}: {e}")
            continue
    
    return function_stats, processed_files, total_unsupported_records

def update_summary_csv(function_stats, output_file):
    """Update existing CSV summary or create new one if it doesn't exist"""
    
    existing_stats = defaultdict(lambda: {'total_count': 0, 'chunks': set()})
    
    # Read existing summary if it exists
    if os.path.exists(output_file):
        try:
            existing_df = pd.read_csv(output_file)
            print(f"   📁 Found existing summary with {len(existing_df)} functions")
            
            for _, row in existing_df.iterrows():
                func_name = row['function_name']
                existing_stats[func_name]['total_count'] = row['total_occurrences']
                # Parse chunk list
                if pd.notna(row['chunk_list']) and row['chunk_list']:
                    chunks = [int(x.strip()) for x in str(row['chunk_list']).split(',') if x.strip()]
                    existing_stats[func_name]['chunks'] = set(chunks)
        except Exception as e:
            print(f"   ⚠ Error reading existing summary: {e}")
            print("   Creating new summary file...")
    else:
        print("   📝 Creating new summary file...")
    
    # Merge existing stats with new stats
    merged_stats = defaultdict(lambda: {'total_count': 0, 'chunks': set()})
    
    # Add existing stats
    for func_name, stats in existing_stats.items():
        merged_stats[func_name]['total_count'] += stats['total_count']
        merged_stats[func_name]['chunks'].update(stats['chunks'])
    
    # Add new stats
    for func_name, stats in function_stats.items():
        merged_stats[func_name]['total_count'] += stats['total_count']
        merged_stats[func_name]['chunks'].update(stats['chunks'])
    
    # Convert to list of dictionaries for DataFrame
    summary_data = []
    
    for func_name, stats in merged_stats.items():
        summary_data.append({
            'function_name': func_name,
            'total_occurrences': stats['total_count'],
            'number_of_chunks': len(stats['chunks']),
            'chunk_list': ','.join(map(str, sorted(stats['chunks'])))
        })
    
    # Sort by total occurrences (descending)
    summary_data.sort(key=lambda x: x['total_occurrences'], reverse=True)
    
    # Create DataFrame and save
    df = pd.DataFrame(summary_data)
    df.to_csv(output_file, index=False)
    
    return df

def main():
    if len(sys.argv) != 3:
        print("Usage: python analyze_unsupported_functions.py <start_num> <end_num>")
        print("Example: python analyze_unsupported_functions.py 140 200")
        return
    
    try:
        start_num = int(sys.argv[1])
        end_num = int(sys.argv[2])
        
        if start_num > end_num:
            print("Error: Starting number must be less than or equal to ending number")
            return
        
        # Analyze all unsupported function files
        function_stats, processed_files, total_records = analyze_unsupported_files(start_num, end_num)
        
        if not function_stats:
            print("\n❌ No unsupported functions found in any files!")
            return
        
        # Use fixed filename that gets updated
        output_file = "unsupported_functions_summary.csv"
        
        # Update summary CSV
        summary_df = update_summary_csv(function_stats, output_file)
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Files processed: {processed_files}")
        print(f"Total unsupported records: {total_records}")
        print(f"Unique unsupported functions: {len(function_stats)}")
        print(f"Summary saved to: {output_file}")
        
        print("\n🔝 TOP 10 MOST COMMON UNSUPPORTED FUNCTIONS:")
        print("-" * 70)
        print(f"{'Function Name':<40} {'Count':<8} {'Chunks':<8}")
        print("-" * 70)
        
        for i, row in summary_df.head(10).iterrows():
            func_name = row['function_name']
            if len(func_name) > 37:
                func_name = func_name[:34] + "..."
            print(f"{func_name:<40} {row['total_occurrences']:<8} {row['number_of_chunks']:<8}")
        
        # Create detailed report
        report_file = "unsupported_analysis_report.txt"
        with open(report_file, 'w') as f:
            f.write(f"Unsupported Functions Analysis Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Range: {start_num} to {end_num}\n")
            f.write(f"Files processed: {processed_files}\n")
            f.write(f"Total unsupported records: {total_records}\n")
            f.write(f"Unique unsupported functions: {len(function_stats)}\n\n")
            
            f.write("All Unsupported Functions (sorted by frequency):\n")
            f.write("-" * 80 + "\n")
            for _, row in summary_df.iterrows():
                f.write(f"{row['function_name']}: {row['total_occurrences']} occurrences in {row['number_of_chunks']} chunks\n")
                f.write(f"   Chunks: {row['chunk_list']}\n\n")
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
    except ValueError:
        print("Error: Please provide valid numbers")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()