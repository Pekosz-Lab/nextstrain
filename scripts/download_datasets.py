
# fetch nextclade datasets
# list of dataset subtypes
nextclade_dataset_subtypes = ["h1n1", "h3n2", "vic"]

# list of dataset segments 
nextclade_dataset_segments = ["ha", "na"]

nextclade dataset get -n flu_h1n1pdm_ha -o nextclade/flu/h1n1/ha
nextclade dataset get -n flu_h1n1pdm_na -o nextclade/flu/h1n1/na

nextclade dataset get -n flu_h3n2_ha -o nextclade/flu/h3n2/ha
nextclade dataset get -n flu_h3n2_na -o nextclade/flu/h3n2/na

nextclade dataset get -n flu_vic_ha -o nextclade/flu/h3n2/ha
nextclade dataset get -n flu_vic_na -o nextclade/flu/h3n2/na

#requirements 
# 1. overwrite the existing datasets 
# 2. download the datasets to their respetive directories

