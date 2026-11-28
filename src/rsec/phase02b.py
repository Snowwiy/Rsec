"""CLI extensions for expert curation, two-track evaluation and hardware readiness."""

from rsec.datasets.benchmark import DEFAULT_BENCH
from rsec.datasets.software import CODEBENCH, RESERVED
from rsec.utils import write_json

DATA_ACTIONS = {"preaudit", "review-ui", "review-export", "replay-plan", "semantic-check"}
BENCH_ACTIONS = {"code-validate", "code-evaluate", "response-rubric", "gold-import"}


def add_commands(commands, data, benchmark):
    prep = data.add_parser(
        "preaudit", help="Bind technical preaudit notes to the existing Phase 02 candidate hashes"
    )
    prep.add_argument("--input", nargs="+", required=True)
    prep.add_argument("--output", required=True)
    ui = data.add_parser("review-ui", help="Open the localhost candidate review UI")
    ui.add_argument("directory")
    ui.add_argument("--ledger", default="data/reviews/events")
    ui.add_argument("--port", type=int, default=8765)
    ui.add_argument("--reviewers")
    ui.add_argument("--reviewer")
    ui.add_argument("--private-key")
    ui.add_argument("--preaudit")
    review = data.add_parser(
        "review-export", help="Verify signed review events and export compatible curation decisions"
    )
    review.add_argument("directory")
    review.add_argument("--reviewers", required=True)
    review.add_argument("--ledger", default="data/reviews/events")
    review.add_argument("--import-events")
    review.add_argument("--output", required=True)
    plan = data.add_parser(
        "replay-plan", help="Freeze a train-only mixed schedule from two vetted SFT releases"
    )
    plan.add_argument("--cyber", required=True)
    plan.add_argument("--software", required=True)
    plan.add_argument("--max-rows", type=int, required=True)
    plan.add_argument("--software-share", type=float, default=0.5)
    plan.add_argument("--seed", type=int, default=42)
    plan.add_argument("--extra-reserved", nargs="*", default=[])
    plan.add_argument("--output", required=True)
    plan.add_argument(
        "--materialize",
        action="store_true",
        help="Write a trainer-compatible mixed release directory",
    )
    semantic = data.add_parser(
        "semantic-check", help="Flag possible reserved matches from local embedding exports"
    )
    semantic.add_argument("--input", nargs="+", required=True)
    semantic.add_argument("--reserved", nargs="+", default=RESERVED)
    semantic.add_argument("--vectors", required=True)
    semantic.add_argument("--threshold", type=float, required=True)
    semantic.add_argument("--output", required=True)
    code = benchmark.add_parser(
        "code-validate", help="Validate the independent CodeBench development cases"
    )
    code.add_argument("--benchmark", default=CODEBENCH)
    code_score = benchmark.add_parser(
        "code-evaluate",
        help="Score precomputed isolated unit evidence and optional quality ratings",
    )
    code_score.add_argument("--benchmark", default=CODEBENCH)
    code_score.add_argument("--predictions", nargs="+", required=True)
    code_score.add_argument("--unit-results", required=True)
    code_score.add_argument("--harness-sha256", required=True)
    code_score.add_argument("--k", type=int, nargs="+", default=[1, 5])
    code_score.add_argument("--ratings")
    code_score.add_argument("--output", required=True)
    response = benchmark.add_parser(
        "response-rubric", help="Evaluate hash-bound CyberBench responses"
    )
    response.add_argument("--benchmark", default=DEFAULT_BENCH)
    response.add_argument("--predictions", nargs="+", required=True)
    response.add_argument("--ratings", required=True)
    response.add_argument("--rubric", default="benchmarks/rsec_cyberbench/rubrics.json")
    response.add_argument("--output", required=True)
    gold = benchmark.add_parser(
        "gold-import", help="Freeze an independently adjudicated private final suite"
    )
    for key in ("cases", "authors", "reviews", "reviewers", "registry", "output"):
        gold.add_argument("--" + key, required=True)
    gold.add_argument("--reserved", nargs="*", default=[])
    gold.add_argument("--training", nargs="*", default=[])

    gpu = commands.add_parser("gpu", help="Local NVIDIA diagnostics and CUDA smoke tests")
    actions = gpu.add_subparsers(dest="action", required=True)
    actions.add_parser("list")
    diagnose = actions.add_parser("diagnose")
    diagnose.add_argument("--output")
    diagnose.add_argument("--markdown")
    validate = actions.add_parser("validate")
    validate.add_argument(
        "--mode",
        choices=["single", "nccl", "ddp", "compare", "independent", "fsdp"],
        default="single",
    )
    validate.add_argument("--device", type=int, default=0)
    validate.add_argument("--output", required=True)
    timing = actions.add_parser("benchmark")
    timing.add_argument("--device", type=int, default=0)
    timing.add_argument("--steps", type=int, default=20)
    timing.add_argument("--output")


def dispatch_data(args):
    if args.action == "preaudit":
        from rsec.datasets.preaudit import preaudit

        return preaudit(args.input, args.output)
    if args.action == "review-ui":
        from rsec.datasets.review_ui import serve

        return serve(
            args.directory,
            args.ledger,
            args.port,
            args.reviewers,
            args.reviewer,
            args.private_key,
            args.preaudit,
        )
    if args.action == "review-export":
        from rsec.datasets.review_ui import export_reviews

        return export_reviews(
            args.directory, args.reviewers, args.ledger, args.output, args.import_events
        )
    if args.action == "semantic-check":
        from rsec.datasets.semantic import semantic_review

        return semantic_review(args.input, args.reserved, args.vectors, args.threshold, args.output)
    from rsec.datasets.software import make_replay_plan, materialize_replay

    run = materialize_replay if args.materialize else make_replay_plan
    return run(
        args.cyber,
        args.software,
        args.output,
        args.max_rows,
        args.software_share,
        args.seed,
        args.extra_reserved,
    )


def dispatch_benchmark(args):
    if args.action == "code-validate":
        from rsec.datasets.software import codebench_summary

        return codebench_summary(args.benchmark)
    if args.action == "code-evaluate":
        from rsec.datasets.evidence import score_codebench

        return score_codebench(
            args.benchmark,
            args.predictions,
            args.unit_results,
            args.harness_sha256,
            args.k,
            args.output,
            args.ratings,
        )
    if args.action == "response-rubric":
        from rsec.datasets.evidence import score_cyber_ratings

        return score_cyber_ratings(
            args.benchmark, args.predictions, args.ratings, args.rubric, args.output
        )
    from rsec.datasets.gold import import_gold

    return import_gold(
        args.cases,
        args.authors,
        args.reviews,
        args.reviewers,
        args.registry,
        args.output,
        args.reserved,
        args.training,
    )


def dispatch_gpu(args):
    from rsec import gpu

    if args.action == "list":
        return {"nvidia_devices": gpu.nvidia_devices()}
    if args.action == "diagnose":
        return gpu.write_diagnostic(args.output, args.markdown)
    if args.action == "validate":
        if args.mode == "single":
            return gpu.validate_single(args.device, args.output)
        from rsec import gpu_distributed

        if args.mode == "nccl":
            return gpu_distributed.validate_nccl(args.output)
        if args.mode == "ddp":
            return gpu.validate_ddp(args.output)
        if args.mode == "fsdp":
            from rsec.gpu_fsdp import validate_fsdp

            return validate_fsdp(args.output)
        return gpu_distributed.validate_comparison(
            args.device, args.output, independent=args.mode == "independent"
        )
    result = gpu.benchmark(args.device, args.steps)
    if args.output:
        write_json(args.output, result)
    return result
