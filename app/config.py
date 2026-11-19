"""Settings, read from environment variables only (no credentials in code or JSON files)."""
import os
from dataclasses import dataclass, field


def env_str(name: str, default: str = '') -> str:
    return os.environ.get(name, default).strip()


def env_int(name: str, default: int) -> int:
    value = env_str(name)
    try:
        return int(value) if value else default
    except ValueError as err:
        raise ValueError(f'{name} must be an integer: {value!r}') from err


def env_bool(name: str, default: bool) -> bool:
    value = env_str(name).lower()
    if not value:
        return default
    return value in ('1', 'true', 'yes', 'on')


def env_list(name: str) -> list:
    return [v.strip() for v in env_str(name).split(',') if v.strip()]


@dataclass(frozen=True)
class AuthConfig:
    """Access tokens of the token server (same settings as the API server `be`)."""
    required: bool
    jwks_uri: str
    public_key: str
    secret: str
    algorithms: list
    issuer: str
    audience: str


@dataclass(frozen=True)
class SftpConfig:
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    private_key_file: str
    private_key_passphrase: str = field(repr=False)
    # Uploads go below this directory and downloads are limited to it ('' = the login directory).
    base_dir: str
    known_hosts: str
    strict_host_key: bool
    timeout: int

    @property
    def configured(self) -> bool:
        return bool(self.host and self.username)


@dataclass(frozen=True)
class Config:
    sftp: SftpConfig
    max_files: int
    max_download: int
    max_content_length: int
    cors_origins: list
    auth: AuthConfig = field(repr=False)
    # SFTP account per tenant from the API server (be /internal/file-servers/<tenant>); empty: the
    # SFTP_* account above is used for every tenant.
    settings_uri: str = ''
    internal_secret: str = field(default='', repr=False)
    settings_ttl: int = 60

    @classmethod
    def from_env(cls) -> 'Config':
        jwks = env_str('JWT_JWKS_URI')
        public_key = env_str('JWT_PUBLIC_KEY').replace('\\n', '\n')
        secret = env_str('JWT_SECRET')
        default_alg = 'HS256' if secret and not (jwks or public_key) else 'RS256'
        return cls(
            sftp=SftpConfig(
                host=env_str('SFTP_HOST'),
                port=env_int('SFTP_PORT', 22),
                username=env_str('SFTP_USER'),
                password=env_str('SFTP_PASSWORD'),
                private_key_file=env_str('SFTP_PRIVATE_KEY_FILE'),
                private_key_passphrase=env_str('SFTP_PRIVATE_KEY_PASSPHRASE'),
                base_dir=env_str('SFTP_BASE_DIR'),
                known_hosts=env_str('SFTP_KNOWN_HOSTS'),
                strict_host_key=env_bool('SFTP_STRICT_HOST_KEY', True),
                timeout=env_int('SFTP_TIMEOUT', 15),
            ),
            max_files=env_int('FILE_MAX_FILES', 50),
            max_download=env_int('FILE_MAX_DOWNLOAD_MB', 100) * 1024 * 1024,
            max_content_length=env_int('MAX_CONTENT_MB', 100) * 1024 * 1024,
            cors_origins=env_list('CORS_ORIGINS'),
            auth=AuthConfig(
                required=env_bool('AUTH_REQUIRED', True),
                jwks_uri=jwks,
                public_key=public_key,
                secret=secret,
                algorithms=env_list('JWT_ALGORITHMS') or [default_alg],
                issuer=env_str('JWT_ISSUER'),
                audience=env_str('JWT_AUDIENCE'),
            ),
            settings_uri=env_str('SERVER_SETTINGS_URI').rstrip('/'),
            internal_secret=env_str('INTERNAL_API_SECRET'),
            settings_ttl=env_int('SERVER_SETTINGS_TTL', 60),
        )
