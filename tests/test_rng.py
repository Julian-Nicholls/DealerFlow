from dealerflow.rng import RandomStreams, poisson


def test_named_streams_are_reproducible() -> None:
    first = RandomStreams(4172)
    second = RandomStreams(4172)
    assert [first.get("demand").random() for _ in range(5)] == [
        second.get("demand").random() for _ in range(5)
    ]


def test_stream_names_are_independent() -> None:
    streams = RandomStreams(4172)
    assert streams.get("demand").random() != streams.get("logistics").random()


def test_poisson_zero_mean() -> None:
    assert poisson(RandomStreams(1).get("x"), 0) == 0
