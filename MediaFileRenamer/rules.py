import os
import re


def extract_tokens(filename, index=None):
    name, ext = os.path.splitext(filename)

    clean = name.replace('.', ' ').replace('_', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()

    tokens = {
        "ext": ext,
        "raw": clean,
        "season": "",
        "episode": "",
        "episode2": "",
        "resolution": "",
        "title": "",
        "index": str(index) if index is not None else ""
    }

    # -----------------------------
    # EXISTING PATTERNS
    # -----------------------------

    #match = re.search(r'S(\d{2})E(\d{2})(?:E(\d{2}))?', clean, re.IGNORECASE)
    # Season & Episode tokens
    clean_title = clean

    se_match = re.search(r'S(\d{2})E(\d{2})(?:E(\d{2}))?', clean_title, re.IGNORECASE)
    if se_match:
        tokens["season"] = se_match.group(1)
        tokens["episode"] = se_match.group(2)
        tokens["episode2"] = se_match.group(3) if se_match.group(3) else ""

        # Remove full match from title
        clean_title = clean_title.replace(se_match.group(0), '')

    # Resolution token
    res_match = re.search(r'(\d{3,4}p)', clean_title, re.IGNORECASE)

    if res_match:
        tokens["resolution"] = res_match.group(1)
        clean_title = clean_title.replace(res_match.group(1), '')

    # Title extraction - everything that remains
    tokens["title"] = re.sub(r'\s+', ' ', clean_title).strip()

    return tokens

def build_filename(tokens, template):
    result = template

    for key, value in tokens.items():
        result = result.replace(f"{{{key}}}", value)

    result = re.sub(r'\s*-\s*$', '', result)
    return result.strip() + tokens.get("ext", "")