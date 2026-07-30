"""
Forge CLI — Fast entity & migration toolkit for EAM
====================================================

Usage:  python -m app.forge <command> [options]

Everyday workflow:
    forge sync                    Push JSON → Models → DB in one shot
    forge sync -m "add location"  … with a custom migration label

Migrations:
    forge migrate                 Apply pending migrations
    forge migrate --status        Show current revision + recent history
    forge migrate --rollback [N]  Roll back N steps (default 1)

Entity scaffolding:
    forge new-entity employee --module core
    forge new-entity employee --module core --fields "name:string,age:int"
    forge add-field employee email email
    forge update-model employee   Regenerate one model from its JSON
    forge update-model --all      Regenerate every model (force)

Info / utilities:
    forge status                  DB revision at a glance
    forge seed                    Run seed_data()
    forge console                 Python REPL with app context
"""
import argparse, asyncio, importlib, json, os, subprocess, sys
import time, itertools, threading
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
APP_DIR     = Path(__file__).parent
BACKEND_DIR = APP_DIR.parent
MODULES_DIR = APP_DIR / "modules"

# ─────────────────────────────────────────────────────────────────────────────
# UI helpers
# ─────────────────────────────────────────────────────────────────────────────
class Spinner:
    """Minimal braille-dot spinner used as a context manager."""
    def __init__(self, msg="Working"):
        self._msg = msg
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
    def _run(self):
        for c in itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
            if self._stop.is_set(): break
            sys.stdout.write(f"\r{c} {self._msg}…"); sys.stdout.flush(); time.sleep(0.08)
        sys.stdout.write("\r" + " " * 60 + "\r")
    def __enter__(self):  self._t.start(); return self
    def __exit__(self, et, ev, tb):
        self._stop.set(); self._t.join()
        print(f"{'❌' if et else '✅'} {self._msg}")

class ProgressBar:
    """Simple step-based progress bar:  Syncing [=========>    ] 3/5"""
    def __init__(self, label, total, width=30):
        self._label = label
        self._total = max(total, 1)
        self._width = width
        self._current = 0
        self._draw()
    def advance(self, detail=""):
        self._current = min(self._current + 1, self._total)
        self._draw(detail)
    def _draw(self, detail=""):
        frac = self._current / self._total
        filled = int(self._width * frac)
        bar = "=" * filled + (">" if filled < self._width else "") + " " * (self._width - filled - (1 if filled < self._width else 0))
        extra = f"  {detail}" if detail else ""
        sys.stdout.write(f"\r{self._label} [{bar}] {self._current}/{self._total}{extra}" + " " * 10)
        sys.stdout.flush()
    def finish(self, msg=""):
        self._current = self._total
        self._draw()
        sys.stdout.write("\n")
        if msg: print(msg)

def _alembic(*args, capture=False):
    """Run an Alembic CLI command as a subprocess."""
    return subprocess.run(
        ["alembic", *args], cwd=str(BACKEND_DIR), capture_output=capture, text=True,
        env={**os.environ, "PYTHONPATH": str(BACKEND_DIR)},
    )

# ─────────────────────────────────────────────────────────────────────────────
# Entity / model helpers
# ─────────────────────────────────────────────────────────────────────────────
def _find_entity_json(name):
    """Locate <name>.json across all module entity dirs."""
    for d in MODULES_DIR.iterdir():
        if not d.is_dir() or d.name.startswith(("_", ".")): continue
        if " " in d.name: continue
        edir = d / "entities"
        if not edir.exists(): continue
        for p in (edir / f"{name}.json", edir / name / f"{name}.json"):
            if p.exists(): return p
    return None

