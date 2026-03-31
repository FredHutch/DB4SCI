
import os
import sys
import yaml

def get_secret(secret_name, env_var_name=None):
    """
    Get secret from Docker Swarm secret file or fall back to environment variable.
    Useful for local development (env vars) vs production (Docker secrets).
    """
    # Try Docker secret first
    secret_path = f"/run/secrets/{secret_name}"
    if os.path.exists(secret_path):
        with open(secret_path, "r") as f:
            return f.read().strip()

    # Fall back to environment variable
    if env_var_name:
        return os.getenv(env_var_name)

    return None


env_type = os.getenv("DB4SCI_ENV")
if (not env_type) or (env_type not in ['dev', 'prod']) :
    print("Environment variable DB4SCI_ENV must be set to dev or prod.")
    sys.exit(5)

config_file = f"mydb-config-{env_type}.yml"

with open(config_file, "r") as f:
    config = yaml.safe_load(f)


_this_module = sys.modules[__name__]


for key, value in config.items():
    if hasattr(_this_module, key):
        continue
    setattr(_this_module, key, value)


FQDN_host = config['container_host'] + "." + config['container_domain']

MAIL_TO = os.getenv("supportAdmin")

AWS_BUCKET_NAME = get_secret("aws_bucket_name", "AWS_BUCKET_NAME")
FLASK_SECRET = get_secret("flask_secret", "FLASK_SECRET")
SQLALCHEMY_ADMIN_URI = get_secret("sqlalchemy_admin_uri", "SQLALCHEMY_ADMIN_URI")
SQLALCHEMY_MIGRATE_URI = get_secret("sqlalchemy_migrate_uri", "SQLALCHEMY_MIGRATE_URI")


