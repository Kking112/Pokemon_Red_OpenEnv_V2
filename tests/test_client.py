from pokemon_red_env.client import PokemonRedEnv
from pokemon_red_env.models import PokemonRedAction


def test_client_payload_and_parse():
    client = PokemonRedEnv(base_url="http://localhost:9999")
    payload = client._step_payload(PokemonRedAction(action=3))
    assert payload["action"] == 3

    result = client._parse_result(
        {
            "observation": {
                "screen_b64": "",
                "screen_shape": [144, 160, 3],
                "game_state": {"x": 1},
                "legal_actions": [0, 1],
                "info": {},
            },
            "reward": 1.25,
            "done": False,
        }
    )
    assert result.reward == 1.25
    assert result.done is False
    assert result.observation.game_state["x"] == 1
