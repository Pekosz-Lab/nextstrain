"""
author: Elgin Akin
description: This script queries fludb and subtype-specific nextclade output and generates a summarized flat table. This can then be piped into PowerBI or quarto report workflows.
requirements: path to a populated fludb database
optional: 3 paths to unmodified h1n1, h3n2 or ibv (only victoria supported) nextclade.tsv output tables
"""

import sqlite3
import argparse
import pandas as pd

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Generate a summary table from an SQLite database and join clade information.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input SQLite database.")
    parser.add_argument("-o", "--output", required=True, help="Path to the output TSV file.")
    parser.add_argument("-e", "--excel", required=False, help="Path to the output Excel file.")
    parser.add_argument("-h1", "--h1_file", help="Path to the TSV file for H1 clades.")
    parser.add_argument("-h3", "--h3_file", help="Path to the TSV file for H3 clades.")
    parser.add_argument("-b", "--b_file", help="Path to the TSV file for Influenza B clades.")
    
    args = parser.parse_args()

    # Connect to the SQLite database
    conn = sqlite3.connect(args.input)
    cursor = conn.cursor()

    # SQL query to generate the initial table
    query = """
    SELECT 
        sequence_ID,
        sample_ID,
        type,
        subtype,
        date,
        passage_history,
        study_id,
        sequencing_run,
        location,
        database_origin,
        (CASE WHEN pb2 IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN pb1 IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN pa IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN ha IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN np IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN na IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN mp IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN ns IS NOT NULL THEN 1 ELSE 0 END) AS segment_count,
        CASE WHEN ha IS NOT NULL THEN 'yes' ELSE 'no' END AS has_ha,
        CASE WHEN ha IS NOT NULL AND na IS NOT NULL THEN 'yes' ELSE 'no' END AS has_ha_and_na,
        RTRIM(
            (CASE WHEN pb2 IS NOT NULL THEN 'pb2;' ELSE '' END) ||
            (CASE WHEN pb1 IS NOT NULL THEN 'pb1;' ELSE '' END) ||
            (CASE WHEN pa IS NOT NULL THEN 'pa;' ELSE '' END) ||
            (CASE WHEN ha IS NOT NULL THEN 'ha;' ELSE '' END) ||
            (CASE WHEN np IS NOT NULL THEN 'np;' ELSE '' END) ||
            (CASE WHEN na IS NOT NULL THEN 'na;' ELSE '' END) ||
            (CASE WHEN mp IS NOT NULL THEN 'mp;' ELSE '' END) ||
            (CASE WHEN ns IS NOT NULL THEN 'ns;' ELSE '' END),
            ';'
        ) AS segments_present
    FROM influenza_genomes;
    """

    # Execute the SQL query and fetch results
    cursor.execute(query)
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    
    # Create a pandas DataFrame from the SQLite query output
    sql_df = pd.DataFrame(rows, columns=column_names)

    # Process the clade data from TSV files
    clade_df = concatenate_clade_data(args.h1_file, args.h3_file, args.b_file)

    # Perform a single left join
    final_df = pd.merge(sql_df, clade_df, how="left", left_on="sequence_ID", right_on="seqName")

    # Drop unnecessary columns
    final_df.drop(columns=["seqName"], inplace=True)

    # Write the final table to a TSV file
    final_df.to_csv(args.output, sep="\t", index=False)
    print(f"Final table written to {args.output}")

    # Write the final table to an Excel file if specified
    if args.excel:
        final_df.to_excel(args.excel, index=False, engine='openpyxl')
        print(f"Final table written to {args.excel}")

    # Close the database connection
    conn.close()

def concatenate_clade_data(h1_file, h3_file, b_file):
    """Concatenates clade and subclade information from multiple TSV files into a single DataFrame."""
    frames = []
    for tsv_file in [h1_file, h3_file, b_file]:
        if tsv_file:
            df = pd.read_csv(tsv_file, sep="\t", usecols=["seqName", "clade", "subclade"])
            frames.append(df)
    if frames:
        return pd.concat(frames, ignore_index=True)
    else:
        return pd.DataFrame(columns=["seqName", "clade", "subclade"])

if __name__ == "__main__":
    main()
