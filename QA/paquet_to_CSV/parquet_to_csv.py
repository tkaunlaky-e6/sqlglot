import pandas as pd
import math
import os
import glob

# --- Requirements ---
# This script requires the pandas library and an engine for reading Parquet files.
# If you encounter an error like "Unable to find a usable engine", you need to
# install one of the required libraries. 'pyarrow' is recommended.
#
# You can install the necessary libraries using pip:
# pip install pandas pyarrow
# --------------------


# --- Configuration ---
# Path to the FOLDER containing your Parquet files
# IMPORTANT: Replace this with the actual path to your folder.
parquet_folder_path = "/Users/tanaykulkarni/Documents/parquet_to_csv/csv_chunks_filtered/ccip_folder"

# Directory where the output folders and CSV files will be saved
output_dir = "more_filtered"

# Number of rows per CSV file
chunk_size = 2000

# --- Script ---

# Check if the source directory exists before proceeding
if not os.path.isdir(parquet_folder_path):
    print(f"Error: The folder was not found at '{parquet_folder_path}'")
    print("Please update the 'parquet_folder_path' variable with the correct location of your folder.")
else:
    try:
        # Find all files with a .parquet extension in the specified folder
        search_pattern = os.path.join(parquet_folder_path, "*.parquet")
        parquet_files = glob.glob(search_pattern, recursive=True)

        if not parquet_files:
            print(f"No Parquet files found in '{parquet_folder_path}'.")
        else:
            print(f"Found {len(parquet_files)} Parquet file(s). Processing each file into its own folder...")
            
            # Create the main output directory if it doesn't already exist
            os.makedirs(output_dir, exist_ok=True)
            print(f"Main output directory '{output_dir}' is ready.\n")

            # Loop through each found parquet file
            for file_path in parquet_files:
                print(f"--- Processing file: {os.path.basename(file_path)} ---")
                
                # Derive the base filename from the current parquet file's name
                base_filename = os.path.splitext(os.path.basename(file_path))[0]

                # Create a dedicated output folder for this file
                file_specific_output_dir = os.path.join(output_dir, base_filename)
                os.makedirs(file_specific_output_dir, exist_ok=True)
                print(f"Created output sub-folder: {file_specific_output_dir}")

                # Read the single Parquet file into a DataFrame
                df = pd.read_parquet(file_path)

                # --- Filtering and Selection ---
                print("Applying filters...")
                # Condition 1 & 2: state and statement_type
                condition1 = (df['state'] == 'SUCCEEDED')
                condition2 = (df['statement_type'] == 'DML')
                
                # Combine initial conditions
                combined_conditions = condition1 & condition2

                # Add text-based filters on 'hashed_query' column if it exists
                if 'hashed_query' in df.columns:
                    print("  - Filtering by 'hashed_query' content (excluding merge, execute, insert, unload)...")
                    # Convert 'hashed_query' to lowercase once and handle potential null (NaN) values
                    query_lower = df['hashed_query'].str.lower().fillna('')
                    
                    # Conditions 3-6: Exclude rows containing specific keywords
                    condition3 = ~query_lower.str.contains('merge')
                    condition4 = ~query_lower.str.contains('execute')
                    condition5 = ~query_lower.str.contains('insert')
                    condition6 = ~query_lower.str.contains('unload')
                    
                    # Add these to the combined conditions
                    combined_conditions = combined_conditions & condition3 & condition4 & condition5 & condition6
                else:
                    print("  - Warning: 'hashed_query' column not found. Skipping text-based filters.")

                # Apply all combined filters to the DataFrame
                df_filtered = df[combined_conditions]

                # Select and rename the final columns
                df_final = df_filtered[['query_hash', 'hashed_query']].copy()
                df_final.rename(columns={
                    'query_hash': 'UNQ_ALIAS',
                    'hashed_query': 'QUERY_TEXT'
                }, inplace=True)

                # --- Chunking and Saving ---
                num_chunks = math.ceil(len(df_final) / chunk_size)

                if num_chunks > 0:
                    print(f"Found {len(df_final)} matching rows. Saving into {num_chunks} chunk(s) of size {chunk_size}.")
                    for i in range(num_chunks):
                        start_index = i * chunk_size
                        end_index = start_index + chunk_size
                        chunk_df = df_final.iloc[start_index:end_index]

                        output_path = os.path.join(file_specific_output_dir, f"{base_filename}_part_{i+1}.csv")
                        chunk_df.to_csv(output_path, index=False)
                        print(f"  -> Successfully saved: {output_path}")
                else:
                    print("No data matched the filter criteria in this file. No CSVs created for it.")
                
                print("-" * (len(os.path.basename(file_path)) + 22) + "\n")

    except ImportError:
        print("\n--- FIX ---")
        print("Error: Missing required library. This script needs 'pyarrow' to read Parquet files.")
        print("Please install it by running this command in your terminal:")
        print("pip install pyarrow")
        print("-----------")
    except KeyError as e:
        print(f"\nAn error occurred: A required column is missing from the data: {e}")
        print("Please ensure your Parquet files contain the columns: 'state', 'statement_type', 'query_hash', and 'hashed_query'.")
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")
