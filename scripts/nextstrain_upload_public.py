import subprocess

# Prompt user for confirmation
confirmation = input("⚠️WARNING⚠️ - Uploading to the Public Builds - Type 'upload public builds' to proceed: ").strip()

if confirmation != "upload public builds":
    print("Input did not match. Exiting.")
    exit()

print("Uploading seasonal influenza builds h1n1, h3n2 and vic to the Public Pekosz Lab Nextstrain...")

# Define the subtypes and their segments
subtypes = {
    "h3n2": ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"],
    "h1n1": ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"],
    "vic": ["pb2", "pb1", "pa", "ha", "np", "na", "mp", "ns"]
}

def nextstrain_login():
    # Log in to Nextstrain CLI
    print("Logging in to Nextstrain...")
    result = subprocess.run(["nextstrain", "login"], capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print("Error logging in to Nextstrain:")
        print(result.stderr)
    else:
        print("Successfully logged in to Nextstrain")

def nextstrain_upload(subtype):
    # Construct the nextstrain remote upload command
    command = [
        "nextstrain", "remote", "upload",
        f"nextstrain.org/groups/PekoszLab-Public/{subtype}"
    ] + [f"../auspice/{subtype}/{segment}.json" for segment in subtypes[subtype]]

    # Print progress message
    print(f"Uploading data for {subtype} to Nextstrain...")

    # Run the command
    result = subprocess.run(command, capture_output=True, text=True)

    # Check for errors
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