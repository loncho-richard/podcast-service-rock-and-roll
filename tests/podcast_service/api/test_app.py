from fastapi import FastAPI
from syrupy.assertion import SnapshotAssertion


def test_openapi_documents_the_status_codes_of_each_route(
    app: FastAPI, snapshot: SnapshotAssertion
) -> None:
    paths = app.openapi()["paths"]

    assert {
        f"{method.upper()} {path}": sorted(operation["responses"])
        for path, operations in paths.items()
        for method, operation in operations.items()
    } == snapshot


def test_protected_routes_declare_the_bearer_scheme(app: FastAPI) -> None:
    paths = app.openapi()["paths"]

    assert sorted(
        f"{method.upper()} {path}"
        for path, operations in paths.items()
        for method, operation in operations.items()
        if not operation.get("security")
    ) == ["GET /health", "POST /auth/token"]
