import pytest
from backend.app.core.security import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    raw_pass = "MySecretPassword123"
    hashed = hash_password(raw_pass)
    
    assert hashed != raw_pass
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_token_encoding_decoding():
    data = {"sub": "investor@test.com", "id": 42}
    token = create_access_token(data)
    
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "investor@test.com"
    assert decoded["id"] == 42
