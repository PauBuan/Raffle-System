"""
config/settings.py
------------------
Application-wide constants and UI theme settings.
"""

APP_NAME    = "Raffle System"
APP_VERSION = "2.0.0"

# ── Prize category labels (must match DB seed) ────────────────────
CATEGORY_MINOR = "Minor"
CATEGORY_MAJOR = "Major"
CATEGORY_GRAND = "Grand"

# ── Animation timing constants ────────────────────────────────────
SLOT_CHAR_INTERVAL_MS  = 3000   # Grand: ms per character reveal
MINOR_ROW_INTERVAL_MS  = 280    # Minor: ms between row reveals
MAJOR_CARD_INTERVAL_MS = 700    # Major: ms between card reveals

# ── Grand prize building defaults ─────────────────────────────────
DEFAULT_LTI_WINNERS = 1
DEFAULT_CIP_WINNERS = 2

# Recent winners section cap
RECENT_WINNERS_LIMIT = 30

# ── Colour palette (used by Qt stylesheets) ───────────────────────
COLORS = {
    "bg_dark":      "#0D0D1A",
    "bg_card":      "#16162A",
    "bg_card2":     "#1E1E3A",
    "accent_gold":  "#FFD700",
    "accent_blue":  "#4FC3F7",
    "accent_red":   "#FF5252",
    "accent_green": "#69F0AE",
    "text_primary": "#FFFFFF",
    "text_muted":   "#9E9E9E",
    "border":       "#2A2A4A",
}
