"""
Kid-safe language filter for Build Your Own Starship and Smart Assistant.

Blocks real curse words and hiding tricks (leet, spacing, repeated letters).
Normal English words (cockpit, class, therapist, encouraging) stay allowed.

Also blocks:
  - Letter spam / keyboard mash (ijudhsjsdkjhsdfkjfuckskdjsjsj)
  - Curse words buried inside long gibberish strings
  - Repeated-letter tricks (fuuuuck, shiiiit)
"""

import re
import unicodedata

# Characters kids might use to hide letters inside words.
_LEET_BASE = {
    "4": "a", "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a",
    "8": "b",
    "©": "c", "¢": "c", "(": "c", "{": "c", "[": "c", "<": "c",
    "3": "e", "€": "e", "ê": "e", "é": "e", "è": "e",
    "6": "g", "9": "g",
    "!": "i", "1": "i", "|": "i", "í": "i", "ì": "i",
    "0": "o", "ö": "o", "ó": "o", "ò": "o",
    "5": "s", "$": "s", "§": "s",
    "7": "t", "+": "t",
    "2": "z",
}

_LEET_VARIANTS = (
    str.maketrans({**_LEET_BASE, "@": "a"}),
    str.maketrans({**_LEET_BASE, "@": "u"}),
)

_LEET_CHAR_SET = set(_LEET_BASE.keys()) | {"@"}

_HOMOGLYPH_MAP = str.maketrans({
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p", "\u0441": "c",
    "\u0443": "u", "\u0445": "x", "\u044a": "b", "\u0456": "i", "\u04cf": "l",
    "\u0501": "d", "\u051b": "t", "\u03b1": "a", "\u03b5": "e", "\u03bf": "o",
    "\u03c1": "p", "\u03c2": "s", "\u03c3": "s", "\u03c5": "u", "\u03c7": "x",
    "\u03ba": "k", "\u03bd": "v", "\u03b9": "i", "\u03c4": "t",
})

_INVISIBLE_CHARS = re.compile(
    "[\u200b\u200c\u200d\u2060\ufeff\u00ad\u034f\u061c\u180e\u2061\u2062\u2063\u2064]+"
)

# Whole tokens always OK — includes game answer words and common false-alarm vocabulary.
_SAFE_TOKENS = frozenset({
    # Design-lab personality & skills
    "friendly", "kind", "patient", "witty", "calm", "encouraging", "encourage",
    "encouragement", "helpful", "cheerful", "homework", "study", "learn", "organize",
    "remind", "schedule", "code", "research", "translate", "calculate", "math",
    "search", "joke", "weather", "music", "remember", "preferences", "history",
    "notes", "birthday", "favorite", "voice", "text", "both", "chat", "speak",
    "screen", "sign", "privacy", "safe", "permission", "teacher", "parent", "honest",
    "respect", "nova", "byte", "echo", "lumen", "atlas", "spark",
    # ass- / class- family
    "assistant", "assassin", "assassinate", "assault", "assert", "assign", "assist",
    "assistance", "assistive", "association", "assume", "assignment", "embarrass",
    "embarrassed", "passion", "passionate", "compass", "surpass", "bypass",
    "classic", "class", "classes", "classroom", "classify", "classical",
    "glass", "grass", "grasshopper", "grape", "bass", "brass", "mass", "massive",
    "pass", "passage", "passenger", "cockpit", "peacock", "cockatoo", "shuttlecock",
    # analysis / express / document family
    "analytics", "analyze", "analysis", "analyst", "express", "expression",
    "document", "accumulate", "circumstance", "subtitle", "entity", "title", "titles",
    # other innocent embedded-pattern words
    "therapist", "therapy", "helmet", "hello", "shell", "hellish", "damnation",
    "helicopter", "skill", "skills", "skillful", "starship", "scrap", "scrape",
    "scrapebook", "butter", "button", "byte", "bytes", "mocha", "compass",
    "drape", "embassy", "learning", "programming", "compassion", "compassionate",
    "organize", "organise", "signature", "thermostat", "predict", "dictionary",
    "mars", "alex", "captain", "owen", "hopper", "mentor", "professor", "coach",
})

