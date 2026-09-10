"""Two deliberately disjoint word banks.

QUERY_TERMS is the language people type when describing who they want: "warm",
"credible", "authoritative". The catalog is written from every other bank here,
and shares none of those words.

That is the whole test of this product. If a roster described its people as
"warm and credible", ranking a query for a warm, credible actor would be a
string match dressed up as understanding. Because the banks are disjoint,
matching "someone warm who explains things without talking down" to "unhurried,
with the vowels of somebody's older cousin, explains without condescending"
requires actual semantic work, and a lexical scorer visibly cannot do it.

`test_catalog.py` fails the build if the banks ever overlap.
"""

from __future__ import annotations

# ------------------------------------------------------------- query side

QUERY_TERMS = (
    "warm", "credible", "authoritative", "playful", "aspirational",
    "reassuring", "energetic", "understated", "premium", "approachable",
    "urgent", "irreverent", "trustworthy", "friendly", "serious", "confident",
)

# ----------------------------------------------------------- catalog side

APPEARANCE_HAIR = (
    "close-cropped hair", "hair pulled back and pinned", "a loose shoulder-length cut",
    "shaved at the sides, longer on top", "greying at the temples",
    "a centre parting that never quite holds", "curls cut short",
    "a plait over one shoulder", "thinning on top and unbothered by it",
)

APPEARANCE_FACE = (
    "heavy brows over deep-set eyes", "a round face that photographs younger than it is",
    "a jaw you notice in profile", "wire-frame glasses pushed up constantly",
    "a cropped beard kept neat", "laugh lines that arrive before the laugh",
    "high cheekbones and a narrow chin", "a broad nose and a wide mouth",
    "a scar through one eyebrow", "freckles across the bridge of the nose",
)

APPEARANCE_BUILD = (
    "tall and slightly stooped", "compact and square-shouldered",
    "long-limbed, all elbows on camera", "solid through the chest",
    "slight, and uses the whole frame anyway", "carries themselves like a swimmer",
    "settles into a chair the moment they can", "stands very straight, always",
)

DELIVERY_PACE = ("unhurried", "brisk", "measured", "quick-footed", "deliberate")

DELIVERY_TEXTURE = (
    "dry around the edges", "with a slight rasp", "clean and unadorned",
    "with a smile audible under it", "flat in a way that reads as honest",
    "with the vowels of somebody's older cousin", "clipped, almost impatient",
    "soft-edged", "declarative", "conversational to the point of rambling",
)

DELIVERY_STANCE = (
    "big-brotherly", "explains without condescending", "sells nothing, states things",
    "sounds like they have used the product", "reads copy like conversation",
    "leans into the camera", "holds a beat before the point",
    "treats the viewer as a peer", "coaxes rather than pitches",
    "talks you through it the way a colleague would",
)

VOICE_TAGS = (
    "low-register", "mid-register", "bright", "gravelly", "breathy",
    "even-toned", "nasal-forward", "resonant", "airy", "clipped",
)

WARDROBE = {
    "studio": ("plain crew neck", "open collar shirt", "single-tone kurta", "light blazer"),
    "home": ("worn cotton tee", "house kurta", "hoodie", "checked shirt, untucked"),
    "office": ("pressed shirt", "blazer over tee", "sari, office-formal", "knit polo"),
    "outdoor": ("windbreaker", "linen shirt", "denim jacket", "field shirt"),
    "classroom": ("cardigan", "cotton sari", "collared shirt with pens", "sweater vest"),
    "beach": ("open shirt over tee", "kaftan", "swim shorts and linen", "sun-faded tee"),
    "street": ("bomber jacket", "printed shirt", "cargo and tank", "layered scarf"),
    "cafe": ("oversized sweater", "denim shirt", "wrap top", "corduroy jacket"),
    "gym": ("training vest", "zip-up over shorts", "sleeveless and taped wrists", "track set"),
}

SCENE = {
    "studio": (
        "seamless grey, one hard key and a bounce",
        "black cyc, rim light picking out the shoulder",
        "white infinity, flat and even",
    ),
    "home": (
        "kitchen counter, afternoon light through a grille window",
        "sofa corner, table lamp on, television off",
        "balcony doorway with plants crowding the frame",
    ),
    "office": (
        "glass meeting room, blinds half-drawn",
        "desk edge, two monitors dark behind",
        "corridor lean, badge still clipped on",
    ),
    "outdoor": (
        "terrace at the end of the day, city haze behind",
        "park path, mid-morning, walkers passing out of focus",
        "rooftop, wind moving the collar",
    ),
    "classroom": (
        "whiteboard half-wiped, marker still in hand",
        "front of a lecture room, empty chairs behind",
        "lab bench, equipment out of focus",
    ),
    "beach": (
        "wet sand at low tide, overcast",
        "shoreline at golden hour, squinting slightly",
        "beach shack table, drink sweating on the wood",
    ),
    "street": (
        "market lane, foot traffic behind",
        "against a shuttered storefront at night",
        "auto-rickshaw stand, horns audible",
    ),
    "cafe": (
        "corner table, cup between both hands",
        "counter stool, espresso machine loud behind",
        "window seat, street reflected in the glass",
    ),
    "gym": (
        "mirrored wall, chalk on the hands",
        "mat floor mid-session, others working behind",
        "rack of dumbbells, towel over one shoulder",
    ),
}

FRAMING = (
    "handheld", "tripod-locked", "natural-light", "practical-lit", "shallow-depth",
    "wide-frame", "waist-up", "seated", "walking", "direct-address",
)

PRESENTS_AS = ("woman", "man", "non-binary")

FIRST_NAMES = (
    "Priya", "Arjun", "Meera", "Rohan", "Kavya", "Ishaan", "Ananya", "Vikram",
    "Nisha", "Aditya", "Sneha", "Karan", "Divya", "Farhan", "Riya", "Tanvi",
    "Rahul", "Zoya", "Aakash", "Leela", "Manav", "Ira", "Devika", "Siddharth",
    "Naveen", "Payal", "Imran", "Shruti", "Gautam", "Anjali",
)

LAST_INITIALS = tuple("ABCDGHJKMNPRSTV")

AGE_BANDS = ("18-24", "25-34", "35-44", "45-54", "55+")
