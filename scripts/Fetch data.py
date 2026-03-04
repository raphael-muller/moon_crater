import requests
from pathlib import Path

# ================================
# CONFIG
# ================================
BASE_URL = "https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/DATA/MDR/WAC_EMP/"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "moon_tiles"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 7 bandes spectrales
BANDS = ["321NM", "360NM", "415NM", "566NM", "604NM", "643NM", "689NM"]

# 8 tuiles equirectangulaires (064P pour 7-band + 3BAND)
E_TILES_064 = [
    "E300N0450_064P",
    "E300S0450_064P",
    "E300N1350_064P",
    "E300S1350_064P",
    "E300N2250_064P",
    "E300S2250_064P",
    "E300N3150_064P",
    "E300S3150_064P",
]

# 643NM existe aussi en 304P (equirectangulaire) + pôles (stéréo polaire)
E_TILES_304_643 = [
    "E300N0450_304P",
    "E300S0450_304P",
    "E300N1350_304P",
    "E300S1350_304P",
    "E300N2250_304P",
    "E300S2250_304P",
    "E300N3150_304P",
    "E300S3150_304P",
]
P_TILES_304_643 = ["P900N0000_304P", "P900S0000_304P"]

# Si tu veux aussi télécharger la 3BAND (RGB) en 064P
DOWNLOAD_3BAND_064 = True

# Timeout réseau
TIMEOUT_S = 60

# ================================
# DOWNLOAD FUNCTION
# ================================

def download_file(filename: str) -> bool:
    """
    Télécharge BASE_URL/filename vers OUTPUT_DIR/filename.
    Ne retélécharge pas si le fichier existe déjà (taille > 0).
    Télécharge en .part puis renomme à la fin (anti-fichier corrompu).
    """
    out_path = OUTPUT_DIR / filename

    if out_path.exists() and out_path.stat().st_size > 0:
        print("Already downloaded:", filename)
        return True

    url = BASE_URL + filename
    print("Downloading:", filename)

    try:
        r = requests.get(url, stream=True, timeout=TIMEOUT_S)
    except Exception as e:
        print("Request failed:", filename, "|", repr(e))
        return False

    if r.status_code != 200:
        print("File not found:", filename, "| HTTP", r.status_code)
        return False

    tmp_path = out_path.with_suffix(out_path.suffix + ".part")
    try:
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
        tmp_path.replace(out_path)
        return True
    finally:
        # Si quelque chose s'est mal passé, on évite de laisser un .part énorme
        if tmp_path.exists() and (not out_path.exists()):
            try:
                tmp_path.unlink()
            except Exception:
                pass


def main():
    print("=== Download WAC_EMP (all bands + IMG + TIF, skip if exists) ===")
    print("Base URL :", BASE_URL)
    print("Output   :", OUTPUT_DIR)
    print("")

    files = []

    # 1) 7 bandes en 064P (IMG)
    for band in BANDS:
        for tile in E_TILES_064:
            files.append(f"WAC_EMP_{band}_{tile}.IMG")

    # 2) 3BAND en 064P (TIF)
    if DOWNLOAD_3BAND_064:
        for tile in E_TILES_064:
            files.append(f"WAC_EMP_3BAND_{tile}.TIF")

    # 3) 643NM en 304P (IMG) + pôles (IMG)
    for tile in E_TILES_304_643:
        files.append(f"WAC_EMP_643NM_{tile}.IMG")
    for tile in P_TILES_304_643:
        files.append(f"WAC_EMP_643NM_{tile}.IMG")

    # Téléchargement
    ok = 0
    for i, fn in enumerate(files, start=1):
        print(f"[{i}/{len(files)}] ", end="")
        ok += int(download_file(fn))

    print("")
    print(f"Done: {ok}/{len(files)} files present.")


if __name__ == "__main__":
    main()