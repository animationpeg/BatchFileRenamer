import os
import re

SUPPORTED_EXTENSIONS = (".mp4", ".m4v", ".mkv", ".avi", ".png", ".jpg", "xvid")

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
_BARE_EP_PATTERN = re.compile(r'(?<!\d)(\d{1,3})\s*$')
# Detects season.episode prefix before dot normalisation destroys it
# Matches: "01.01", "1.01", "01.1" at the start of the filename
_SE_DOT_PATTERN = re.compile(r'^(\d{1,2})\.(\d{1,2})\s*[-–]?\s*')
# Detects "Ep.01", "Ep. 01", "EP.1" etc. at the start of the filename
_EP_PREFIX_PATTERN = re.compile(r'Ep\.\s*(\d{1,3})\s*[-–]?\s*', re.IGNORECASE)
# Matches "Season 1 Episode 1", "Season 01 Episode 01" etc.
_SE_WORD_PATTERN = re.compile(
    r'Season\s*(\d{1,2})\s*Episode\s*(\d{1,2})',
    re.IGNORECASE
)
# Matches compact season+episode like 101, 201, 1001 (S01E01, S02E01, S10E01)
# Must be word-bounded to avoid matching years or other numbers
_SE_COMPACT_PATTERN = re.compile(
    r'(?<!\d)(\d{1,2})(\d{2})(?![\dp])'  # Exclude matches followed by p or another digit
)
# Detects title-NN-episode_title structure within a hyphen-separated string
_HYPHEN_EP_PATTERN = re.compile(r'^(.+?)-(\d{1,3})-(.+)$')

def _is_metadata_token(word: str) -> bool:
    # Return True if a single word looks like a technical metadata token.
    core = word.strip('.-[]').split('-')[0]
    parts = core.split('+') # Text every '+' joined segment - all must be metadata signals
    return all(bool(_METADATA_SIGNAL.match(p)) for p in parts)

def _split_at_metadata(text: str) -> tuple[str, str]:
    # Walk tokens left to right. Cut at first metadata signal.
    # Return (Human_readable, metadata_tail).
    # Works regardless of whether the separator is a hyphen, dot, space, or nothing
    words = text.split()
    for i, word in enumerate(words):
        if word.startswith(('[', '(')) or _is_metadata_token(word):
            return ' '.join(words[:i]).strip(' -'), ' '.join(words[i:])
    return text.strip(' -'), ''

