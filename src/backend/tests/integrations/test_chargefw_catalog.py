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


def test_method_notes_offer_nothing_acc_does_not_have(engine):
    import chargefw

    notes = {m.internal_name: m.notes for m in engine.get_available_methods()}

    assert notes["formal"] == "Returns the formal charges of the input unchanged; not a charge model."
    assert notes["dummy"] == "Returns zero for every atom; not a charge model."
    assert notes["eem"] is None
    # ACC runs every method with its default options and does not offer the others.
    for method in chargefw.methods.values():
        for option in method.options:
            assert option not in (notes[method.id] or ""), (method.id, option)


@pytest.mark.parametrize(
    "method,parameters,error",
    [
        ("sqeqp", "SQEqp_Schindler2021_CCD_gen", None),
        ("eqeq", None, None),
        ("nope", None, "Method 'nope' is not available."),
        ("sqeqp", None, "Method sqeqp requires parameters."),
        ("eqeq", "EEM_Baek1991", "Method eqeq has no parameters."),
        ("sqeqp", "SQEqp_99_unknown", "Parameters 'SQEqp_99_unknown' are not available for method sqeqp."),
        ("sqeqp", "EEM_Baek1991", "Parameters 'EEM_Baek1991' are not available for method sqeqp."),
    ],
)
def test_config_errors_name_the_problem(engine, method, parameters, error):
    assert engine.config_error(method, parameters) == error
