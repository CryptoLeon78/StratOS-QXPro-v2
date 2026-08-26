from core.auth.security import hash_password, verify_password


def test_verify_password_accepts_correct_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_verify_password_rejects_malformed_hash() -> None:
    assert verify_password("anything", "not-an-argon2-hash") is False


def test_hash_password_produces_different_hashes_for_same_password() -> None:
    # argon2 salts each hash -> nunca debe ser reproducible byte a byte
    assert hash_password("same") != hash_password("same")
