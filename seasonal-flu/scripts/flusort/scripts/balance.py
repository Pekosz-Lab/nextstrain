'''
This script is intended to accept a single multi fasta or multiple fasta files (which will first be concatenated together) and perform the following operations: 
1. Concatenate input fastas if multiple inputs are provided
2. Pipe input fasta into `nextclade -sort` using custom reference dataset present at local port
3. Generate a master nextclade.tsv file containing quality information for each segment file: 
    - qc.overallScore
    - qc.overallStatus
    - in/del metrics
'''

