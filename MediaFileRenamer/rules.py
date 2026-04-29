import os
import re

SUPPORTED_EXTENSIONS = (".mp4", ".m4v", ".mkv", ".avi", ".png", ".jpg")

AVAILABLE_TOKENS = [
    "title",
    "season",
    "episode",
    "episode2",
    "episode_title",
    "resolution",
    "year",
    "edition",
    "index",
]

# ---------------------------------------------------------------------------
# Metadata signal: any token whose first hyphen-segment matches one of these
# patterns marks the boundary between human-readable text and technical tags.
# ---------------------------------------------------------------------------
_METADATA_SIGNAL = re.compile(
    r'^(?:'
    r'\d{3,4}p'                                             # resolution: 1080p, 720p
    r'|BluRay|BDRip|WEBRip|WEB[.\-]?DL|HDTV|DVDRip|HDRip'   # release source
    r'|DSNP|AMZN|HMAX|NF|PCOK|ATVP'                         # streaming services
    r'|x26[45]|HEVC|AVC|H\.?26[45]|XviD'                    # video codec
    r'|DD\d|EAC3|AAC|DTS|AC3|FLAC|TrueHD|Atmos'             # audio codec
    r'|\d{3,4}MB|\d+GB'                                     # file size
    r'|PROPER|REPACK|EXTENDED|THEATRICAL|UNRATED'           # release flags
    r'|FRENCH|ENGLISH|ENG|SPANISH|GERMAN|ITALIAN|PORTUGUESE'# \
    r'|JAPANESE|JAP|KOREAN|CHINESE|MULTI|DUAL|VOSTFR|VO|VF' #  language tags
    r')$',
    re.IGNORECASE
)
# Season/Episode pattern - to allow handling of optional space between S/E parts and a hyphen or space before
# the second episode number — handles S01 E01, S01 E01-E02, S01E01E02.
_SE_PATTERN = re.compile(
    r'S(\d{1,2})\s*E(\d{1,2})(?:[-\s]?E(\d{1,2}))?',
    re.IGNORECASE
)
def _is_metadata_token(word: str) -> bool:
    # Return True if a single word looks like a technical metadata token.
    core = word.strip('.-').split('-')[0]
    parts = core.split('+') # Text every '+' joined segment - all must be metadata signals
    return all(bool(_METADATA_SIGNAL.match(p)) for p in parts)

def _split_at_metadata(text: str) -> tuple[str, str]:
    # Walk tokens left to right. Cut at first metadata signal.
    # Return (Human_readable, metadata_tail).
    # Works regardless of whether the separator is a hyphen, dot, space, or nothing
    words = text.split()
    for i, word in enumerate(words):
        if _is_metadata_token(word):
            return ' '.join(words[:i]).strip(' -'), ' '.join(words[i:])
    return text.strip(' -'), ''

def extract_tokens(filename, index=None):
    name, ext = os.path.splitext(filename)

    clean = name.replace('.', ' ').replace('_', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()

    tokens = {key: "" for key in AVAILABLE_TOKENS} # Create dicitonary of tokens from defined available tokens, set to empty strings
    tokens.update({
        "ext":      ext,
        "raw":      clean,
        "index":    str(index) if index is not None else ""
        })

    # -----------------------------
    # BRANCH A: TV Episode - SxxExx is the structural anchor
    # -----------------------------

    se_match = _SE_PATTERN.search(clean)
    
    if se_match:
        tokens["season"]   = se_match.group(1)
        tokens["episode"]  = se_match.group(2)
        tokens["episode2"] = se_match.group(3) or ""

        left  = clean[:se_match.start()].strip(' -')
        right = clean[se_match.end():].strip(' -')

        # Left side: pull year out of brackets, the rest is the series title
        year_match = re.search(r'[\(\[](19\d{2}|20\d{2})[\)\]]', left)
        if year_match:
            tokens["year"] = year_match.group(1)
            left = left[:year_match.start()].strip(' -')
        tokens["title"] = re.sub(r'\s+', ' ', left).strip()

        # Right side: Parenthetical/bracket groups are always metadata - strip them first,
        # then walk to find where the episode title ends.
        right_no_parens = re.sub(r'[\(\[][^\)\]]*[\)\]]', '', right).strip(' -')
        episode_title, _ = _split_at_metadata(right_no_parens)
        tokens["episode_title"] = re.sub(r'\s+', ' ', episode_title).strip()

        # Resolution: Scan the parens-stripped right side for the resolution so that
        # both "(1080p BluRay x265)" as well as bare "720p" are reliably found.
        res_match = re.search(r'(\d{3,4}p)', right_no_parens, re.IGNORECASE)
        if not res_match:  # fallback to original right for edge cases
            res_match = re.search(r'(\d{3,4}p)', right, re.IGNORECASE)
        if res_match:
            tokens["resolution"] = res_match.group(1)
    # -----------------------------
    # BRANCH B: Film - Year is the structural anchor
    # -----------------------------
    else:
        # Prefer a bracketed year; fall back to a bare 4-digit year
        year_match = (
            re.search(r'[\(\[](19\d{2}|20\d{2})[\)\]]', clean)
            or re.search(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)', clean)
            )

        if year_match:
            tokens["year"] = year_match.group(1)
            left  = clean[:year_match.start()].strip(' -')
            right = clean[year_match.end():].strip(' -')
        else:
            # If no year present - split the whole string at the first metadata token
            left, right = _split_at_metadata(clean)

        tokens["title"] = re.sub(r'\s+', ' ', left).strip()

        # The prefix before the first metadata token is the edition (e.g. "Directors Cut")
        edition, meta_tail = _split_at_metadata(right)
        if edition:
            tokens["edition"] = re.sub(r'\s+', ' ', edition).strip()

        res_match = re.search(r'(\d{3,4}p)', meta_tail, re.IGNORECASE)
        if res_match:
            tokens["resolution"] = res_match.group(1)

    return tokens

def build_filename(tokens: dict, template: str) -> str:
    result = template

    for key, value in tokens.items():
        result = result.replace(f"{{{key}}}", value)

    # Strip orphaned separators from both ends
    result = re.sub(r'^[\s\-]+|[\s\-]+$', '', result)
    # Collapse any internal runs of " - " that result from empty middle tokens
    result = re.sub(r'(\s*-\s*){2,}', ' - ', result)

    return result.strip() + tokens.get("ext", "")

# Sorting Key
def natural_sort_key(filename: str):
    # Split filename into a list of str/int chunks so that numeric segments are compared by value rather than lexicographically.
    return [
        int(chunk) if chunk.isdigit() else chunk.lower()
        for chunk in re.split(r'(\d+)', filename)
        ]