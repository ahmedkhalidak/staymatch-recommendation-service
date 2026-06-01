import math


def geo_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


GOVERNORATE_CENTERS = {
    "cairo": (30.0444, 31.2357),
    "alexandria": (31.2001, 29.9187),
    "giza": (30.0131, 31.2089),
    "sharqia": (30.7125, 31.7180),
    "dakahlia": (31.0448, 31.3784),
    "beheira": (31.0969, 30.3819),
    "qalyubia": (30.4725, 31.3784),
    "monufia": (30.5975, 31.3182),
    "gharbia": (30.8754, 31.0344),
    "kafr el-sheikh": (31.1111, 31.1233),
    "damietta": (31.4175, 31.8153),
    "port said": (31.2653, 32.3019),
    "ismailia": (30.6043, 32.2723),
    "suez": (29.9668, 32.5498),
    "north sinai": (30.9984, 33.5900),
    "south sinai": (28.5605, 33.9436),
    "red sea": (26.8206, 33.4766),
    "minya": (28.0887, 30.7611),
    "asyut": (27.1813, 31.1837),
    "sohag": (26.5570, 31.6948),
    "qena": (26.1648, 32.7261),
    "luxor": (25.6872, 32.6396),
    "aswan": (24.0889, 32.8998),
    "fayoum": (29.3084, 30.8428),
    "beni suef": (29.0724, 31.0979),
    "new valley": (24.5454, 30.1770),
    "matrouh": (31.1417, 27.1534),
}


def governorate_center(name: str):
    key = name.lower().strip()
    return GOVERNORATE_CENTERS.get(key)