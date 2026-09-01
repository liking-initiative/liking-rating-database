

def test_unrelated_env_vars_do_not_break_settings(tmp_path, monkeypatch):
    """A secret in .env that the app does not read must not stop it booting.

    The .env is a shared operator file -- it carries GITHUB_TOKEN for the
    release download and ZENODO_TOKEN for publishing, neither of which the
    application reads. pydantic-settings defaults to extra="forbid", so
    adding one of those once raised at import time and took down every
    route, with an error naming the variable but not the consequence.
    """
    env = tmp_path / ".env"
    # LOG_LEVEL, not RATE_LIMIT_PER_MINUTE: conftest exports the latter into
    # the real environment, which outranks any env file, so asserting on it
    # would test the fixture rather than the fix.
    env.write_text(
        "ZENODO_TOKEN=irrelevant-to-the-api\n"
        "GITHUB_TOKEN=also-irrelevant\n"
        "LOG_LEVEL=DEBUG\n"
    )
    monkeypatch.chdir(tmp_path)

    from backend.config import Settings

    s = Settings(_env_file=str(env))
    assert s.LOG_LEVEL == "DEBUG"  # declared keys are still read
    assert not hasattr(s, "ZENODO_TOKEN")  # undeclared ones are ignored
