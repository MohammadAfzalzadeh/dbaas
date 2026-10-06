from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator, field_validator
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import subprocess, tempfile, os, re, yaml, logging, json, secrets
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Literal
from pathlib import Path
from html import escape
from urllib.parse import urlsplit


# ----------------------------
# Logging setup
# ----------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

log = logging.getLogger("dbaas")  # <-- use this instead of plain print/logging
log.setLevel(LOG_LEVEL)
# ----------------------------
# App & static
# ----------------------------
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
origins = [x.strip() for x in os.getenv("DBAAS_ALLOWED_ORIGINS", "").split(",") if x.strip()]
if "*" in origins:
    raise RuntimeError("DBAAS_ALLOWED_ORIGINS must contain explicit origins")
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["POST"], allow_headers=["Authorization", "Content-Type"])

@app.middleware("http")
async def authenticate(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        # Only preflight is public; the subsequent operation still authenticates.
        if request.method != "OPTIONS":
            expected = os.getenv("DBAAS_API_TOKEN", "")
            if len(expected) < 32:
                return JSONResponse(status_code=503, content={"detail": "API authentication is not configured"})
            header = request.headers.get("Authorization", "")
            scheme, _, token = header.partition(" ")
            if scheme.lower() != "bearer" or not secrets.compare_digest(token.encode(), expected.encode()):
                return JSONResponse(status_code=401, content={"detail": "Authentication required"},
                                    headers={"WWW-Authenticate": "Bearer"})
    try:
        response = await call_next(request)
    except Exception as exc:
        # Catch before ASGI's outer error middleware can log raw exception data.
        log.error("Request failed: %s", type(exc).__name__)
        response = JSONResponse(status_code=500, content={"detail": "Internal operation failed"})
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- Jinja env ---
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=False,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

# ----------------------------
# Models
# ----------------------------
class Project(BaseModel):
    releaseName: str = Field(..., min_length=1, max_length=35, pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
    enableMinio: bool = False
    enablePgCat: bool = False
    class Config: extra = "ignore"

class PostgresCreds(BaseModel):
    username: str = Field(..., min_length=1, max_length=63, pattern=r"^[A-Za-z_][A-Za-z0-9_$-]*$")
    password: str = Field(..., min_length=1, max_length=1024)
    class Config: extra = "ignore"

class Postgres(BaseModel):
    pgReplicas: int = Field(1, ge=1, le=100, strict=True)
    pgStorageCapacity: int = Field(20, ge=1, le=1048576, strict=True)
    superuser: PostgresCreds | None = None
    replication: PostgresCreds | None = None
    class Config: extra = "ignore"

class DB(BaseModel):
    name: str
    poolMode: Literal["session", "transaction"] | None = None
    primaryReadMode: bool | None = None
    class Config: extra = "ignore"

class User(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    connectionLimit: int | None = Field(None, ge=1, le=10000, strict=True)
    validUntil: str | None = None
    class Config: extra = "ignore"

class AccessRule(BaseModel):
    username: str
    database: str
    accessLevel: str
    maxConnections: int | None = None
    class Config: extra = "ignore"

class WalGS3(BaseModel):
    accessKey: str | None = None
    secretKey: str | None = None
    endpoint: str | None = None
    bucketName: str | None = None
    class Config: extra = "ignore"

    @field_validator("endpoint")
    @classmethod
    def safe_endpoint(cls, value):
        if value:
            url = urlsplit(value)
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("S3 endpoint must be HTTP(S) without embedded credentials/query")
        return value

    @field_validator("bucketName")
    @classmethod
    def safe_bucket(cls, value):
        if value and not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", value):
            raise ValueError("Invalid S3 bucket name")
        return value

class WalGBackup(BaseModel):
    enablePITR: bool = False
    compressionMethod: Literal["brotli", "lz4", "lzma", "zstd"] = "brotli"
    backupSchedule: str = "0 2 * * *"
    @field_validator("backupSchedule")
    @classmethod
    def valid_schedule(cls, value):
        fields = value.split()
        if len(fields) != 5:
            raise ValueError("backupSchedule must have five cron fields")
        for field, (low, high) in zip(fields, [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]):
            for item in field.split(","):
                parts = item.split("/")
                if len(parts) > 2 or (len(parts) == 2 and (not parts[1].isdigit() or int(parts[1]) < 1)):
                    raise ValueError("invalid cron step")
                if parts[0] == "*":
                    continue
                bounds = parts[0].split("-")
                if len(bounds) > 2 or not all(x.isdigit() and low <= int(x) <= high for x in bounds):
                    raise ValueError("invalid cron field")
                if len(bounds) == 2 and int(bounds[0]) > int(bounds[1]):
                    raise ValueError("invalid cron range")
        return value

    class Config: extra = "ignore"

class WalG(BaseModel):
    s3: WalGS3 | None = None
    backup: WalGBackup | None = None
    class Config: extra = "ignore"

class Monitoring(BaseModel):
    enableLogMonitoring: bool = False
    enableSystemMonitoring: bool = False
    monitoringDocsProvided: bool = False
    class Config: extra = "ignore"

class MinioSpec(BaseModel):
    rootUser: str = ""
    rootPassword: str = ""
    storageCapacity: int = Field(..., ge=1, le=1048576, strict=True)  # Gi
    backupUser: str = ""
    backupPassword: str = ""
    backupBucket: str = ""

    @model_validator(mode="after")
    def backup_user_must_differ_from_root(self):
        if self.rootUser and self.rootUser.strip() == self.backupUser.strip():
            raise ValueError("MinIO backup user must be different from the root user")
        return self

class SecretReferences(BaseModel):
    postgres: str = ""
    walg: str = ""
    pgcat: str = ""
    pgadmin: str = ""
    minio: str = ""

    @field_validator("*")
    @classmethod
    def secret_name(cls, value):
        if value and (len(value) > 253 or any(not SAFE.fullmatch(part) or len(part) > 63 for part in value.split("."))):
            raise ValueError("Invalid Secret name")
        return value

class DeploySpec(BaseModel):
    existingSecrets: SecretReferences = Field(default_factory=SecretReferences)

    namespace: str = Field("dbaas", max_length=63, pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
    project: Project
    postgresql: Postgres
    databases: list[DB] = []
    users: list[User] = []
    databaseAccess: list[AccessRule] = []
    walg: WalG | None = None
    monitoring: Monitoring | None = None
    minio: Optional[MinioSpec] = None      # ← single, strong schema
    @model_validator(mode="after")
    def consistent_spec(self):
        if self.project.enableMinio and self.minio is None:
            raise ValueError("MinIO enabled but minio settings are missing")
        if self.walg and self.walg.backup and self.walg.backup.enablePITR:
            raise ValueError("PITR is an operator recovery operation; use scripts/ptr_recovery.sh. It cannot be enabled by provisioning.")
        for name, values in [("database", [x.name for x in self.databases]), ("user", [x.username for x in self.users])]:
            if len(set(values)) != len(values) or any(not x or len(x.encode()) > 63 or "\n" in x or "\r" in x for x in values):
                raise ValueError(f"{name} names must be nonempty, unique, and at most 63 bytes")
        def check_strings(value):
            if isinstance(value, dict):
                for item in value.values():
                    check_strings(item)
            elif isinstance(value, list):
                for item in value:
                    check_strings(item)
            elif isinstance(value, str) and any(ord(char) < 32 for char in value):
                raise ValueError("Configuration strings cannot contain control characters")
        check_strings(self.model_dump())
        return self

    class Config: extra = "ignore"

# ----------------------------
# Utilities
# ----------------------------
SAFE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")  # k8s DNS-1123 label

def assert_dns_label(val: str, field: str):
    if not SAFE.match(val):
        raise HTTPException(422, f"{field} must be DNS-1123 (lowercase, digits, '-')")

# redact secrets in nested dicts
SECRET_KEYS = re.compile(r"(password|pass$|secret|access.?key|token|authorization|credential|endpoint|(^|_)(url|uri)$)", re.I)
def redact(obj):
    if isinstance(obj, dict):
        return {k: ("***REDACTED***" if SECRET_KEYS.search(k) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj

def run(cmd: list[str]) -> str:
    operation = " ".join(cmd[:2])
    log.info("Subprocess started: %s", operation)
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=660)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Provisioning command timed out") from None
    except OSError:
        raise HTTPException(500, "Provisioning tool unavailable") from None
    if p.returncode:
        log.warning("Subprocess failed: %s exit=%s", operation, p.returncode)
        raise HTTPException(400, "Provisioning command failed; inspect cluster state with operator tools")
    return "Helm operation completed"

def render(template_name: str, ctx: dict) -> str:
    log.info("Render template: %s", template_name)
    return jinja.get_template(template_name).render(**ctx)
def find_chart(component: str) -> str:
    """
    Return a path to a Helm chart directory or .tgz for the given component
    by checking (in order):
      1) Env var (e.g., CHART_MINIO, CHART_PATRONI, CHART_PGCAT)
      2) /app/helmCharts/<component>
      3) Bundled charts relative to this module
      4) ./helmCharts/<component> relative to CWD, then ancestor folders
      5) Any matching .tgz next to those folders (e.g., minio-*.tgz)
    """
    env_name = f"CHART_{component.upper()}"
    env_path = os.getenv(env_name)
    if env_path:
        if not Path(env_path).exists():
            raise RuntimeError(f"{env_name} does not exist")
        return str(Path(env_path).resolve())

    candidates: list[Path] = []

    # inside container default
    candidates.append(Path(f"/app/helmCharts/{component}"))

    # Prefer bundled charts so repository-root execution uses the app family.
    candidates.append(Path(__file__).resolve().parents[1] / "helmCharts" / component)
    candidates.append(Path.cwd() / "helmCharts" / component)

    # search upwards from this file for a 'helmCharts' folder
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        hc = parent / "helmCharts" / component
        candidates.append(hc)

    # also look for packaged charts (.tgz) next to those
    extra_tgz = []
    for c in candidates:
        if c.parent.exists():
            extra_tgz.extend(c.parent.glob(f"{component}-*.tgz"))
    candidates.extend(extra_tgz)

    for c in candidates:
        if c.exists():
            return str(c)

    raise HTTPException(
        400,
        f"Helm chart for '{component}' not found. "
        f"Checked env {env_name} and candidates: "
        + ", ".join(str(p) for p in candidates)
    )

# chart paths inside the image
# CHART_PATRONI = "/app/helmCharts/patroni"
# CHART_MINIO   = "app/helmCharts/minio"
# CHART_PGCAT   = "/app/helmCharts/pgcat"
CHART_MINIO   = find_chart("minio")
CHART_PATRONI = find_chart("patroni")
CHART_PGCAT   = find_chart("pgcat")
# ----------------------------
# Middleware & handlers
# ----------------------------
@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # Pydantic errors include submitted values, including passwords.
    return JSONResponse(status_code=422, content={"detail": "Invalid deployment specification"})

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.error("Request failed: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Internal operation failed"})

# ----------------------------
# Routes
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    log.info("Serving UI: static/index.html")
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

@app.get("/healthz")
def healthz():
    log.debug("healthz ping")
    return {"ok": True}

@app.get("/readyz")
def readyz():
    # Local dependencies only: a Kubernetes outage must not trigger API restarts.
    import shutil
    ready = (len(os.getenv("DBAAS_API_TOKEN", "")) >= 32
             and all(shutil.which(tool) for tool in ("helm", "kubectl"))
             and all((Path(chart) / "Chart.yaml").is_file()
                     for chart in (CHART_MINIO, CHART_PATRONI, CHART_PGCAT)))
    return JSONResponse(status_code=200 if ready else 503, content={"ready": bool(ready)})

def build_context(spec: DeploySpec) -> dict:
    ctx = spec.model_dump()
    ctx["release"] = spec.project.releaseName
    ctx["patroniReleaseName"] = f"{spec.project.releaseName}-patroni"
    supplied = bool(spec.postgresql.superuser or spec.postgresql.replication or spec.users or (spec.minio and (spec.minio.rootPassword or spec.minio.backupPassword)) or (spec.walg and spec.walg.s3 and (spec.walg.s3.accessKey or spec.walg.s3.secretKey)))
    ctx["inlineSecrets"] = supplied and os.getenv("DBAAS_ALLOW_INLINE_SECRETS", "false").lower() == "true"
    if not ctx["inlineSecrets"]:
        if supplied:
            raise HTTPException(422, "Use existingSecrets; inline credentials are disabled")
        for kind in ["superuser", "replication"]:
            ctx["postgresql"][kind] = {"username": "postgres" if kind == "superuser" else "replicator", "password": ""}
    else:
        default_file = Path(CHART_PATRONI) / "values.yaml"
        if default_file.is_file():
            defaults = yaml.safe_load(default_file.read_text())["postgres"]
        else:
            result = subprocess.run(["helm", "show", "values", CHART_PATRONI], capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise HTTPException(500, "Cannot read Patroni chart defaults")
            defaults = yaml.safe_load(result.stdout)["postgres"]
        for kind, prefix in [("superuser", "SUPERUSER"), ("replication", "REPLICATION")]:
            if ctx["postgresql"][kind] is None:
                ctx["postgresql"][kind] = {"username": defaults[f"{prefix}_USERNAME"], "password": defaults[f"{prefix}_PASSWORD"]}
    if not ctx["databases"]:
        ctx["databases"] = [{"name": "postgres", "poolMode": "session", "primaryReadMode": True}]
    if not ctx["users"]:
        ctx["users"] = [{**ctx["postgresql"]["superuser"], "connectionLimit": 10}]
    return ctx


def generated_values(spec: DeploySpec) -> dict[str, str]:
    allowed = {x.strip() for x in os.getenv("DBAAS_ALLOWED_NAMESPACES", "dbaas").split(",") if x.strip()}
    if spec.namespace not in allowed:
        raise HTTPException(403, "Namespace is not authorized")
    ctx = build_context(spec)
    components = (["minio"] if spec.project.enableMinio else []) + ["patroni"] + (["pgcat"] if spec.project.enablePgCat else [])
    values = {}
    for component in components:
        content = render(f"{component}-values.yaml.j2", ctx)
        if not isinstance(yaml.safe_load(content), dict):
            raise HTTPException(422, f"Invalid generated {component} values")
        values[component] = content
    return values


@app.post("/api/values/preview", response_class=HTMLResponse)
def preview(spec: DeploySpec):
    return "".join(f"<h3>{component}</h3><pre>{escape(yaml.safe_dump(redact(yaml.safe_load(content)), sort_keys=False))}</pre>" for component, content in generated_values(spec).items())


@app.post("/api/deploy")
def deploy(spec: DeploySpec):
    values = generated_values(spec)
    charts = {"minio": CHART_MINIO, "patroni": CHART_PATRONI, "pgcat": CHART_PGCAT}
    outputs, completed = [], []
    # Namespace and its provisioning RoleBinding must be prepared by the operator.
    # No automatic rollback: earlier releases/data are retained on a later failure.
    with tempfile.TemporaryDirectory(prefix="dbaas-values-") as directory:
        files = {}
        for component, content in values.items():
            path = Path(directory) / f"{component}.yaml"
            path.write_text(content, encoding="utf-8")
            path.chmod(0o600)
            files[component] = str(path)
        try:
            # Validate every component before creating any release.
            for component in values:
                run(["helm", "lint", charts[component], "-f", files[component]])
            for component in values:
                release = f"{spec.project.releaseName}-{component}"
                output = run(["helm", "upgrade", "--install", release, charts[component],
                              "--namespace", spec.namespace, "-f", files[component],
                              "--wait", "--wait-for-jobs", "--timeout", "10m0s" if component == "patroni" else "5m0s"])
                # Helm treats OnDelete StatefulSets as ready without waiting for pods.
                # Wait explicitly for the desired member count before the next component.
                if component in {"minio", "patroni"}:
                    workload = release + ("-minio-statefulset" if component == "minio" else "-patronimvp")
                    replicas = 1 if component == "minio" else spec.postgresql.pgReplicas
                    run(["kubectl", "wait", "--namespace", spec.namespace,
                         f"--for=jsonpath={{.status.readyReplicas}}={replicas}",
                         "statefulset/" + workload, "--timeout=600s"])
                outputs.append(output)
                completed.append(release)
        except HTTPException as exc:
            raise HTTPException(exc.status_code, {"message": "Provisioning failed; no automatic rollback was performed",
                                                "completedReleases": completed, "cause": exc.detail}) from exc
    return {"ok": True, "release": spec.project.releaseName, "namespace": spec.namespace,
            "output": "\n\n---\n\n".join(outputs)}
