"""
Species Classifier Mapping

This module defines the 25 bird species that the classifier model can identify.
These are Gulf Coast colonial waterbirds trained from expert-annotated data.

The classifier uses 4-letter AOU (American Ornithological Union) species codes.
"""

# Species classifier outputs 25 species (alphabetically ordered by code)
CLASSIFIER_SPECIES = {
    0:  'AMOY',  # American Oystercatcher
    1:  'AWPE',  # American White Pelican
    2:  'BCNH',  # Black-crowned Night Heron
    3:  'BLSK',  # Black Skimmer
    4:  'BRPE',  # Brown Pelican
    5:  'CAEG',  # Cattle Egret
    6:  'CATE',  # Caspian Tern
    7:  'DCCO',  # Double-crested Cormorant
    8:  'FOTE',  # Forster's Tern
    9:  'GBHE',  # Great Blue Heron
    10: 'GBTE',  # Gull-billed Tern
    11: 'GREG',  # Great Egret
    12: 'GRFL',  # Greater Flamingo
    13: 'LAGU',  # Laughing Gull
    14: 'LETE',  # Least Tern
    15: 'NECO',  # Neotropic Cormorant
    16: 'REEG',  # Reddish Egret
    17: 'ROSP',  # Roseate Spoonbill
    18: 'ROYT',  # Royal Tern
    19: 'SATE',  # Sandwich Tern
    20: 'SNEG',  # Snowy Egret
    21: 'SOTE',  # Sooty Tern
    22: 'TRHE',  # Tricolored Heron
    23: 'WFIB',  # White-faced Ibis
    24: 'WHIB',  # White Ibis
}

# Full species names (will be loaded from database when available)
SPECIES_COMMON_NAMES = {
    'AMOY': 'American Oystercatcher',
    'AWPE': 'American White Pelican',
    'BCNH': 'Black-crowned Night Heron',
    'BLSK': 'Black Skimmer',
    'BRPE': 'Brown Pelican',
    'CAEG': 'Cattle Egret',
    'CATE': 'Caspian Tern',
    'DCCO': 'Double-crested Cormorant',
    'FOTE': "Forster's Tern",
    'GBHE': 'Great Blue Heron',
    'GBTE': 'Gull-billed Tern',
    'GREG': 'Great Egret',
    'GRFL': 'Greater Flamingo',
    'LAGU': 'Laughing Gull',
    'LETE': 'Least Tern',
    'NECO': 'Neotropic Cormorant',
    'REEG': 'Reddish Egret',
    'ROSP': 'Roseate Spoonbill',
    'ROYT': 'Royal Tern',
    'SATE': 'Sandwich Tern',
    'SNEG': 'Snowy Egret',
    'SOTE': 'Sooty Tern',
    'TRHE': 'Tricolored Heron',
    'WFIB': 'White-faced Ibis',
    'WHIB': 'White Ibis',
}

# Functional groups for visualization color-coding
# Groups species by similar appearance/ecology for easier field identification
SPECIES_TO_GROUP = {
    # Pelicans
    'BRPE': 'PELICAN',
    'AWPE': 'PELICAN',

    # Cormorants
    'DCCO': 'CORMORANT',
    'NECO': 'CORMORANT',

    # Large herons
    'GBHE': 'LARGE_HERON',
    'GREG': 'LARGE_HERON',
    'BCNH': 'LARGE_HERON',

    # White waders (egrets & white ibis)
    'SNEG': 'WHITE_WADER',
    'CAEG': 'WHITE_WADER',
    'WHIB': 'WHITE_WADER',

    # Colorful waders
    'REEG': 'COLOR_WADER',
    'TRHE': 'COLOR_WADER',
    'ROSP': 'COLOR_WADER',
    'WFIB': 'COLOR_WADER',

    # Gulls & Skimmers
    'LAGU': 'GULL',
    'BLSK': 'GULL',

    # Terns
    'ROYT': 'TERN',
    'CATE': 'TERN',
    'SATE': 'TERN',
    'FOTE': 'TERN',
    'GBTE': 'TERN',
    'LETE': 'TERN',
    'SOTE': 'TERN',

    # Shorebirds
    'AMOY': 'SHOREBIRD',

    # Rare species
    'GRFL': 'RARE',
}

# Per-group annotation colors in BGR format for OpenCV
GROUP_COLORS = {
    'PELICAN':     (87, 119, 217),   # Claude orange #D97757
    'CORMORANT':   (60, 60, 60),     # Dark gray/black
    'LARGE_HERON': (180, 180, 120),  # Blue-gray
    'GULL':        (42, 200, 100),   # Green
    'TERN':        (42, 180, 220),   # Cyan/teal
    'WHITE_WADER': (220, 220, 220),  # Light gray/white
    'COLOR_WADER': (200, 60, 220),   # Purple/pink
    'SHOREBIRD':   (30, 160, 255),   # Orange
    'RARE':        (0, 215, 255),    # Gold
    'UNKNOWN':     (87, 119, 217),   # Claude orange (fallback)
}


def get_species_code(class_id: int) -> str:
    """
    Get species code from classifier output class ID

    Args:
        class_id: Classifier output (0-24)

    Returns:
        str: 4-letter species code (e.g., 'BRPE')
    """
    return CLASSIFIER_SPECIES.get(class_id, 'UNKNOWN')


def get_species_name(species_code: str) -> str:
    """
    Get common name from species code

    Args:
        species_code: 4-letter code (e.g., 'BRPE')

    Returns:
        str: Common name (e.g., 'Brown Pelican')
    """
    return SPECIES_COMMON_NAMES.get(species_code, species_code)


def get_species_group(species_code: str) -> str:
    """
    Get functional group for a species (for color-coding)

    Args:
        species_code: 4-letter code (e.g., 'BRPE')

    Returns:
        str: Group name (e.g., 'PELICAN')
    """
    return SPECIES_TO_GROUP.get(species_code, 'UNKNOWN')


def get_group_color(group: str) -> tuple:
    """
    Get BGR color for a functional group

    Args:
        group: Group name (e.g., 'PELICAN')

    Returns:
        tuple: BGR color (e.g., (87, 119, 217))
    """
    return GROUP_COLORS.get(group, GROUP_COLORS['UNKNOWN'])