def _update_model_for_entity(name, *, force=False):
    """Regenerate a model .py from its JSON definition.

    Returns a dict with:
    - status: one of "written", "skipped", "not_found", "error"
    - written: bool
    - skipped: bool
    - reason: optional text
    """
    from app.infrastructure.metadata.model_generator import ModelGeneratorService
    json_path = _find_entity_json(name)
    if not json_path:
        return {"status": "not_found", "written": False, "skipped": False}
    model_path = json_path.parent.parent / "models" / f"{name}.py"
    # Skip if model is newer than JSON (unless forced)
    if not force and model_path.exists() and model_path.stat().st_mtime >= json_path.stat().st_mtime:
        return {"status": "skipped", "written": False, "skipped": True, "reason": "up_to_date"}
    with open(json_path) as f:
        data = json.load(f)
    result = ModelGeneratorService().update_model_file(data, json_path=json_path)
    if not result.get("success", False):
        return {
            "status": "error",
            "written": False,
            "skipped": bool(result.get("skipped", False)),
            "reason": result.get("error", "unknown"),
        }
    if result.get("skipped", False):
        return {
            "status": "skipped",
            "written": False,
            "skipped": True,
            "reason": "unchanged",
        }
    return {"status": "written", "written": True, "skipped": False}

def _collect_entity_jsons():
    """Yield (stem, path) for every entity JSON in the modules tree."""
    for d in MODULES_DIR.iterdir():
        if not d.is_dir() or d.name.startswith(("_", ".")): continue
        if " " in d.name: continue  # skip non-package dirs (e.g. display names)
        edir = d / "entities"
        if not edir.exists(): continue
        for p in edir.glob("**/*.json"):
            yield p.stem, p

def cmd_generate_types(args):
    """Generate TypeScript interfaces from entity metadata into frontend/app/types/entity-types.ts."""
    # Lazy imports — forge runs standalone so we import only what we need
    from app.core.loader import load_modules
    from app.entities import load_all_entities
    from app.meta.registry import MetaRegistry

    load_modules()
    load_all_entities()

    # TS type mapping: field_type → TypeScript type string
    TS_TYPE_MAP: dict[str, str] = {
        "string": "string", "str": "string", "text": "string",
        "textarea": "string", "richtext": "string", "rich_text": "string",
        "email": "string", "phone": "string", "url": "string",
        "password": "string", "link": "string", "select": "string",
        "multiselect": "string", "data": "string", "time": "string",
        "integer": "number", "int": "number",
        "float": "number", "number": "number",
        "currency": "number", "percent": "number",
        "decimal": "number",
        "boolean": "boolean", "bool": "boolean",
        "date": "string", "datetime": "string",
    }

    _SERVER = frozenset({
        "id", "created_at", "updated_at", "created_by",
        "last_modified_by", "workflow_state", "row_no",
    })

    def to_ts_name(entity_name: str) -> str:
        """Convert snake_case entity name to PascalCase interface name."""
        return "".join(part.capitalize() for part in entity_name.split("_"))

    lines: list[str] = [
        "// Auto-generated TypeScript types from entity metadata",
        "// Do not edit manually - run: python -m app.forge generate-types",
        "",
        "export interface BaseEntity {",
        "  id: string",
        "  created_at: string",
        "  updated_at: string",
        "}",
        "",
    ]

    entities = MetaRegistry.list_all()
    for entity_meta in sorted(entities, key=lambda e: e.name):
        iface_name = to_ts_name(entity_meta.name)
        lines.append(f"export interface {iface_name} extends BaseEntity {{")

        for field in entity_meta.fields:
            if field.name in _SERVER:
                continue
            if field.computed_from or field.readonly:
                # Keep readonly fields in read interface but mark optional
                ts_type = TS_TYPE_MAP.get(field.field_type.lower(), "unknown")
                lines.append(f"  {field.name}?: {ts_type}")
                continue

            ts_type = TS_TYPE_MAP.get(field.field_type.lower(), "unknown")
            suffix = "" if field.required else "?"
            lines.append(f"  {field.name}{suffix}: {ts_type}")

        lines.append("}")
        lines.append("")

    # Resolve output path relative to this file (backend/app/forge.py → frontend/app/types/)
    out_path = BACKEND_DIR.parent / "frontend" / "app" / "types" / "entity-types.ts"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Generated {len(entities)} TypeScript interfaces → {out_path.relative_to(BACKEND_DIR.parent)}")


