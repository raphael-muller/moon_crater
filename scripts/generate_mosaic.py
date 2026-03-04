# scripts/generate_mosaic.py
from pathlib import Path
import subprocess
import rasterio

# =========================
# CONFIG
# =========================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "data" / "moon_tiles"
OUTPUT_DIR = PROJECT_ROOT / "output" / "mosaics"
TMP_DIR = OUTPUT_DIR / "_tmp"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

E_TILES_064 = [
    "E300N0450_064P", "E300S0450_064P",
    "E300N1350_064P", "E300S1350_064P",
    "E300N2250_064P", "E300S2250_064P",
    "E300N3150_064P", "E300S3150_064P",
]

E_TILES_304 = [
    "E300N0450_304P", "E300S0450_304P",
    "E300N1350_304P", "E300S1350_304P",
    "E300N2250_304P", "E300S2250_304P",
    "E300N3150_304P", "E300S3150_304P",
]
P_TILES_304 = ["P900N0000_304P", "P900S0000_304P"]

BANDS_064 = ["321NM", "360NM", "415NM", "566NM", "604NM", "689NM"]  # 643 traité à part

TR_304 = 1.0 / 304.0
TE_GLOBAL = (0.0, -90.0, 360.0, 90.0)

# Nodata values
NODATA_FLOAT = "-9999"   # OK for float products
NODATA_BYTE = "0"        # OK for 8-bit RGB

# =========================


def run(cmd):
    print("[CMD]", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)


def ensure_exists(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing tile: {path}")


def get_ref_srs_wkt(ref_raster: Path, out_wkt_file: Path):
    with rasterio.open(ref_raster) as ref:
        if ref.crs is None:
            raise ValueError(f"Reference raster has no CRS: {ref_raster}")
        out_wkt_file.write_text(ref.crs.to_wkt(), encoding="utf-8")


def mosaic_tiles_to_tif(inputs, out_tif: Path, tmp_vrt: Path, nodata: str, predictor: int):
    """
    Build VRT then translate to GeoTIFF (tiled+compressed) with predictor adapted to dtype.
    predictor:
      - 2 for integer data (UInt8/UInt16)
      - 3 for float data (Float32/Float64)
    """
    if tmp_vrt.exists():
        tmp_vrt.unlink()
    if out_tif.exists():
        out_tif.unlink()

    # VRT
    run(["gdalbuildvrt", "-srcnodata", nodata, "-vrtnodata", nodata, str(tmp_vrt), *[str(p) for p in inputs]])

    # Translate
    # For DEFLATE compression:
    #  - Predictor=2 for integer
    #  - Predictor=3 for float
    run([
        "gdal_translate",
        str(tmp_vrt), str(out_tif),
        "-a_nodata", nodata,
        "-co", "TILED=YES",
        "-co", "COMPRESS=DEFLATE",
        "-co", f"PREDICTOR={predictor}",
        "-co", "BIGTIFF=YES",
    ])


def build_mosaic_3band_064():
    print("\n=== 1) Mosaic 3BAND @ 64P ===")
    inputs = []
    for tile in E_TILES_064:
        p = INPUT_DIR / f"WAC_EMP_3BAND_{tile}.TIF"
        ensure_exists(p)
        inputs.append(p)

    out_tif = OUTPUT_DIR / "WAC_EMP_3BAND_E_GLOBAL_064P.tif"
    tmp_vrt = TMP_DIR / "mosaic_3band_064.vrt"

    # 3BAND is typically UInt8 -> predictor 2, nodata 0
    mosaic_tiles_to_tif(inputs, out_tif, tmp_vrt, nodata=NODATA_BYTE, predictor=2)
    print("[DONE]", out_tif)


def build_mosaic_band_064(band: str):
    print(f"\n=== 3) Mosaic {band} @ 64P ===")
    inputs = []
    for tile in E_TILES_064:
        p = INPUT_DIR / f"WAC_EMP_{band}_{tile}.IMG"
        ensure_exists(p)
        inputs.append(p)

    out_tif = OUTPUT_DIR / f"WAC_EMP_{band}_E_GLOBAL_064P.tif"
    tmp_vrt = TMP_DIR / f"mosaic_{band}_064.vrt"

    # IMG bands are typically float -> predictor 3, nodata -9999
    mosaic_tiles_to_tif(inputs, out_tif, tmp_vrt, nodata=NODATA_FLOAT, predictor=3)
    print("[DONE]", out_tif)


def build_mosaic_643_304_with_poles():
    print("\n=== 2) Mosaic 643NM @ 304P with poles (P reprojected -> E) ===")

    ref_path = INPUT_DIR / f"WAC_EMP_643NM_{E_TILES_304[0]}.IMG"
    ensure_exists(ref_path)

    srs_file = TMP_DIR / "ref_srs_643_304.wkt"
    get_ref_srs_wkt(ref_path, srs_file)

    e_paths = []
    for t in E_TILES_304:
        p = INPUT_DIR / f"WAC_EMP_643NM_{t}.IMG"
        ensure_exists(p)
        e_paths.append(p)

    warped_p_paths = []
    for t in P_TILES_304:
        src = INPUT_DIR / f"WAC_EMP_643NM_{t}.IMG"
        ensure_exists(src)

        out = TMP_DIR / f"{src.stem}_toE_304P.tif"
        warped_p_paths.append(out)

        run([
            "gdalwarp",
            "-t_srs", str(srs_file),
            "-tr", str(TR_304), str(TR_304),
            "-te", str(TE_GLOBAL[0]), str(TE_GLOBAL[1]), str(TE_GLOBAL[2]), str(TE_GLOBAL[3]),
            "-r", "near",
            "-srcnodata", NODATA_FLOAT,
            "-dstnodata", NODATA_FLOAT,
            "-overwrite",
            str(src), str(out)
        ])

    out_tif = OUTPUT_DIR / "WAC_EMP_643NM_E_GLOBAL_WITH_POLES_304P.tif"
    tmp_vrt = TMP_DIR / "mosaic_643_304_with_poles.vrt"

    mosaic_tiles_to_tif(e_paths + warped_p_paths, out_tif, tmp_vrt, nodata=NODATA_FLOAT, predictor=3)
    print("[DONE]", out_tif)


def main():
    print("=== Generate WAC_EMP mosaics (GDAL, disk-based) ===")
    print("Input :", INPUT_DIR)
    print("Output:", OUTPUT_DIR)
    print("Tmp   :", TMP_DIR)

    # 1) 3BAND 64P
    build_mosaic_3band_064()

    # 2) 643 304P with poles
    build_mosaic_643_304_with_poles()

    # 3) Other wavelength mosaics at 64P
    for band in BANDS_064:
        build_mosaic_band_064(band)

    print("\nALL DONE ✅")


if __name__ == "__main__":
    main()