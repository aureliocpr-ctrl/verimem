"""The published numbers come from the registry, not from a hand (G4, T218).

`benchmark/repro_all.py` maps every headline number to the artifact that backs it. These tests
pin the other half: the TEXT a reader sees between two markers,

    <!-- g4:<id> -->0.971<!-- /g4 -->

is exactly what the registry renders from the artifact. A number edited by hand, an artifact
that moved on, a marker the registry does not know, or a registered marker that is gone —
each one is a failure, not a warning.
"""
import json

from benchmark.repro_all import REGISTRY, check_docs


def _repo(tmp_path, readme: str, value=0.971):
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "demo.json").write_text(json.dumps({"a": {"b": value}}), encoding="utf-8")
    (tmp_path / "README.md").write_bytes(readme.encode("utf-8"))
    registry = {"demo-claim": {
        "claim": "demo", "artifact": "demo.json", "value_at": ["a", "b"],
        "command": "python -m benchmark.demo", "cost": "local",
        "docs": [{"file": "README.md", "id": "demo", "text": "{v:.3f}", "fields": {"v": ["a", "b"]}}],
    }}
    return registry, tmp_path / "results", tmp_path


def test_a_number_edited_by_hand_is_a_failure(tmp_path):
    registry, results, root = _repo(tmp_path, "AUROC <!-- g4:demo -->0.970<!-- /g4 --> on SNLI\n")
    problems = check_docs(registry=registry, results_dir=results, root=root)
    assert len(problems) == 1 and "demo" in problems[0] and "0.970" in problems[0], problems


def test_render_writes_the_registry_value_and_then_the_check_passes(tmp_path):
    registry, results, root = _repo(tmp_path, "AUROC <!-- g4:demo -->0.970<!-- /g4 --> on SNLI\n")
    check_docs(registry=registry, results_dir=results, root=root, write=True)
    assert (root / "README.md").read_text(encoding="utf-8") == \
        "AUROC <!-- g4:demo -->0.971<!-- /g4 --> on SNLI\n"
    assert check_docs(registry=registry, results_dir=results, root=root) == []


def test_render_keeps_the_line_endings_of_the_file(tmp_path):
    registry, results, root = _repo(tmp_path, "one\r\nAUROC <!-- g4:demo -->0.9<!-- /g4 -->\r\ntwo\r\n")
    check_docs(registry=registry, results_dir=results, root=root, write=True)
    assert (root / "README.md").read_bytes() == \
        b"one\r\nAUROC <!-- g4:demo -->0.971<!-- /g4 -->\r\ntwo\r\n"


def test_a_marker_the_registry_does_not_know_is_a_failure(tmp_path):
    registry, results, root = _repo(
        tmp_path, "<!-- g4:demo -->0.971<!-- /g4 --> and <!-- g4:ghost -->42%<!-- /g4 -->\n")
    problems = check_docs(registry=registry, results_dir=results, root=root)
    assert len(problems) == 1 and "ghost" in problems[0], problems


def test_a_registered_marker_that_is_gone_is_a_failure(tmp_path):
    registry, results, root = _repo(tmp_path, "AUROC 0.971 on SNLI, no marker any more\n")
    problems = check_docs(registry=registry, results_dir=results, root=root)
    assert len(problems) == 1 and "demo" in problems[0], problems


def test_the_same_marker_twice_is_a_failure(tmp_path):
    registry, results, root = _repo(
        tmp_path, "<!-- g4:demo -->0.971<!-- /g4 --> and again <!-- g4:demo -->0.971<!-- /g4 -->\n")
    problems = check_docs(registry=registry, results_dir=results, root=root)
    assert len(problems) == 1 and "demo" in problems[0], problems


def test_an_artifact_that_moved_on_fails_the_old_text(tmp_path):
    registry, results, root = _repo(tmp_path, "<!-- g4:demo -->0.971<!-- /g4 -->\n", value=0.5)
    problems = check_docs(registry=registry, results_dir=results, root=root)
    assert len(problems) == 1 and "0.500" in problems[0], problems


def test_the_published_documents_agree_with_the_registry():
    """The guard itself: the real README (and every file a registry entry names) says what
    the artifacts say. Red here means a number was touched by hand or an artifact changed
    without `python -m benchmark.repro_all --render`."""
    assert check_docs() == []


def test_the_registry_does_publish_through_markers():
    """A guard that checks zero markers passes trivially: at least one registered number
    must actually be rendered into a document."""
    assert any(e.get("docs") for e in REGISTRY.values())
