import pytest

from app.integrations.chargefw.chargefw import ChargeFWLocal


@pytest.fixture(scope="module")
def engine():
    return ChargeFWLocal()


def test_methods_have_ids_and_types(engine):
    methods = {method.internal_name: method for method in engine.get_available_methods()}

    assert len(methods) == 22
    assert next(iter(methods)) == "sqeqp"
    assert methods["sqeqp"].type == "3D"
    assert methods["eem"].type == "3D"
    assert methods["peoe"].type == "2D"
    # The two methods that are not charge models are of type "other".
    assert methods["formal"].type == "other"
    assert methods["dummy"].type == "other"
    assert methods["eem"].has_parameters
    assert not methods["eqeq"].has_parameters


def test_parameters_belong_to_their_method(engine):
    for method in engine.get_available_methods():
        parameters = engine.get_available_parameters(method.internal_name)

        assert len(parameters) > 0 if method.has_parameters else parameters == []
        assert all(p.method == method.internal_name for p in parameters)

    sqeqp = [p.internal_name for p in engine.get_available_parameters("sqeqp")]
    assert sqeqp[0] == "SQEqp_Schindler2021_CCD_gen"