def extract_tokens(filename, index=None, episode_index=None):
    name, ext = os.path.splitext(filename)

    # Check for season.episode prefix BEFORE dot normalisation
    se_dot_match = _SE_DOT_PATTERN.match(name)
    ep_prefix_match = _EP_PREFIX_PATTERN.search(name)

    clean = name.replace('.', ' ').replace('_', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()

    tokens = {key: "" for key in AVAILABLE_TOKENS} # Create dicitonary of tokens from defined available tokens, set to empty strings
    tokens.update({
        "ext":      ext,
        "raw":      clean,
        "index":    str(index).zfill(2) if index is not None else ""
        })
    # -----------------------------
    # BRANCH D: Ep. prefix format e.g. "Ep. 01 - The Boy in the Iceberg"
    # -----------------------------
    if ep_prefix_match:
        tokens["episode"] = ep_prefix_match.group(1).zfill(2)

        # Anything left of the Ep. match is the series title
        left = name[:ep_prefix_match.start()].replace('.', ' ').replace('_', ' ').strip(' -')
        if left:
            tokens["title"] = re.sub(r'\s+', ' ', left).strip()

        # Anything right of the match is the episode title
        remainder = name[ep_prefix_match.end():]
        remainder_clean = remainder.replace('.', ' ').replace('_', ' ').strip(' -')
        episode_title, _ = _split_at_metadata(remainder_clean)
        tokens["episode_title"] = re.sub(r'\s+', ' ', episode_title).strip()

        res_match = re.search(r'(\d{3,4}p)', remainder_clean, re.IGNORECASE)
        if res_match:
            tokens["resolution"] = res_match.group(1)
    
    # -----------------------------------------------------------------------
    # BRANCH E: Written out format e.g. "{title} Season 01 Episode 01 - {Episode_Title}"
    # -----------------------------------------------------------------------
    elif se_word_match := _SE_WORD_PATTERN.search(clean):
        tokens["season"]  = se_word_match.group(1).zfill(2)
        tokens["episode"] = se_word_match.group(2).zfill(2)

        left  = clean[:se_word_match.start()].strip(' -')
        right = clean[se_word_match.end():].strip(' -')

        tokens["title"] = re.sub(r'\s+', ' ', left).strip()

        episode_title, _ = _split_at_metadata(right)
        tokens["episode_title"] = re.sub(r'\s+', ' ', episode_title).strip()

        res_match = re.search(r'(\d{3,4}p)', right, re.IGNORECASE)
        if res_match:
            tokens["resolution"] = res_match.group(1)

    # -----------------------------
    # BRANCH A: TV Episode - SxxExx is the structural anchor
    # -----------------------------
    elif se_match := _SE_PATTERN.search(clean):
    
        tokens["season"]   = se_match.group(1).zfill(2)
        tokens["episode"]  = se_match.group(2).zfill(2)
        tokens["episode2"] = se_match.group(3).zfill(2) if se_match.group(3) else ""

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
    # BRANCH C: season.episode prefix format e.g. "01.01 Episode Name.mkv"
    # -----------------------------
    elif se_dot_match and not _SE_PATTERN.search(clean):
        tokens["season"]   = se_dot_match.group(1).zfill(2)
        tokens["episode"]  = se_dot_match.group(2).zfill(2)

        remainder = name[se_dot_match.end():]
        remainder_clean = remainder.replace('.', ' ').replace('_', ' ').strip(' -')
        episode_title, _ = _split_at_metadata(remainder_clean)
        tokens["episode_title"] = re.sub(r'\s+', ' ', episode_title).strip()

        res_match = re.search(r'(\d{3,4}p)', clean, re.IGNORECASE)
        if res_match:
            tokens["resolution"] = res_match.group(1)

    # -----------------------------------------------------------------------
    # BRANCH F: Compact format e.g. 101 = S01E01, 201 = S02E01
    # -----------------------------------------------------------------------
    else:
        clean_no_brackets = re.sub(r'[\(\[][^\)\]]*[\)\]]', '', clean)
        se_compact_match = _SE_COMPACT_PATTERN.search(clean_no_brackets)

        if se_compact_match:
            tokens["season"]  = se_compact_match.group(1).zfill(2)
            tokens["episode"] = se_compact_match.group(2).zfill(2)

            # Use match positions against clean_no_brackets for the split
            left  = clean_no_brackets[:se_compact_match.start()].strip(' -')
            right = clean_no_brackets[se_compact_match.end():].strip(' -')

            tokens["title"] = re.sub(r'\s+', ' ', left).strip()

            episode_title, _ = _split_at_metadata(right)
            tokens["episode_title"] = re.sub(r'\s+', ' ', episode_title).strip()

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
                left, right = _split_at_metadata(clean_no_brackets)
        
            hyphen_ep_match = _HYPHEN_EP_PATTERN.search(left)
            if hyphen_ep_match:
                tokens["title"]         = hyphen_ep_match.group(1).strip()
                tokens["episode"]       = hyphen_ep_match.group(2).zfill(2)
                tokens["episode_title"] = hyphen_ep_match.group(3).strip()  # ← clean of brackets already
            else:
                bare_ep_match = _BARE_EP_PATTERN.search(left)
                if bare_ep_match:
                    tokens["episode"] = bare_ep_match.group(1).zfill(2)
                    left = left[:bare_ep_match.start()].strip(' -')
                tokens["title"] = re.sub(r'\s+', ' ', left).strip()

            # The prefix before the first metadata token is the edition (e.g. "Directors Cut")
            edition, meta_tail = _split_at_metadata(right)
            if edition:
                tokens["edition"] = re.sub(r'\s+', ' ', edition).strip()

            res_match = re.search(r'(\d{3,4}p)', meta_tail, re.IGNORECASE)
            if res_match:
                tokens["resolution"] = res_match.group(1)

    # -----------------------------
    # DYNAMIC EPISODE FALLBACK
    # -----------------------------
    if not tokens["episode"] and episode_index is not None:
        tokens["episode"] = str(episode_index).zfill(2)


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