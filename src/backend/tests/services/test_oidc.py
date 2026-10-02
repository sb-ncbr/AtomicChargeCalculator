from datetime import UTC, datetime
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.oidc import OIDCService


@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def service(monkeypatch, signing_key):
    for name, value in {
        "OIDC_BASE_URL": "https://issuer.example",
        "OIDC_DISCOVERY_URL": "https://issuer.example/.well-known/openid-configuration",
        "OIDC_REDIRECT_URL": "https://app.example/callback",
        "OIDC_CLIENT_ID": "test-client",
        "OIDC_CLIENT_SECRET": "test-secret",
    }.items():
        monkeypatch.setenv(name, value)
    service = OIDCService(logger=Mock())
    service.config_cache["config"] = {"issuer": "https://issuer.example"}
    key = jwt.algorithms.RSAAlgorithm.to_jwk(signing_key.public_key(), as_dict=True)
    service.jwks_cache["jwks"] = {"keys": [{**key, "kid": "test-key", "use": "sig"}]}
    return service


@pytest.fixture
def claims():
    now = int(datetime.now(UTC).timestamp())
    return {
        "sub": "test-user",
        "iss": "https://issuer.example",
        "aud": "test-client",
        "iat": now - 60,
        "nbf": now - 60,
        "exp": now + 300,
    }


@pytest.mark.asyncio
async def test_verify_valid_token(service, signing_key, claims):
    token = jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": "test-key"})
    assert await service.verify_token(token) == claims


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": 1},
        {"nbf": 4102444800},
        {"iat": 4102444800},
        {"aud": "wrong-client"},
        {"iss": "https://wrong-issuer.example"},
    ],
)
async def test_reject_invalid_claims(service, signing_key, claims, overrides):
    token = jwt.encode(
        {**claims, **overrides}, signing_key, algorithm="RS256", headers={"kid": "test-key"}
    )
    assert await service.verify_token(token) is None
    service.logger.warn.assert_called_once()
    service.logger.error.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["aud", "iss"])
async def test_reject_missing_identity_claims(service, signing_key, claims, missing):
    del claims[missing]
    token = jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": "test-key"})
    assert await service.verify_token(token) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [{}, {"kid": "unknown-key"}])
async def test_reject_missing_or_unknown_key_id(service, signing_key, claims, headers):
    token = jwt.encode(claims, signing_key, algorithm="RS256", headers=headers)
    assert await service.verify_token(token) is None


@pytest.mark.asyncio
async def test_reject_invalid_signature(service, claims):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(claims, other_key, algorithm="RS256", headers={"kid": "test-key"})
    assert await service.verify_token(token) is None
    service.logger.warn.assert_called_once()
    service.logger.error.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("algorithm", ["HS256", "none"])
async def test_reject_unapproved_algorithm(service, claims, algorithm):
    key = "a-test-secret-that-is-at-least-32-bytes" if algorithm == "HS256" else None
    token = jwt.encode(claims, key, algorithm=algorithm, headers={"kid": "test-key"})
    assert await service.verify_token(token) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["", "not-a-jwt", "a.b.c"])
async def test_reject_malformed_token(service, token):
    assert await service.verify_token(token) is None
    service.logger.warn.assert_called_once()
    service.logger.error.assert_not_called()
