import os
import re


def extract_tokens(filename, index=None):
    name, ext = os.path.splitext(filename)

    clean = name.replace('.', ' ').replace('_', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()

    tokens = {
        "ext": ext,
        "raw": clean
    }

    # -----------------------------
    # EXISTING PATTERNS
    # -----------------------------

    # Season & Episode tokens
    match = re.search(r'S(\d{2})E(\d{2})(?:E(\d{2}))?', clean, re.IGNORECASE)
    tokens["season"] = match.group(1) if match else ""
    tokens["episode"] = match.group(2) if match else ""
    tokens["episode2"] = match.group(3) if match and match.group(3) else ""

    # Known Resolution formats
    res = re.search(r'(\d{3,4}p)', clean)
    tokens["resolution"] = res.group(1) if res else ""

    # Title extraction (everything before known tokens)
    match = re.search(r'(S\d{2}E\d{2}(?:E\d{2})?)', clean, re.IGNORECASE)
    if match:
        base = clean[:match.start()]
    else:
        base = clean
    base = base.strip()

    tokens["title"] = re.sub(r'\s+', ' ', base)

    # -----------------------------
    # SEQUENTIAL INDEX
    # -----------------------------
    tokens["index"] = str(index) if index is not None else ""

    return tokens


def build_filename(tokens, template):
    result = template

    for key, value in tokens.items():
        result = result.replace(f"{{{key}}}", value)

    result = re.sub(r'\s*-\s*$', '', result)
    return result.strip() + tokens.get("ext", "")