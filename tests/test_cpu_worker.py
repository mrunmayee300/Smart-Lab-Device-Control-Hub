from smart_lab.workers.cpu_worker import spectral_feature_extraction


def test_spectral_feature_extraction() -> None:
    features = spectral_feature_extraction([1.0, 2.0, 3.0])

    assert features["mean"] == 2.0
    assert round(features["rms"], 3) == 2.16
    assert features["peak"] == 3.0
