import json
import shutil
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "datasets" / "aihub" / "traffic-accident-video" / "aihubshell" / "095.교통사고_영상_데이터"
LABELS_ROOT = REPO_ROOT / "datasets" / "aihub" / "traffic-accident-video" / "labels" / "video"


def split_for_path(path: Path) -> str:
    text = str(path)
    if "1.Training" in text or "training" in path.parts:
        return "training"
    if "2.Validation" in text or "validation" in path.parts:
        return "validation"
    raise ValueError(f"Cannot infer AI-Hub split for {path}")


def ensure_dirs() -> None:
    for split in ("training", "validation"):
        for kind in ("zips", "json"):
            (LABELS_ROOT / split / kind).mkdir(parents=True, exist_ok=True)


def move_official_downloads() -> None:
    if not SOURCE_ROOT.exists():
        return
    for path in sorted(SOURCE_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in {".zip", ".json"}:
            continue
        split = split_for_path(path)
        kind = "zips" if path.suffix == ".zip" else "json"
        target = LABELS_ROOT / split / kind / path.name
        if target.exists():
            target.unlink()
        shutil.move(str(path), str(target))
    remaining_files = [path for path in SOURCE_ROOT.rglob("*") if path.is_file()]
    if not remaining_files:
        shutil.rmtree(SOURCE_ROOT)


def build_zip_lookup() -> dict[str, dict[str, str]]:
    lookup = {}
    for zip_path in sorted((LABELS_ROOT / "training" / "zips").glob("*.zip")) + sorted((LABELS_ROOT / "validation" / "zips").glob("*.zip")):
        split = split_for_path(zip_path)
        try:
            with zipfile.ZipFile(zip_path) as archive:
                for name in archive.namelist():
                    if name.endswith(".json"):
                        lookup[Path(name).name] = {
                            "source_zip": zip_path.name,
                            "split": split,
                        }
        except zipfile.BadZipFile:
            continue
    return lookup


def write_index() -> int:
    zip_lookup = build_zip_lookup()
    entries = []
    for split in ("training", "validation"):
        for kind in ("zips", "json"):
            for path in sorted((LABELS_ROOT / split / kind).glob("*")):
                if not path.is_file():
                    continue
                entry = {
                    "file_name": path.name,
                    "split": split,
                    "kind": "zip" if kind == "zips" else "json",
                    "relative_path": path.relative_to(REPO_ROOT).as_posix(),
                }
                if kind == "json":
                    entry.update(zip_lookup.get(path.name, {}))
                entries.append(entry)
    (LABELS_ROOT / "index.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(entries)


def main() -> None:
    ensure_dirs()
    move_official_downloads()
    count = write_index()
    print(f"organized AI-Hub 597 video labels into {LABELS_ROOT}")
    print(f"indexed {count} files")


if __name__ == "__main__":
    main()
