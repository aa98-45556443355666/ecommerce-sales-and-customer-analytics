from pathlib import Path

from src.ingestion.load_data import calculate_sha256


def test_same_content_produces_same_hash(tmp_path: Path) -> None:
    file_a = tmp_path / "a.csv"
    file_b = tmp_path / "b.csv"

    content = b"id,name\n1,Aarush\n"

    file_a.write_bytes(content)
    file_b.write_bytes(content)

    assert calculate_sha256(file_a) == calculate_sha256(file_b)


def test_changed_content_produces_different_hash(tmp_path: Path) -> None:
    file_path = tmp_path / "data.csv"

    file_path.write_text(
        "id,name\n1,Aarush\n",
        encoding="utf-8",
    )

    original_hash = calculate_sha256(file_path)

    file_path.write_text(
        "id,name\n1,Aarush Updated\n",
        encoding="utf-8",
    )

    updated_hash = calculate_sha256(file_path)

    assert original_hash != updated_hash
