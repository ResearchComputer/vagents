from pathlib import Path

from vagents.manager.package import GitRepository


def test_parse_repo_url_with_subdir_variants():
    # SSH with .git and subdir
    repo, sub = GitRepository.parse_repo_url_with_subdir(
        "git@github.com:user/repo.git/packages/mod"
    )
    assert repo.endswith("repo.git")
    assert sub == "packages/mod"

    # HTTPS with .git and subdir
    repo, sub = GitRepository.parse_repo_url_with_subdir(
        "https://github.com/user/repo.git/pkg"
    )
    assert repo.endswith("repo.git") and sub == "pkg"

    # SSH without .git
    repo, sub = GitRepository.parse_repo_url_with_subdir(
        "git@github.com:user/repo/path/to/pkg"
    )
    assert repo.endswith("repo.git") and sub == "path/to/pkg"

    # HTTPS without .git
    repo, sub = GitRepository.parse_repo_url_with_subdir(
        "https://github.com/user/repo/path/to/pkg"
    )
    assert repo.endswith("repo.git") and sub == "path/to/pkg"

    # Plain repo URL
    repo, sub = GitRepository.parse_repo_url_with_subdir("https://example.com/a.git")
    assert repo.endswith("a.git") and sub is None


def test_extract_subdirectory_missing(tmp_path: Path):
    # When subdir not present, returns False
    repo = tmp_path / "repo"
    repo.mkdir()
    ok = GitRepository.extract_subdirectory(repo, "nonexistent", tmp_path / "out")
    assert ok is False
