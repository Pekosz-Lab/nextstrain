import subprocess
import sys
import os
import shutil
import argparse

# Install required packages
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

packages = ['shutil']

for package in packages:
    try:
        __import__(package)
    except ImportError:
        install(package)

# Parse command line arguments
parser = argparse.ArgumentParser(description='pyflute Script')
parser.add_argument('-i', '--input', help='Input file in FASTA format')
parser.add_argument('-o', '--output', help='Output directory for the extracted sequences')
parser.add_argument('-r', '--stats', action='store_true', help='Generates a report for each sorted segment file')
args = parser.parse_args()

# Display logo
logo = '''       
                 ____    __       __  __  __             
               /\  _`\ /\ \     /\ \/\ \/\ \__          
 _____   __  __\ \ \L\_\ \ \    \ \ \ \ \ \ ,_\    __   
/\ '__`\/\ \/\ \\ \  _\/\ \ \  __\ \ \ \ \ \ \/  /'__`\ 
\ \ \L\ \ \ \_\ \\ \ \/  \ \ \L\ \\ \ \_\ \ \ \_/\  __/ 
 \ \ ,__/\/`____ \\ \_\   \ \____/ \ \_____\ \__\ \____/
  \ \ \/  `/___/> \\/_/    \/___/   \/_____/\/__/\/____/
   \ \_\     /\___/                                     
    \/_/     \/__/                                      
 v1.0 by Elgin Akin
'''

print(logo)
print("")

# Set input file and output directory
input_file = args.input
output_dir = args.output

# Check if input file is specified
if input_file is None:
    print("Input file is not specified. Exiting...")
    parser.print_help()
    sys.exit(1)

# Check if input file exists
if not os.path.exists(input_file):
    print(f"Input file '{input_file}' does not exist. Exiting...")
    sys.exit(1)

# Create output directory if it doesn't exist
if output_dir is None:
    output_dir = os.getcwd()
else:
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)


# Define segments and their regex patterns with case insensitivity
segments = {
    "pb2": "(?i).*_1$|.*\\|1$|.*\\|PB2$",
    "pb1": "(?i).*_2$|.*\\|2$|.*\\|PB1$",
    "pa": "(?i).*_3$|.*\\|3$|.*\\|PA$",
    "ha": "(?i).*_4$|.*\\|4$|.*\\|HA$",
    "np": "(?i).*_5$|.*\\|5$|.*\\|NP$",
    "na": "(?i).*_6$|.*\\|6$|.*\\|NA$",
    "mp": "(?i).*_7$|.*\\|7$|.*\\|MP$",
    "ns": "(?i).*_8$|.*\\|8$|.*\\|NS$"
}

# Loop through fasta and extract segments
total_segments = len(segments)
for index, (segment, regex) in enumerate(segments.items(), start=1):
    output_file = os.path.join(output_dir, f"{segment}.fasta")
    command = f"seqkit grep -r -p '{regex}' {input_file} > {output_file}"
    subprocess.run(command, shell=True)
    progress = index / total_segments * 100
    print(f"Sorting segment {segment}: {progress:.2f}% complete")

print('segments sorted')

# Execute "seqkit stats *.fasta" in the output directory
if args.stats:
    os.chdir(output_dir)
    subprocess.run("seqkit stats *.fasta", shell=True)