# ─────────────────────────────────────────────────────────────────────────────
# SYNC  —  the single everyday command
# ─────────────────────────────────────────────────────────────────────────────
def cmd_sync(args):
    """JSON → Models → DB in one atomic pass.

    Fast path:  no model files changed  →  skip Alembic entirely  (~0.5 s)
    Slow path:  models changed          →  autogenerate + upgrade  (~3-5 s)
    """
    t0 = time.time()
    print(f"\n🚀 {datetime.now().strftime('%H:%M:%S')} | Forge Sync\n")

    # Determine total steps: models check is always 1, DB steps only if needed
    entities = list(_collect_entity_jsons())
    total_entities = len(entities)

    # Step 1 — regenerate stale models
    pb = ProgressBar("Syncing", total_entities + 2)  # +2 for check + apply
    updated = 0
    for stem, _ in entities:
        result = _update_model_for_entity(stem)
        if result.get("written"):
            updated += 1
        pb.advance(stem)

    # Step 2 — fast path: nothing changed, skip DB
    if updated == 0 and not getattr(args, "force", False):
        pb.advance("no changes")
        pb.advance("skip DB")
        pb.finish()
        dt = f"{time.time()-t0:.1f}s"
        print(f"✅ No changes — DB in sync  ({dt})")
        return

    # Step 3 — generate migration
    msg = getattr(args, "message", None) or f"sync_{datetime.now().strftime('%H%M%S')}"
    pb.advance("generate migration")
    gen = _alembic("revision", "--autogenerate", "-m", msg, capture=True)
    if gen.returncode != 0:
        if "No changes in schema detected" not in (gen.stdout or ""):
            pb.finish()
            print(f"\n❌ Autogenerate failed:\n{gen.stderr}")
            return

    # Step 4 — apply migration
    pb.advance("apply migration")
    if gen.returncode == 0:
        apply = _alembic("upgrade", "head", capture=True)
        if apply.returncode != 0:
            pb.finish()
            print(f"\n❌ Upgrade failed:\n{apply.stderr}")
            return

    pb.finish()
    dt = f"{time.time()-t0:.1f}s"
    print(f"🎉 Sync complete — {updated} model(s) updated  ({dt})")

# ─────────────────────────────────────────────────────────────────────────────
# MIGRATE  —  manual Alembic control
# ─────────────────────────────────────────────────────────────────────────────
def cmd_migrate(args):
    if args.status:
        _alembic("current")
        _alembic("history", "-v")
        return
    if args.rollback:
        n = args.rollback
        with Spinner(f"Rolling back {n} step(s)"):
            _alembic("downgrade", f"-{n}")
        return
    if args.apply_only:
        with Spinner("Applying pending migrations"):
            _alembic("upgrade", "head")
        return
    # Default: generate + apply
    msg = args.message or f"mig_{datetime.now().strftime('%H%M%S')}"
    with Spinner(f"Generate + apply: {msg}"):
        gen = _alembic("revision", "--autogenerate", "-m", msg, capture=True)
        if gen.returncode != 0:
            print(f"\n❌ Autogenerate failed:\n{gen.stderr}"); return
        _alembic("upgrade", "head")

# ─────────────────────────────────────────────────────────────────────────────
# Entity scaffolding
# ─────────────────────────────────────────────────────────────────────────────
def cmd_new_entity(args):
    from app.entities.generator import EntityGenerator
    fields = []
    if args.fields:
        for f in args.fields.split(","):
            parts = f.split(":")
            fields.append({"name": parts[0], "field_type": parts[1] if len(parts) > 1 else "string"})
    EntityGenerator().create_entity(
        {"name": args.name, "module": args.module, "fields": fields}, overwrite=args.force,
    )
    print(f"✅ Entity '{args.name}' created.  Run  forge sync  to push to DB.")

