"""Windows Office owner files must not break code-image capture."""

from __future__ import annotations

from mlpstorage_py.submission_checker.tools.code_checksum import compute_code_tree_md5


class _Logger:
    def warning(self, *_args) -> None:
        pass


def test_office_owner_lock_file_is_excluded(tmp_path) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "benchmark.py").write_bytes(b"MODEL = 'unet3d'\n")
    digest_without_lock = compute_code_tree_md5(str(tree), _Logger())

    docs = tree / "docs"
    docs.mkdir()
    (docs / "~$FULL_TEST_PLAN.xlsx").write_bytes(b"transient office lock")
    digest_with_lock = compute_code_tree_md5(str(tree), _Logger())

    assert digest_with_lock == digest_without_lock