# Blocked when typed as a whole word.
_BLOCKLIST = frozenset({
    "anal", "anus", "arse", "ass", "asshole", "bastard", "bitch", "bloody",
    "blowjob", "bollock", "boner", "boob", "bugger", "bullshit", "bum",
    "butt", "clit", "cock", "coon", "crap", "cum", "cunt", "damn", "dick",
    "dildo", "douche", "dyke", "fag", "faggot", "fuck", "fucker", "fucking",
    "goddamn", "hooker", "jizz", "kike",
    "kys", "lesbo", "milf", "muff", "nazi", "negro", "nigga", "nigger",
    "penis", "piss", "porn", "prick", "pussy", "queer", "rape", "rapist",
    "retard", "scrotum", "sex", "shit", "shitty", "slut", "spic",
    "tit", "tits", "twat", "vagina", "wank", "whore",
})

# Unmistakable profanity — also caught inside glued words (SuperShitRocket).
# Short blocks like cock/ass/dick only match as whole tokens, not inside cockatoo/class.
_CLEAR_EMBEDDED = frozenset({
    "fuck", "fucker", "fucking", "shit", "shitty", "bitch", "bullshit",
    "asshole", "blowjob", "nigger", "nigga", "faggot", "pussy", "whore",
    "cunt", "bastard", "douche", "dildo", "rape", "rapist",
    "penis", "vagina", "porn", "slut", "retard", "wank", "twat", "goddamn",
    "hooker", "scrotum",
})

# Phonetic patterns — only applied when input looks like hiding (leet / spam / short).
_PHONETIC_PATTERNS = (
    (re.compile(r"ph+u+[qck]+", re.I), "fuck"),
    (re.compile(r"f+u+[qck]+", re.I), "fuck"),
    (re.compile(r"f+a+c+k+", re.I), "fuck"),
    (re.compile(r"f+v+c+k+", re.I), "fuck"),
    (re.compile(r"f+c+k+", re.I), "fuck"),
    (re.compile(r"f+k+", re.I), "fuck"),
    (re.compile(r"s+h+[iy1!]+t+", re.I), "shit"),
    (re.compile(r"s+h+[iy]+e+t*", re.I), "shit"),
    (re.compile(r"s+h+t+", re.I), "shit"),
    (re.compile(r"b+i+[ao]*t+c*h*", re.I), "bitch"),
    (re.compile(r"b+t+c+h+", re.I), "bitch"),
    (re.compile(r"a+z+", re.I), "ass"),
    (re.compile(r"d+i+[ck]+", re.I), "dick"),
    (re.compile(r"d+c+k+", re.I), "dick"),
    (re.compile(r"c+v+n+t+", re.I), "cunt"),
    (re.compile(r"c+n+t+", re.I), "cunt"),
    (re.compile(r"p+u+s+s+y+", re.I), "pussy"),
    (re.compile(r"w+h+o+r+e+", re.I), "whore"),
)

_PHRASES = (
    "piece of shit", "son of a bitch", "mother fucker", "motherfucker",
    "go to hell", "suck my", "eat shit", "fuck you", "fuck off",
    "what the fuck", "shut the fuck", "stfu",
)

_REPEAT_SPAM = re.compile(r"(.)\1+")
_VOWELS = frozenset("aeiou")

# Long single-token gibberish (random key mashing).
_KEYBOARD_MASH_MIN_LEN = 16

_FRIENDLY_MESSAGE = "Please use friendly words — this is a kid-friendly lab!"


def friendly_message() -> str:
    return _FRIENDLY_MESSAGE


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _strip_invisible(text: str) -> str:
    return _INVISIBLE_CHARS.sub("", text)


