from rules import extract_tokens, build_filename

def get_all_tokens(files):
    found_tokens = set() # Add into a set to not allow for duplicates

    for file in files:
        tokens = extract_tokens(file)
        found_tokens.update(tokens.keys())

    return sorted(found_tokens)
        
def process_files(files, template):
    results = []

    for i, file in enumerate(files, start=1):
        tokens = extract_tokens(file, index=i)
        new_name = build_filename(tokens, template)

        results.append((file, new_name))

    return results


def rename_files(folder, mappings, dry_run=True):
    import os

    for old_name, new_name in mappings:
        old_path = os.path.join(folder, old_name)
        new_path = os.path.join(folder, new_name)

        if old_name == new_name:
            continue

        if dry_run:
            print(f"[DRY] {old_name} -> {new_name}")
        else:
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)