def cmd_add_field(args):
    path = _find_entity_json(args.entity)
    if not path:
        print(f"❌ Entity '{args.entity}' not found."); return
    with open(path) as f: data = json.load(f)
    data.setdefault("fields", []).append({"name": args.field_name, "field_type": args.field_type})
    with open(path, "w") as f: json.dump(data, f, indent=2)
    _update_model_for_entity(args.entity, force=True)
    print(f"✅ Field '{args.field_name}' added.  Run  forge sync  to push to DB.")

def cmd_update_model(args):
    if args.all:
        count = 0
        with Spinner("Regenerating all models"):
            for stem, _ in _collect_entity_jsons():
                result = _update_model_for_entity(stem, force=True)
                if result.get("written"):
                    count += 1
        print(f"   {count} model(s) written")
    else:
        if not args.entity:
            print("❌ Specify an entity name or use --all"); return
        result = _update_model_for_entity(args.entity, force=True)
        if result.get("status") == "written":
            print(f"✅ Model for '{args.entity}' regenerated")
        elif result.get("status") == "skipped":
            print(f"✅ Model for '{args.entity}' already up to date")
        elif result.get("status") == "not_found":
            print(f"⚠️  No JSON found for '{args.entity}'")
        else:
            print(f"❌ Model update failed for '{args.entity}': {result.get('reason', 'unknown')}")

def cmd_status(args):
    _alembic("current")

# ─────────────────────────────────────────────────────────────────────────────
# Parser & dispatch
# ─────────────────────────────────────────────────────────────────────────────
HELP_EPILOG = """\
examples:
  forge sync                          push everything to DB
  forge sync -m "add cost_code"       … with a label
  forge migrate --status              check DB revision
  forge migrate --rollback 2          undo last 2 migrations
  forge new-entity report --module reporting --fields "title:string,value:float"
  forge add-field employee phone string
  forge update-model --all            regenerate every model from JSON
  forge generate-types                sync TypeScript interfaces from entity metadata
"""

def main():
    p = argparse.ArgumentParser(
        prog="forge",
        description="Forge — Fast entity & migration toolkit for EAM",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command")

    # sync
    s = sub.add_parser("sync", help="JSON → Models → DB (everyday command)")
    s.add_argument("-m", "--message", help="migration label (auto-generated if omitted)")

    # migrate
    m = sub.add_parser("migrate", help="manual Alembic control")
    m.add_argument("-m", "--message", help="migration label")
    m.add_argument("--apply-only", action="store_true", help="only apply pending migrations")
    m.add_argument("--rollback", type=int, nargs="?", const=1, help="rollback N steps (default 1)")
    m.add_argument("--status", action="store_true", help="show current revision + history")

    # new-entity
    n = sub.add_parser("new-entity", help="scaffold a new entity")
    n.add_argument("name"); n.add_argument("--module", default="core")
    n.add_argument("--fields", help="comma-sep field:type pairs")
    n.add_argument("--force", action="store_true")

    # add-field
    a = sub.add_parser("add-field", help="add a field to an entity JSON + model")
    a.add_argument("entity"); a.add_argument("field_name"); a.add_argument("field_type")

    # update-model
    u = sub.add_parser("update-model", help="regenerate model .py from JSON")
    u.add_argument("entity", nargs="?"); u.add_argument("--all", action="store_true")

    # simple commands
    sub.add_parser("status", help="show DB revision")
    sub.add_parser("seed", help="run seed_data()")
    sub.add_parser("console", help="interactive Python REPL")
    sub.add_parser("generate-types", help="generate TypeScript interfaces from entity metadata")

    dispatch = {
        "sync": cmd_sync, "migrate": cmd_migrate, "new-entity": cmd_new_entity,
        "add-field": cmd_add_field, "update-model": cmd_update_model, "status": cmd_status,
        "seed": lambda a: asyncio.run(importlib.import_module("app.core.seed").seed_data()),
        "console": lambda a: importlib.import_module("code").interact(local={"app": importlib.import_module("app")}),
        "generate-types": cmd_generate_types,
    }

    args = p.parse_args()
    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        p.print_help()

if __name__ == "__main__":
    main()