def _strip_homoglyphs(text: str) -> str:
    return text.translate(_HOMOGLYPH_MAP)


def _apply_ph_rule(text: str) -> str:
    return re.sub(r"\bph", "f", text, flags=re.IGNORECASE)


def _apply_v_evasions(text: str) -> str:
    text = re.sub(r"fv", "fu", text, flags=re.IGNORECASE)
    text = re.sub(r"clv", "clu", text, flags=re.IGNORECASE)
    return text


def _apply_phonetic_evasions(text: str) -> str:
    for pattern, replacement in _PHONETIC_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _collapse_repeats_aggressive(text: str) -> str:
    """fuuuuck -> fuck, shiiiit -> shit."""
    if not text:
        return ""
    out = [text[0]]
    for ch in text[1:]:
        if ch != out[-1]:
            out.append(ch)
    return "".join(out)


def _preprocess_surface(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _strip_invisible(text)
    text = _strip_homoglyphs(text)
    text = _strip_accents(text)
    return text.lower()


def _has_letter_spam(token: str) -> bool:
    """True when letters are repeated to hide a curse (fuuuuck, shiiit)."""
    return bool(_REPEAT_SPAM.search(token))


def _has_leet_or_symbols(token: str) -> bool:
    """True when leet speak or masking symbols are present."""
    for ch in token:
        if ch in _LEET_CHAR_SET:
            return True
    return False


def _needs_phonetic_check(token: str) -> bool:
    """Phonetic rules only on short tokens or ones that look like hiding."""
    return len(token) <= 6 or _has_letter_spam(token) or _has_leet_or_symbols(token)


def _normalize_with_map(text: str, leet_map: dict, collapse: bool, phonetic: bool) -> str:
    text = _preprocess_surface(text)
    # Star masking (f**k, sh*t) is not checked — skip phonetic when stars are present.
    use_phonetic = phonetic and "*" not in text
    text = _apply_ph_rule(text)
    text = _apply_v_evasions(text)
    if use_phonetic:
        text = _apply_phonetic_evasions(text)
    text = text.translate(leet_map)
    text = re.sub(r"[^a-z0-9]", "", text)
    if use_phonetic:
        text = _apply_phonetic_evasions(text)
    if collapse:
        return _collapse_repeats_aggressive(text)
    return text


def _normalize_variants(text: str, *, phonetic: bool) -> list[str]:
    variants = []
    for leet_map in _LEET_VARIANTS:
        variants.append(_normalize_with_map(text, leet_map, collapse=False, phonetic=phonetic))
        variants.append(_normalize_with_map(text, leet_map, collapse=True, phonetic=phonetic))
    seen = set()
    unique = []
    for item in variants:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _normalize_token(token: str) -> list[str]:
    phonetic = _needs_phonetic_check(token)
    return _normalize_variants(token, phonetic=phonetic)


def _normalize_packed(text: str) -> list[str]:
    return _normalize_variants(text, phonetic=True)


def _tokenize(text: str) -> list[str]:
    cleaned = _preprocess_surface(text)
    return [part for part in re.split(r"[^a-zA-Z0-9]+", cleaned) if part]


def _contains_embedded_clear_profanity(text: str) -> bool:
    """True when unmistakable profanity appears inside a longer string."""
    masked = _mask_safe_substrings(text.lower())
    return any(blocked in masked for blocked in _CLEAR_EMBEDDED)


def _is_keyboard_mash(token: str) -> bool:
    """
    True for long random letter spam (no real words).

    Catches key-mashing like ijudhsjsdkjhsdfkjfuckskdjsjsj and plain garbage
    such as sdkjfhskdjfhsjkdfhsjkdf.
    """
    low = token.lower()
    if low in _SAFE_TOKENS or len(low) < _KEYBOARD_MASH_MIN_LEN:
        return False

    if _contains_embedded_clear_profanity(low):
        return True

    vowels = sum(1 for ch in low if ch in _VOWELS)
    vowel_ratio = vowels / len(low)
    if vowel_ratio < 0.18:
        return True

    # Keyboard-row mashing (asdfghjklqwertyuiop...) — few vowels, very long.
    if len(low) >= 26 and vowel_ratio < 0.22:
        return True

    return False


def _mask_safe_substrings(packed: str) -> str:
    """Hide known-good tokens inside packed text before embedded scans."""
    masked = packed
    safe_forms = set(_SAFE_TOKENS)
    for safe in _SAFE_TOKENS:
        collapsed = _collapse_repeats_aggressive(safe)
        if collapsed:
            safe_forms.add(collapsed)
    for safe in sorted(safe_forms, key=len, reverse=True):
        if safe in masked:
            masked = masked.replace(safe, " " * len(safe))
    return masked


def _variant_is_blocked(variant: str) -> bool:
    if not variant or variant in _SAFE_TOKENS:
        return False
    if variant in _BLOCKLIST:
        return True
    masked = _mask_safe_substrings(variant)
    for blocked in sorted(_CLEAR_EMBEDDED, key=len, reverse=True):
        if blocked in masked:
            return True
    return False


def _packed_phrase_blocked(packed_variants: list[str]) -> bool:
    for phrase in _PHRASES:
        phrase_variants = _normalize_packed(phrase)
        for packed in packed_variants:
            masked = _mask_safe_substrings(packed)
            for phrase_norm in phrase_variants:
                if phrase_norm in masked:
                    return True
    return False


def _whole_text_is_safe_token(text: str) -> bool:
    tokens = _tokenize(text)
    if len(tokens) != 1:
        return False
    return tokens[0].lower() in _SAFE_TOKENS


def _token_blocked(raw_token: str) -> bool:
    low = raw_token.lower()

    if low in _SAFE_TOKENS:
        return False

    if low in _BLOCKLIST:
        return True

    if _is_keyboard_mash(low):
        return True

    if _contains_embedded_clear_profanity(low):
        return True

    hiding = _has_letter_spam(low) or _has_leet_or_symbols(low) or len(low) >= 10

    if hiding:
        phonetic = _needs_phonetic_check(raw_token) or len(low) >= 10
        for variant in _normalize_variants(raw_token, phonetic=phonetic):
            if _variant_is_blocked(variant):
                return True
        return False

    return False


def contains_profanity(text: str) -> bool:
    blocked, _ = check_text(text)
    return blocked


def check_text(text: str) -> tuple[bool, str | None]:
    if not text or not text.strip():
        return False, None

    if _whole_text_is_safe_token(text):
        return False, None

    tokens = _tokenize(text)
    packed_variants = _normalize_packed(text)

    if packed_variants:
        if _packed_phrase_blocked(packed_variants):
            return True, _FRIENDLY_MESSAGE
        for packed in packed_variants:
            if _variant_is_blocked(packed):
                return True, _FRIENDLY_MESSAGE

    for raw_token in tokens:
        if _token_blocked(raw_token):
            return True, _FRIENDLY_MESSAGE

    return False, None


def is_acceptable_name(text: str) -> bool:
    return not contains_profanity(text)


_TAG_FILTER_MESSAGE = "Nice try — custom tags go through the friendly filter too! :D"


def tag_filter_message() -> str:
    """Playful rejection when kids try to sneak past the tag filter."""
    return _TAG_FILTER_MESSAGE


def validate_tag(text: str) -> tuple[bool, str | None]:
    """
    Validate one custom tag. Returns (is_ok, error_message).
    Kids love trying to sneak past filters — this catches them too. :)
    """
    tag = text.strip()
    if not tag:
        return False, "Type a tag first!"
    if len(tag) > 20:
        return False, "Tags must be 20 characters or less."
    if contains_profanity(tag):
        return False, _TAG_FILTER_MESSAGE
    return True, None