# ABOUTME: Sample hook that extends the Jinja2 env with a custom filter.
# Used by tests/test_plugins.py to verify on_env hook discovery.


def on_env(env, config):  # type: ignore[no-untyped-def]
    env.filters["shout"] = lambda text: text.upper() + "!"
    return env
