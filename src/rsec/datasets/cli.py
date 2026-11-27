"""Additional dataset commands; legacy CLI dispatch remains intact."""

from pathlib import Path

from rsec.datasets.benchmark import DEFAULT_BENCH
from rsec.datasets.software import RESERVED
from rsec.errors import RsecError
from rsec.utils import read_json, write_json


def add_commands(commands, ds, download):
    download.add_argument(
        "--registered",
        action="store_true",
        help="Acquire only registry-approved pinned small snapshots",
    )
    sources = ds.add_parser("sources", help="List source permissions separately from public access")
    sources.add_argument("--registry", default="data/manifests/source_registry.json")
    pilot = ds.add_parser("pilot", help="Generate deterministic pending-review fixture candidates")
    pilot.add_argument("--output", required=True)
    pilot.add_argument("--benchmark", action="store_true")
    curate = ds.add_parser("curate", help="Build an immutable phase-02 curation bundle")
    curate.add_argument("--input", nargs="+", required=True)
    curate.add_argument("--output", required=True)
    curate.add_argument("--version", required=True)
    curate.add_argument("--registry", default="data/manifests/source_registry.json")
    curate.add_argument("--taxonomy", default="configs/taxonomy.json")
    curate.add_argument("--reserved", nargs="+", default=RESERVED)
    curate.add_argument("--decisions")
    curate.add_argument("--seed", type=int, default=42)
    curate.add_argument("--anonymize", action="store_true")
    for action in ("quality", "quarantine", "version"):
        p = ds.add_parser(action, help="Inspect a hash-verified curation " + action + " report")
        p.add_argument("directory")
    stats = ds.add_parser(
        "stats", help="Inspect whitespace or measure local-tokenizer sequence lengths"
    )
    stats.add_argument("directory")
    stats.add_argument("--tokenizer")
    stats.add_argument("--output")
    split = ds.add_parser(
        "split", help="Export an expert-reviewed curation as compatible SFT train/eval/test"
    )
    split.add_argument("directory")
    split.add_argument("--output", required=True)
    review = ds.add_parser(
        "review", help="Create a hash-bound review packet; does not approve records"
    )
    review.add_argument("directory")
    review.add_argument("--output", required=True)
    knowledge = ds.add_parser(
        "normalize-cve",
        help="Normalize only locally acquired, hash-pinned CVE records as knowledge",
    )
    knowledge.add_argument("--input", nargs="+", required=True)
    knowledge.add_argument("--output", required=True)
    bench = commands.add_parser(
        "benchmark", help="Validate CyberBench development candidates and reservations"
    )
    bs = bench.add_subparsers(dest="action", required=True)
    for action in ("list", "validate"):
        p = bs.add_parser(action)
        p.add_argument("--benchmark", default=DEFAULT_BENCH)
    export = bs.add_parser("export")
    export.add_argument("--benchmark", default=DEFAULT_BENCH)
    export.add_argument("--output", required=True)
    rating = bs.add_parser("rubric-score")
    rating.add_argument("--benchmark", default=DEFAULT_BENCH)
    rating.add_argument("--ratings", required=True)
    rating.add_argument("--output", required=True)
    check = bs.add_parser("contamination-check")
    check.add_argument("--input", nargs="+", required=True)
    check.add_argument("--reserved", nargs="+", default=RESERVED)
    ev = bs.add_parser("evaluate")
    ev.add_argument("--benchmark", default=DEFAULT_BENCH)
    ev.add_argument("--predictions", required=True)
    ev.add_argument("--output", required=True)
    from rsec.phase02b import add_commands as add_phase02b_commands

    add_phase02b_commands(commands, ds, bs)


def dispatch_data(args):
    from rsec.data import load_rows
    from rsec.datasets.registry import Registry, acquire_registry
    from rsec.datasets.release import export_sft, read_candidates, validate_bundle

    if args.action == "sources":
        return Registry(args.registry).summary()
    if args.action == "download" and args.registered:
        return acquire_registry(args.config, args.output)
    if args.action == "pilot":
        from rsec.datasets.pilot import generate

        return generate(args.output, args.benchmark)
    if args.action == "normalize-cve":
        from rsec.datasets.knowledge import normalize_cve

        return normalize_cve(args.input, args.output)
    if args.action == "curate":
        from rsec.datasets.release import curate

        return curate(
            args.input,
            args.output,
            args.version,
            args.registry,
            args.taxonomy,
            args.reserved,
            args.decisions,
            args.seed,
            args.anonymize,
        )
    result = validate_bundle(args.directory)
    root = Path(args.directory)
    if args.action == "validate":
        return result
    if args.action in {"quality", "quarantine", "version"}:
        return (
            read_json(
                root
                / ("quality_report.json" if args.action == "quality" else "release_status.json")
            )
            if args.action != "quarantine"
            else {"rejected_records": list(load_rows(root / "quarantine.jsonl"))}
        )
    rows = read_candidates([root / "records.jsonl"])
    if args.action == "stats":
        from rsec.datasets.stats import statistics

        report = statistics(rows, args.tokenizer)
        if args.output:
            write_json(args.output, report)
        return report
    if args.action == "review":
        from rsec.datasets.schema import content_hash

        registry = Registry(root / "source_registry.json")
        packet = {
            "registry_hash": registry.hash,
            "instructions": "A human expert must inspect content and references, then submit explicit decisions to data curate --decisions. Packet creation does not approve anything.",
            "records": [
                {
                    "id": r.id,
                    "record_hash": content_hash(r),
                    "domain": r.domain,
                    "difficulty": r.difficulty,
                    "required_reviewers": 2 if r.difficulty in {"advanced", "expert"} else 1,
                }
                for r in rows
            ],
            "required_checks": [
                "technical_correctness",
                "evidence",
                "references",
                "privacy",
                "rights",
            ],
            "decision_schema": "rsec.datasets.review.Decision; reviewer_id is an opaque identifier, not personal data",
        }
        write_json(args.output, packet)
        return {"output": args.output, "records": len(rows), "approved": 0}
    if args.action == "split":
        from rsec.datasets.review import apply_decisions

        registry = Registry(root / "source_registry.json")
        decisions = list(load_rows(root / "reviews.jsonl"))
        apply_decisions(rows, decisions, registry.hash)
        eligible = [r for r in rows if r.purpose == "sft" and r.review.status == "EXPERT REVIEWED"]
        if not eligible:
            raise RsecError("SFT split blocked: no expert-approved examples")
        from rsec.datasets.release import read_reserved

        export_sft(
            eligible,
            args.output,
            registry,
            decisions,
            read_json(root / "taxonomy.json"),
            read_json(root / "curation_manifest.json")["seed"],
            read_reserved([root / "reserved.jsonl"]),
        )
        return {"output": args.output, "sft_records": len(eligible)}
    raise RsecError("Unknown dataset engineering command")


def dispatch_benchmark(args):
    from rsec.datasets.benchmark import check_contamination, evaluate_benchmark, validate

    if args.action == "export":
        from rsec.datasets.benchmark import export_cases

        return export_cases(args.output, args.benchmark)
    if args.action == "rubric-score":
        from rsec.datasets.benchmark import score_rubrics

        return score_rubrics(args.ratings, args.output, args.benchmark)
    if args.action == "contamination-check":
        return check_contamination(args.input, args.reserved)
    if args.action == "evaluate":
        return evaluate_benchmark(args.predictions, args.output, args.benchmark)
    return validate(args.benchmark)
