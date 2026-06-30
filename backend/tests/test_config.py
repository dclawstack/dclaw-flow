"""Production config hardening checks (Phase 1)."""

from app.config import Settings


def test_no_warnings_in_development():
    s = Settings(app_env="development", admin_token="change-me-in-production")
    assert s.insecure_config_warnings() == []


def test_production_flags_default_secrets_and_bad_cors():
    s = Settings(
        app_env="production",
        webhook_secret="change-me-in-production",
        admin_token="change-me-in-production",
        cors_origins="*,http://localhost:3000",
    )
    issues = " ".join(s.insecure_config_warnings())
    assert "WEBHOOK_SECRET" in issues
    assert "ADMIN_TOKEN" in issues
    assert "JWT_SECRET" in issues
    assert "wildcard" in issues
    assert "localhost" in issues


def test_production_clean_config_has_no_warnings():
    s = Settings(
        app_env="production",
        webhook_secret="real-secret",
        admin_token="real-token",
        jwt_secret="real-jwt-secret",
        cors_origins="https://app.example.com",
    )
    assert s.insecure_config_warnings() == []


def test_cors_credentials_disabled_with_wildcard():
    assert Settings(cors_origins="*").cors_allow_credentials is False
    assert Settings(cors_origins="https://app.example.com").cors_allow_credentials
