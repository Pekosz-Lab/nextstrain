import subprocess

print("Uploading seasonal influenza builds h1n1, h3n2, and vic to the PRIVATE Pekosz Lab Nextstrain...")

subtypes = {
    "h3n2": ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"],
    "h1n1": ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"],
    "vic": ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns", "genome"]
}

def nextstrain_login():
    """Log in to Nextstrain CLI."""
    print("Logging in to Nextstrain...")
    result = subprocess.run(["nextstrain", "login"], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error logging in to Nextstrain:")
        print(result.stderr)
    else:
        print("Successfully logged in to Nextstrain")

def nextstrain_upload(subtype):
    """Upload Nextstrain JSON files for a given subtype."""
    command = ([
        "nextstrain", "remote", "upload",
        f"nextstrain.org/groups/PekoszLab-Public/mostafa/iav24-25/{subtype}"
    ] + 
    [f"auspice/{subtype}/{segment}.json" for segment in subtypes[subtype]] +
    [f"auspice/{subtype}/{segment}_tip-frequencies.json" for segment in subtypes[subtype]])

    print(f"Uploading data for {subtype} to Nextstrain...")
    
    
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error uploading data for {subtype}:")
        print(result.stderr)
    else:
        print(f"Successfully uploaded data for {subtype}")

# Log in to Nextstrain CLI
nextstrain_login()

# Upload data for each subtype
for subtype in subtypes.keys():
    nextstrain_upload(subtype)