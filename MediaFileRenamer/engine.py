import re
from rules import extract_tokens, build_filename
from patterns import PatternType

def get_default_template(pattern):
    if pattern == PatternType.TV:
        return "{title} S{season}E{episode}"
    elif pattern == PatternType.FILM:
        return "{title} {year}"
    elif pattern == PatternType.SEQUENCE:
        return "{index} {title}"
    elif pattern == PatternType.IMAGE_SEQUENCE:
        return "{index:03}"
    else:
        return "{title}"

def detect_pattern(files):
    if not files:
        return PatternType.UNKNOWN

    tv_count = 0
    seq_count = 0
    img_seq_count = 0

    for f in files:
        name = f.lower()

        if re.search(r's\d{2}e\d{2}', name):
            tv_count += 1

        if re.search(r'^\d+', name):
            seq_count += 1

        if re.search(r'\d{3,4}', name) and any(ext in name for ext in [".png", ".jpg"]):
            img_seq_count += 1

    total = len(files)

    # Heuristic thresholds
    if tv_count / total > 0.6:
        return PatternType.TV
    if img_seq_count / total > 0.6:
        return PatternType.IMAGE_SEQUENCE
    if seq_count / total > 0.6:
        return PatternType.SEQUENCE

    return PatternType.UNKNOWN

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