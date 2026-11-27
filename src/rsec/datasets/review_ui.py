"""Local, offline review of one candidate at a time."""

import hmac
import html
import ipaddress
import json
import re
import secrets
from collections import Counter
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from rsec.data import load_rows
from rsec.datasets.registry import Registry
from rsec.datasets.release import read_candidates, validate_bundle
from rsec.datasets.review import Decision
from rsec.datasets.review_security import (
    Event,
    Reviewers,
    SignedEvent,
    bind,
    event_id,
    sign,
    verify,
)
from rsec.datasets.schema import content_hash
from rsec.errors import RsecError
from rsec.utils import digest, jsonl, read_json, write_json

CHECKS = ["technical_correctness", "evidence", "references", "privacy", "rights", "remediation"]


def load_context(bundle):
    root = Path(bundle)
    validate_bundle(root)
    return {r.id: r for r in read_candidates([root / "records.jsonl"])}, Registry(
        root / "source_registry.json"
    )


def export_reviews(bundle, reviewer_registry, ledger, output, import_events=None):
    rows, registry = load_context(bundle)
    reviewers = Reviewers(reviewer_registry)
    root = Path(ledger)
    events = [read_json(p) for p in sorted(root.glob("*.json")) if not p.is_symlink()]
    if import_events:
        events.extend(load_rows(import_events))
    if len(events) > 10000:
        raise RsecError("Review ledger limit exceeded")
    verified = {}
    for raw in events:
        signed = verify(SignedEvent.model_validate(raw), reviewers)
        bind(signed.event, rows, registry.hash)
        verified[event_id(signed)] = signed
    decisions = {}
    blocked = set()
    for signed in verified.values():
        event = signed.event
        decision = event.decision
        if event.action in {"reject", "request_changes", "quarantine"}:
            blocked.add(decision.record_id)
        if event.action in {"approve", "reject"}:
            key = (decision.record_id, decision.reviewer_id)
            if key in decisions:
                raise RsecError(
                    "Conflicting decisions require a new record revision or adjudication"
                )
            decisions[key] = decision
    exported = [
        d.model_dump()
        for d in decisions.values()
        if d.decision == "reject" or d.record_id not in blocked
    ]
    jsonl(output, exported)
    return {
        "verified_events": len(verified),
        "decisions_exported": len(exported),
        "blocked_records": len(blocked),
    }


