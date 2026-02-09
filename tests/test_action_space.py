from pokemon_red_env.action_space import build_action_bindings


def test_action_bindings_default_have_noop_last():
    bindings = build_action_bindings(include_select=False, include_noop=True)
    assert len(bindings) == 8
    assert bindings[-1].name == "noop"
    assert bindings[-1].is_noop is True


def test_action_bindings_with_select_put_noop_last():
    bindings = build_action_bindings(include_select=True, include_noop=True)
    assert len(bindings) == 9
    assert bindings[-2].name == "select"
    assert bindings[-1].name == "noop"
