"""Settings module for test app."""
ENV = "development"
TESTING = True
SQLALCHEMY_DATABASE_URI = "sqlite:///test.sqlite"
SECRET_KEY = "not-so-secret-in-tests"
BCRYPT_LOG_ROUNDS = (
    4  # For faster tests; needs at least 4 to avoid "ValueError: Invalid rounds"
)
DEBUG_TB_ENABLED = False
SQLALCHEMY_TRACK_MODIFICATIONS = False
WTF_CSRF_ENABLED = False  # Allows form testing
SQLALCHEMY_ECHO = False
