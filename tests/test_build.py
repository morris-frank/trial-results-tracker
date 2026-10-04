from trial_results_tracker.__main__ import main


def test_build_writes_the_site(tmp_path):
    main(["build", "--out", str(tmp_path)])
    assert (tmp_path / "index.html").is_file()
