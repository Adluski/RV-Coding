import os

# Must be set before backend.app.db is imported anywhere.
os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["ADMIN_USERNAME"] = "root_admin"
os.environ["ADMIN_PASSWORD"] = "admin-pass-123"
