def test_framework_importa() -> None:
    import stella.framework

    assert stella.framework.__doc__ is not None


def test_agents_dir_importa() -> None:
    import stella.agents

    assert stella.agents.__doc__ is not None