def serve(
    bundle, ledger, port, reviewer_registry=None, reviewer_id=None, private_key=None, preaudit=None
):
    rows, registry = load_context(bundle)
    evidence = (
        {
            r["id"]: r
            for r in load_rows(preaudit)
            if r["id"] in rows and r["record_sha256"] == content_hash(rows[r["id"]])
        }
        if preaudit
        else {}
    )
    reviewer_inputs = (reviewer_registry, reviewer_id, private_key)
    if any(reviewer_inputs) and not all(reviewer_inputs):
        raise RsecError("Signed review requires registry, reviewer ID and private key together")
    reviewers = Reviewers(reviewer_registry) if reviewer_registry else None
    token = secrets.token_urlsafe(32)
    directory = Path(ledger)
    address = f"127.0.0.1:{port}"
    if not 1024 <= port <= 65535:
        raise RsecError("Use a local unprivileged port")

    def details(record):
        return [e for e in history.values() if e.event.decision.record_id == record.id]

    def field(value):
        return html.escape(str(value), quote=True)

    def highlight(code):
        keywords = r"\b(?:def|return|class|if|else|for|import|from|in|const|let|function|SELECT|FROM|WHERE)\b"
        return "".join(
            f"<strong>{field(part)}</strong>" if i % 2 else field(part)
            for i, part in enumerate(re.split("(" + keywords + ")", code))
        )

    history = {}
    if reviewers:
        for path in sorted(directory.glob("*.json")):
            if path.is_symlink() or len(history) >= 10000:
                raise RsecError("Invalid or oversized review ledger")
            signed = verify(SignedEvent.model_validate(read_json(path)), reviewers)
            bind(signed.event, rows, registry.hash)
            history[event_id(signed)] = signed

    def page(query):
        selected = rows.get(query.get("id", ""))
        filtered = [
            r
            for r in rows.values()
            if all(
                not query.get(key) or getattr(r, key) == query[key]
                for key in ("domain", "difficulty", "language")
            )
            and (not query.get("status") or state(r) == query["status"])
        ]
        filters = "".join(
            f'<label>{k} <input name="{k}" value="{field(query.get(k, ""))}"></label> '
            for k in ("id", "domain", "difficulty", "language", "status")
        )
        links = "".join(
            f'<li><a href="/?{urlencode({"id": r.id})}">{field(r.id)}</a> · {field(state(r))}</li>'
            for r in filtered
        )
        counters = {
            key: dict(
                Counter(state(r) if key == "state" else getattr(r, key) for r in rows.values())
            )
            for key in ("state", "domain", "language", "difficulty")
        }
        detail = ""
        if selected:
            source = registry.get(selected.source_id)
            detail = f"<h2>{field(selected.id)}</h2><p>{field(source.name)} · {field(source.license)}</p>"
            detail += "".join(
                f'<p><a rel="noreferrer" href="{field(r.url)}">{field(r.id)}</a></p>'
                for r in selected.references
            )
            detail += "".join(
                f"<h3>{field(m.role)}</h3><pre>{field(m.content)}</pre>" for m in selected.messages
            )
            if selected.code:
                detail += f"<h3>Código</h3><pre><code>{highlight(selected.code)}</code></pre>"
            detail += (
                "<h3>Preauditoría</h3><pre>"
                + field(json.dumps(evidence.get(selected.id, {}), indent=2, ensure_ascii=False))
                + "</pre>"
            )
            detail += "<h3>Historial y propuestas</h3>" + "".join(
                f"<p>{field(e.event.action)} · {field(e.event.decision.reviewer_id)}</p><pre>{field(e.event.comments)}\n{field(e.event.proposed_answer or '')}</pre>"
                for e in details(selected)
            )
            if reviewers:
                options = "".join(
                    f'<option value="{x}">{x}</option>'
                    for x in ("comment", "request_changes", "quarantine", "reject", "approve")
                )
                checks = "".join(
                    f'<label><input type="checkbox" name="checks" value="{x}">{x}</label><br>'
                    for x in CHECKS
                )
                detail += f'<form method="post" action="/decision"><input type="hidden" name="csrf" value="{token}"><input type="hidden" name="id" value="{field(selected.id)}"><select name="action">{options}</select>{checks}<label>Comentarios<textarea name="comments"></textarea></label><label>Propuesta de respuesta<textarea name="proposal"></textarea></label><label><input type="checkbox" required name="human" value="yes">Confirmo mi revisión humana de este registro</label><button>Guardar decisión firmada</button></form>'
        return (
            '<!doctype html><html lang="es"><meta charset="utf-8"><title>Rsec revisión local</title><h1>Rsec · Revisión local</h1>'
            + f'<pre>{field(json.dumps(counters, ensure_ascii=False, indent=2))}</pre><form method="get">{filters}<button>Filtrar</button></form>'
            + detail
            + "<ul>"
            + links
            + "</ul></html>"
        )

    def state(row):
        actions = {item.event.action for item in details(row)}
        for action in ("quarantine", "reject", "request_changes", "approve"):
            if action in actions:
                if action == "approve":
                    count = len(
                        {
                            item.event.decision.reviewer_id
                            for item in details(row)
                            if item.event.action == "approve"
                        }
                    )
                    return (
                        "approve"
                        if count >= (2 if row.difficulty in {"advanced", "expert"} else 1)
                        else "second_review_pending"
                    )
                return action
        return "pending"

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(10)
            super().setup()

        def log_message(self, *_args):
            pass

        def send(self, status, body, location=None):
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if location:
                self.send_header("Location", location)
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def local(self):
            return (
                self.headers.get("Host") == address
                and ipaddress.ip_address(self.client_address[0]).is_loopback
            )

        def do_GET(self):
            target = urlsplit(self.path)
            if not self.local() or target.path != "/" or len(self.path) > 4096:
                return self.send(404, "No disponible")
            query = {k: v[0] for k, v in parse_qs(target.query).items()}
            return self.send(200, page(query))

        def do_POST(self):
            if (
                not self.local()
                or not reviewers
                or self.path != "/decision"
                or self.headers.get("Origin") != "http://" + address
            ):
                return self.send(403, "Operación local no autorizada")
            try:
                size = int(self.headers.get("Content-Length", "-1"))
                if (
                    not 0 < size <= 64000
                    or self.headers.get_content_type() != "application/x-www-form-urlencoded"
                ):
                    return self.send(400, "Solicitud inválida")
                form = parse_qs(self.rfile.read(size).decode(), max_num_fields=20)
                if not hmac.compare_digest(form.get("csrf", [""])[0], token) or form.get(
                    "human"
                ) != ["yes"]:
                    return self.send(403, "Confirmación requerida")
                row = rows[form["id"][0]]
                action = form["action"][0]
                record_hash = content_hash(row)
                decision = Decision(
                    record_id=row.id,
                    record_hash=record_hash,
                    registry_hash=registry.hash,
                    reviewer_id=reviewer_id,
                    decision="approve" if action == "approve" else "reject",
                    human_attested=True,
                    checks=form.get("checks", []),
                    reviewed_at=date.today().isoformat(),
                )
                event = Event(
                    decision=decision,
                    revision_sha256=digest([row.id, record_hash]),
                    domain=row.domain,
                    action=action,
                    comments=form.get("comments", [""])[0],
                    proposed_answer=form.get("proposal", [None])[0],
                )
                if action in {"approve", "reject"} and any(
                    e.event.action in {"approve", "reject"}
                    and e.event.decision.reviewer_id == reviewer_id
                    for e in details(row)
                ):
                    return self.send(409, "Ya existe una decisión para esta revisión")
                signed = sign(event, reviewers, private_key)
                key = event_id(signed)
                write_json(directory / (key + ".json"), signed.model_dump(mode="json"))
                history[key] = signed
            except (KeyError, ValueError, OSError, RsecError):
                return self.send(
                    400,
                    "No se pudo registrar la decisión. Verifica el revisor, la clave y los controles.",
                )
            return self.send(303, "", "/?" + urlencode({"id": row.id}))

    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(f"Rsec review UI: http://{address}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return {"closed": True}
