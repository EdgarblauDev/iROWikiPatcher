import subprocess

CHANGED_FILES = "changed_files.txt"
PATCH_FILE = "patch/patchlist/patch3.txt"


def get_changes():
    """
    Reads the CHANGED_FILES file and returns a list of changed lines.

    Each line in the file is stripped of whitespace. This file is expected to
    contain one change per line.

    Returns:
        list[tuple]: A list of tuples (status, filename)
    """
    output = []

    # Open the CHANGED_FILES in read mode
    with open(CHANGED_FILES, "r", encoding='utf-8') as f:
        for line in f:
            # Remove any leading/trailing whitespace
            stripped_line = line.strip()
            if stripped_line:
                # Split the line on the first tab into status and filename
                status, filename = stripped_line.split("\t", 1)
                # Only add files that are .rgz and .gpf
                if filename.endswith(('.rgz', '.gpf')):
                    output.append((filename, status))

    return output


def current_patchfile():
    """
    Reads the PATCH_FILE and returns a dictionary of the current patch entries.

    It processes each line that does not start with '//' (which indicates a commented line).
    Each valid line is split into a number and a filename. The number is used as the key,
    and the filename as the value in the dictionary.

    Returns:
        dict: A dictionary mapping patch numbers (str) to filenames (str).
    """
    current = {}
    # Open the PATCH_FILE in read mode
    with open(PATCH_FILE, "r", encoding='utf-8') as f:
        # Process each line in the file
        for line in f:
            # Strip whitespace and check if the line is not commented out
            if not line.strip().startswith('//'):
                # Split the line into number and filename using the first space as delimiter
                num, file = line.split(' ', 1)
                # Store the number and file into the dictionary
                # .strip() to remove any trailing whitespace
                current[num] = file.strip()

    return current


def update_file_entries(file_path, valid_entries, github_changes):
    """
    Updates the file based on GitHub changes:
    - 'D' (Deleted): Comment out the last valid occurrence.
    - 'A' (Added): Append a new entry with the next available number.
    - 'M' (Modified): Comment out the last valid occurrence and add a new entry.

    :param file_path: Path to the main file.
    :param valid_entries: Dictionary {number: filename}.
    :param github_changes: List of tuples [(filename, status), ...].
    """
    # Read original file
    with open(file_path, "r", encoding='utf-8') as file:
        lines = file.readlines()

    # Identify deleted, added, and modified files
    deleted_files = {filename for filename,
                     status in github_changes if status == "D"}
    added_files = [filename for filename,
                   status in github_changes if status == "A"]
    modified_files = {filename for filename,
                      status in github_changes if status == "M"}

    # Find the last occurrence of each file
    last_occurrences = {}
    for num, filename in reversed(valid_entries.items()):  # Iterate in reverse
        if filename in deleted_files or filename in modified_files:
            if filename not in last_occurrences:
                last_occurrences[filename] = num

    # Get the next available number
    next_number = max(map(int, valid_entries.keys()), default=0) + 1

    # Update lines in memory
    updated_lines = []
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("//"):
            updated_lines.append(line)  # Keep already commented lines
            continue

        num, filename = stripped_line.split(" ", 1)

        if filename in last_occurrences and last_occurrences[filename] == num:
            updated_lines.append(f"//{line}")  # Comment out last occurrence
        else:
            updated_lines.append(line)  # Keep unchanged

    # Add new entries for added files
    for filename in added_files:
        updated_lines.append(f"{next_number} {filename}\n")
        next_number += 1

    # Handle modified files (comment old and add new)
    for filename in modified_files:
        updated_lines.append(f"{next_number} {filename}\n")
        next_number += 1

    # Write back the updated content
    with open(file_path, "w", encoding='utf-8') as file:
        file.writelines(updated_lines)


def commit_and_push_file(file_path, commit_message="Update patch file [skip ci]"):
    """
    Commits and pushes the updated file back to the repository.
    Uses '[skip ci]' in the commit message to prevent triggering GitHub Actions.

    :param file_path: Path to the file to commit and push.
    :param commit_message: Commit message (default includes '[skip ci]' to avoid CI triggers).
    """
    try:
        # Configure Git (needed in GitHub Actions)
        subprocess.run(["git", "config", "--global",
                       "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email",
                       "github-actions@github.com"], check=True)

        # Stage the file
        subprocess.run(["git", "add", file_path], check=True)

        # Commit with [skip ci] to prevent triggering GitHub Actions
        subprocess.run(["git", "commit", "-m", commit_message], check=True)

        # Push changes
        subprocess.run(["git", "push"], check=True)

        print(f"Successfully committed and pushed {file_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error committing and pushing file: {e}")


if __name__ == "__main__":
    changes = get_changes()
    entries = current_patchfile()
    update_file_entries(PATCH_FILE, entries, changes)
    commit_and_push_file(PATCH_FILE)
