from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator
from jinja2 import Environment, FileSystemLoader, select_autoescape
import subprocess, tempfile, os, re, yaml, logging, json, traceback
from typing import Optional
import time, datetime, json

# ----------------------------
# Logging setup
# ----------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

log = logging.getLogger("dbaas")  # <-- use this instead of plain print/logging
log.setLevel(LOG_LEVEL)
# ----------------------------
# App & static
# ----------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Jinja env ---
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(disabled_extensions=("yaml", "yml")),
    trim_blocks=True,
    lstrip_blocks=True,
)

# ----------------------------
# Models
# ----------------------------
class Project(BaseModel):
    releaseName: str = Field(..., min_length=1)
    enableMinio: bool = False
    enablePgCat: bool = False
    class Config: extra = "ignore"

class PostgresCreds(BaseModel):
    username: str
    password: str
    class Config: extra = "ignore"

class Postgres(BaseModel):
    pgReplicas: int = 1
    pgStorageCapacity: int = 20
    superuser: PostgresCreds | None = None
    replication: PostgresCreds | None = None
    class Config: extra = "ignore"

class DB(BaseModel):
    name: str
    poolMode: str | None = None
    primaryReadMode: bool | None = None
    class Config: extra = "ignore"

class User(BaseModel):
    username: str
    password: str
    connectionLimit: int | None = None
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

class WalGBackup(BaseModel):
    enablePITR: bool = False
    compressionMethod: str = "brotli"
    backupSchedule: str = "0 2 * * *"
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
    rootUser: str
    rootPassword: str = Field(..., min_length=8)
    storageCapacity: int = Field(..., ge=1)  # Gi
    backupUser: str
    backupPassword: str = Field(..., min_length=8)
    backupBucket: str

    @model_validator(mode="after")
    def backup_user_must_differ_from_root(self):
        if self.rootUser.strip() == self.backupUser.strip():
            raise ValueError("MinIO backup user must be different from the root user")
        return self

class DeploySpec(BaseModel):
    namespace: str = "dbaas"
    project: Project
    postgresql: Postgres
    databases: list[DB] = []
    users: list[User] = []
    databaseAccess: list[AccessRule] = []
    walg: WalG | None = None
    monitoring: Monitoring | None = None
    minio: Optional[MinioSpec] = None      # ← single, strong schema
    class Config: extra = "ignore"

# ----------------------------
# Utilities
# ----------------------------
SAFE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")  # k8s DNS-1123 label

def assert_dns_label(val: str, field: str):
    if not SAFE.match(val):
        raise HTTPException(422, f"{field} must be DNS-1123 (lowercase, digits, '-')")

