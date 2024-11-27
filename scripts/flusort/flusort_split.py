import argparse
from Bio import SeqIO

def filter_sequences(fasta_file_path, sequence_id=None, segment_number=None, influenza_type=None, ha_subtype=None, na_subtype=None, genome_completeness=None, sequence=None):
    """
    Filter sequences from a FASTA file based on specified attributes.

    Parameters:
    - fasta_file_path (str): Path to the input FASTA file.
    - sequence_id (str or None): Sequence ID to filter on. If None, no filter is applied.
    - segment_number (int or None): Segment number to filter on. If None, no filter is applied.
    - influenza_type (str or None): Influenza type to filter on. If None, no filter is applied.
    - ha_subtype (str or None): HA subtype to filter on. If None, no filter is applied.
    - na_subtype (str or None): NA subtype to filter on. If None, no filter is applied.
    - genome_completeness (str or None): Genome completeness to filter on. If None, no filter is applied.
    - sequence (str or None): Sequence to filter on. If None, no filter is applied.

    Returns:
    - filtered_entries (list): List of dictionaries containing information for filtered sequences.
    """
    # Parse the sequences and extract information
    sequence_data_list = []
    with open(fasta_file_path, "r") as fasta_file:
        for record in SeqIO.parse(fasta_file, "fasta"):
            header_parts = record.id.split("_")
            if len(header_parts) == 6:
                seq_id, seg_number, influenza, ha_sub, na_sub, genome_comp = header_parts
                seg_number = int(seg_number)
                seq = str(record.seq)
                sequence_data_list.append({
                    "sequence_id": seq_id,
                    "segment_number": seg_number,
                    "influenza_type": influenza,
                    "ha_subtype": ha_sub,
                    "na_subtype": na_sub,
                    "genome_completeness": genome_comp,
                    "sequence": seq
                })
            else:
                print(f"Invalid header format: {record.id}")

    # Filter the sequence_data_list based on specified attributes
    filtered_entries = sequence_data_list
    if sequence_id is not None:
        filtered_entries = [data for data in filtered_entries if data["sequence_id"] == sequence_id]
    if segment_number is not None:
        filtered_entries = [data for data in filtered_entries if data["segment_number"] == segment_number]
    if influenza_type is not None:
        filtered_entries = [data for data in filtered_entries if data["influenza_type"] == influenza_type]
    if ha_subtype is not None:
        filtered_entries = [data for data in filtered_entries if data["ha_subtype"] == ha_subtype]
    if na_subtype is not None:
        filtered_entries = [data for data in filtered_entries if data["na_subtype"] == na_subtype]
    if genome_completeness is not None:
        filtered_entries = [data for data in filtered_entries if data["genome_completeness"] == genome_completeness]
    if sequence is not None:
        filtered_entries = [data for data in filtered_entries if data["sequence"] == sequence]

    return filtered_entries


def write_fasta(filtered_entries, output_file):
    """
    Write filtered sequences to a new FASTA file.

    Parameters:
    - filtered_entries (list): List of dictionaries containing filtered sequence information.
    - output_file (str): Path to the output FASTA file.
    """
    with open(output_file, "w") as output_fasta:
        for entry in filtered_entries:
            fasta_header = f">{entry['sequence_id']}"
            output_fasta.write(f"{fasta_header}\n")
            output_fasta.write(f"{entry['sequence']}\n")

def main():
    parser = argparse.ArgumentParser(description='Filter sequences from a FASTA file and optionally split them into separate files based on segment number.')
    parser.add_argument('-i', '--input', help='Input FASTA file path', required=True)
    parser.add_argument('-o', '--output', help='Output FASTA file path')
    parser.add_argument('--sequence_id', help='Sequencs ID to filter on')
    parser.add_argument('--segment_number', type=int, help='Segment number to filter on')
    parser.add_argument('--influenza_type', help='Influenza type to filter on')
    parser.add_argument('--ha_subtype', help='HA subtype to filter on')
    parser.add_argument('--na_subtype', help='NA subtype to filter on')
    parser.add_argument('--genome_completeness', help='Genome completeness to filter on')
    parser.add_argument('--sequence', help='Sequence to filter on')
    parser.add_argument('-s', '--split', action='store_true', help='Split filtered sequences into separate files based on segment number')
    args = parser.parse_args()

    filtered_entries = filter_sequences(args.input, args.sequence_id, args.segment_number, args.influenza_type, args.ha_subtype, args.na_subtype, args.genome_completeness, args.sequence)

    if args.split:
        # Split filtered sequences into separate files based on segment number
        for seg_num in set(entry['segment_number'] for entry in filtered_entries):
            seg_filtered_entries = [entry for entry in filtered_entries if entry['segment_number'] == seg_num]
            output_file = f"segment_{seg_num}_sorted.fasta"
            write_fasta(seg_filtered_entries, output_file)
            print(f"Filtered sequences for segment {seg_num} written to {output_file}.")
    else:
        # Write all filtered sequences to a single file
        if args.output:
            write_fasta(filtered_entries, args.output)
            print(f"Filtered sequences written to {args.output}.")
        else:
            print("No output file specified. Use -o/--output to specify the output file path.")

if __name__ == "__main__":
    main()