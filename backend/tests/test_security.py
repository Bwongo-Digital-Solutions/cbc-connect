import os
import pytest
from app.security import hash_password, authenticate, create_access_token, decode_access_token

def test_password_hash_and_verify():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert authenticate("correct-horse-battery-staple", hashed)
    assert not authenticate("wrong-password", hashed)

def test_jwt_round_trip(monkeypatch):
    monkeypatch.setenv("CBC_JWT_SECRET", "x" * 48)
    token = create_access_token({"sub":"test-user","role":"TECHNICIAN"})
    claims = decode_access_token(token)
    assert claims["sub"] == "test-user"
    assert claims["role"] == "TECHNICIAN"

def test_short_password_rejected():
    with pytest.raises(ValueError):
        hash_password("short")
