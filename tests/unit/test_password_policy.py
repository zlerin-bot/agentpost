import pytest

from agentpost.accounts.crypto import hash_password, validate_password, verify_password


def test_new_password_minimum_is_eight_and_existing_hashes_still_verify():
    assert validate_password("abcd1234") == "abcd1234"
    for password in ("1234567", "        ", "x" * 257):
        with pytest.raises(ValueError):
            validate_password(password)
    for password in ("abcd1234", "existing password longer than twelve"):
        salt, digest = hash_password(password)
        assert verify_password(password, salt, digest)
        assert not verify_password("wrong-password", salt, digest)
