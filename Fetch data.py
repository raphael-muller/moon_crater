import requests
from pathlib import Path

# ================================
# CONFIG
# ================================

BASE_URL = "https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/DATA/MDR/WAC_EMP/"

OUTPUT_DIR = Path("data\moon_tiles")
OUTPUT_DIR.mkdir(exist_ok=True)

# 7 bandes spectrales
BANDS = [
    "321NM",
    "360NM",
    "415NM",
    "566NM",
    "604NM",
    "643NM",
    "689NM"
]

# tuiles géographiques
TILES = [
"E300N0450_064P",
"E300S0450_064P",
"E300N1350_064P",
"E300S1350_064P",
"E300N2250_064P",
"E300S2250_064P",
"E300N3150_064P",
"E300S3150_064P"
]

# ================================
# DOWNLOAD FUNCTION
# ================================

def download_file(url, path):

    if path.exists():
        print("Already downloaded:", path.name)
        return

    print("Downloading:", path.name)

    r = requests.get(url, stream=True)

    if r.status_code != 200:
        print("File not found:", url)
        return

    with open(path, "wb") as f:
        for chunk in r.iter_content(1024*1024):
            f.write(chunk)


# ================================
# DOWNLOAD IMG BANDS
# ================================

print("\nDownloading spectral bands (.IMG)\n")

for band in BANDS:
    for tile in TILES:

        filename = f"WAC_EMP_{band}_{tile}.IMG"
        url = BASE_URL + filename

        download_file(url, OUTPUT_DIR / filename)


# ================================
# DOWNLOAD RGB 3BAND TIF
# ================================

print("\nDownloading RGB mosaics (.TIF)\n")

for tile in TILES:

    filename = f"WAC_EMP_3BAND_{tile}.TIF"
    url = BASE_URL + filename

    download_file(url, OUTPUT_DIR / filename)


print("\nDownload finished")