# redact secrets in nested dicts
SECRET_KEYS = re.compile(r"(password|secret|accesskey|rootpassword|backupPassword|secretKey)", re.I)
def redact(obj):
    if isinstance(obj, dict):
        return {k: ("***REDACTED***" if SECRET_KEYS.search(k) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj

def run(cmd: list[str]) -> str:
    log.info("RUN: %s", " ".join(cmd))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    log.debug("RUN-OUTPUT:\n%s", p.stdout.strip())
    if p.returncode != 0:
        log.error("RUN-ERROR (exit %s):\n%s", p.returncode, p.stdout.strip())
        raise HTTPException(400, f"Command failed: {' '.join(cmd)}\n{p.stdout}")
    return p.stdout

def render(template_name: str, ctx: dict) -> str:
    log.info("Render template: %s", template_name)
    if log.isEnabledFor(logging.DEBUG):
        log.debug("Render context (redacted): %s", json.dumps(redact(ctx), ensure_ascii=False))
    return jinja.get_template(template_name).render(**ctx)
from pathlib import Path

def find_chart(component: str) -> str:
    """
    Return a path to a Helm chart directory or .tgz for the given component
    by checking (in order):
      1) Env var (e.g., CHART_MINIO, CHART_PATRONI, CHART_PGCAT)
      2) /app/helmCharts/<component>
      3) ./helmCharts/<component> relative to CWD
      4) <repo_root>/helmCharts/<component> by searching upwards from this file
      5) Any matching .tgz next to those folders (e.g., minio-*.tgz)
    """
    env_name = f"CHART_{component.upper()}"
    env_path = os.getenv(env_name)
    if env_path and Path(env_path).exists():
        return str(Path(env_path).resolve())

    candidates: list[Path] = []

    # inside container default
    candidates.append(Path(f"/app/helmCharts/{component}"))

    # relative to current working dir
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
@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        log.info("REQ %s %s", request.method, request.url.path)
        response = await call_next(request)
        log.info("RES %s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    except Exception as e:
        log.exception("Unhandled error in middleware: %s", e)
        raise

@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Ensure JSON error responses + log stack
    tb = "".join(traceback.format_exception(exc))
    log.error("EXC %s %s\n%s", request.method, request.url.path, tb)
    # If it's already an HTTPException, keep its code; else use 500
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"ok": False, "detail": exc.detail})
    return JSONResponse(status_code=500, content={"ok": False, "detail": str(exc)})

# ----------------------------
# Routes
# ----------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    log.info("Serving UI: static/index.html")
    return open("static/index.html","r",encoding="utf-8").read()

@app.get("/healthz")
def healthz():
    log.debug("healthz ping")
    return {"ok": True}

@app.post("/api/values/preview", response_class=HTMLResponse)
def preview(spec: DeploySpec):
    # show redacted incoming spec
    log.info("Preview requested for release '%s' in ns '%s'", spec.project.releaseName, spec.namespace)
    if log.isEnabledFor(logging.DEBUG):
        log.debug("Incoming spec (redacted): %s", json.dumps(redact(spec.model_dump(exclude_none=True)), ensure_ascii=False))

    ctx = yaml.safe_load(yaml.safe_dump(spec.model_dump(exclude_none=True)))
    patroni_yaml = render("patroni-values.yaml.j2", ctx)
    minio_yaml   = render("minio-values.yaml.j2", ctx) if spec.project.enableMinio else "(MinIO disabled)"
    pgcat_yaml   = render("pgcat-values.yaml.j2", ctx) if spec.project.enablePgCat else "(PgCat disabled)"
    return f"<h3>patroni</h3><pre>{patroni_yaml}</pre><h3>minio</h3><pre>{minio_yaml}</pre><h3>pgcat</h3><pre>{pgcat_yaml}</pre>"

def _debug_write_yaml(prefix: str, content: str | dict) -> str:
    """Write YAML (str or dict) to /tmp with a timestamped filename and return the path."""
    ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    path = f"/tmp/{prefix}-{ts}.yaml"
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(content, dict):
            yaml.safe_dump(content, f, sort_keys=False)
        else:
            f.write(content)
    log.info("DEBUG: wrote %s", path)
    return path

@app.post("/api/deploy")
def deploy(spec: DeploySpec):
    log.info("Deploy requested: release='%s' ns='%s'", spec.project.releaseName, spec.namespace)
    if log.isEnabledFor(logging.DEBUG):
        log.debug("Incoming spec (redacted): %s",
                  json.dumps(redact(spec.model_dump(exclude_none=True)), ensure_ascii=False))

    release = spec.project.releaseName
    ns = spec.namespace
    outputs = []

    # Sanity checks
    if spec.project.enableMinio and not spec.minio:
        raise HTTPException(400, "MinIO enabled but 'minio' block is missing in request.")
    # Only verify namespace exists (no create here)
    # run(["kubectl", "get", "ns", ns])
    # Shared Jinja context for templates
    ctx = {
        "release": release,
        "namespace": ns,
        "project": spec.project.model_dump(),
        "postgresql": spec.postgresql.model_dump(),
        "databases": [d.model_dump() for d in spec.databases],
        "users": [u.model_dump() for u in spec.users],
        "minio": spec.minio.model_dump() if spec.minio else None,
        "walg": spec.walg.model_dump() if spec.walg else None,
        "monitoring": spec.monitoring.model_dump() if spec.monitoring else None,
        "access": [a.model_dump() for a in spec.databaseAccess],
        "patroniRelease" : release + '-patroni'
    }
    if log.isEnabledFor(logging.DEBUG):
        log.debug("Template ctx (redacted): %s", json.dumps(redact(ctx), ensure_ascii=False))

    # ---------------------------
    # 1) MINIO (if enabled)
    # ---------------------------
    if spec.project.enableMinio:
        if not os.path.exists(CHART_MINIO):
            raise HTTPException(400, f"MinIO chart not found at {CHART_MINIO}")

        log.info("Step 1/3: Installing/Upgrading MinIO for release '%s' in ns '%s'", release, ns)
        minio_values_str = render("minio-values.yaml.j2", ctx)
        minio_values_path = _debug_write_yaml(f"{release}-minio-values", minio_values_str)
        log.info("000000000000000000")
        log.info(minio_values_path)
        cmd_minio = [
            "helm", "upgrade", "--install", f"{release}-minio", CHART_MINIO,
            "--namespace", ns, "--create-namespace",
            "-f", minio_values_path,
            "--wait", "--timeout", "5m0s",
        ]
        log.info("Helm (MinIO): %s", " ".join(cmd_minio))
        out_minio = run(cmd_minio)
        outputs.append(out_minio)

        log.info("MinIO installed. Sleeping 60s to allow services to stabilize…")
        time.sleep(60)

    else:
        log.info("Step 1/3: MinIO is disabled, skipping.")

    # ---------------------------
    # 2) PATRONI
    # ---------------------------
    if not os.path.exists(CHART_PATRONI):
        raise HTTPException(400, f"Patroni chart not found at {CHART_PATRONI}")

    log.info("Step 2/3: Installing/Upgrading Patroni for release '%s' in ns '%s'", release, ns)
    patroni_values_str = render("patroni-values.yaml.j2", ctx)
    patroni_values_path = _debug_write_yaml(f"{release}-patroni-values", patroni_values_str)

    cmd_patroni = [
        "helm", "upgrade", "--install", f"{release}-patroni", CHART_PATRONI,
        "--namespace", ns, "--create-namespace",
        "-f", patroni_values_path,
        "--wait", "--timeout", "10m0s",
    ]
    log.info("Helm (Patroni): %s", " ".join(cmd_patroni))
    out_patroni = run(cmd_patroni)
    outputs.append(out_patroni)

    log.info("Patroni installed. Sleeping 10s to allow endpoints to be ready…")
    time.sleep(10)

    # ---------------------------
    # 3) PGCAT (if enabled)
    # ---------------------------
    if spec.project.enablePgCat:
        if not os.path.exists(CHART_PGCAT):
            raise HTTPException(400, f"PgCat chart not found at {CHART_PGCAT}")

        log.info("Step 3/3: Installing/Upgrading PgCat for release '%s' in ns '%s'", release, ns)
        pgcat_values_str = render("pgcat-values.yaml.j2", ctx)
        pgcat_values_path = _debug_write_yaml(f"{release}-pgcat-values", pgcat_values_str)

        cmd_pgcat = [
            "helm", "upgrade", "--install", f"{release}-pgcat", CHART_PGCAT,
            "--namespace", ns, "--create-namespace",
            "-f", pgcat_values_path,
            "--wait", "--timeout", "5m0s",
        ]
        log.info("Helm (PgCat): %s", " ".join(cmd_pgcat))
        out_pgcat = run(cmd_pgcat)
        outputs.append(out_pgcat)
    else:
        log.info("Step 3/3: PgCat is disabled, skipping.")

    log.info("Deployment pipeline completed for release='%s' ns='%s'", release, ns)
    return {
        "ok": True,
        "release": release,
        "namespace": ns,
        "output": "\n\n---\n\n".join(outputs)
    }