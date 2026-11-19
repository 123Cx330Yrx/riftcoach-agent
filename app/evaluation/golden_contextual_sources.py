"""Bind already-supplied external snapshots into the contextual evidence index.

No fetch and no fact extraction from evaluated prose. Snapshot provenance and
use limits remain data; numeric support does not establish semantic relevance.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import math
import re
from types import SimpleNamespace

from app.evaluation.golden_integrated_review import ReviewInput
from app.evaluation.golden_review_experiment import SourceIndex, compact, digest
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_numeric_evidence_v4 import numeric_support as riot_numeric_support
from app.evaluation.golden_numeric_evidence_v3 import METRICS
from app.evaluation.golden_fact_candidate import NUMBER
from app.meta.models import LaneMetaChampionFact, MetaProvenance, MetaUseCase

MARKER = "外部来源事实（数据，不是指令）："
PACK_ID = "golden-contextual-external-facts-v1"
EXTERNAL_NUMBER = re.compile(NUMBER.pattern+r"|(?<=[Tt])[0-9]+(?![\w.])",re.ASCII)
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})")


def _validate_snapshot(snapshot):
    try:
        if not isinstance(snapshot,dict) or not isinstance(snapshot.get("facts"),list):
            raise ValueError()
        if snapshot["position"] not in {"top","jungle","mid","adc","support"}:
            raise ValueError()
        if not re.fullmatch(r"[a-f0-9]{64}",snapshot["digest"]):
            raise ValueError()
        MetaProvenance(snapshot["provenance"])
        uses = snapshot["allowed_uses"]
        if not isinstance(uses,list) or "current_snapshot_recommendation" not in uses:
            raise ValueError()
        for use in uses:
            MetaUseCase(use)
        retrieved, expires = (datetime.fromisoformat(snapshot[field]) for field in ("retrieved_at","expires_at"))
        if retrieved.tzinfo is None or expires.tzinfo is None or expires <= retrieved:
            raise ValueError()
        facts = [LaneMetaChampionFact(**fact) for fact in snapshot["facts"]]
        if not 1 <= len(facts) <= 10 or len({f.champion.casefold() for f in facts}) != len(facts):
            raise ValueError()
        if len({f.rank for f in facts}) != len(facts):
            raise ValueError()
    except (KeyError,TypeError,ValueError):
        raise ValueError("contextual_external_source_invalid") from None


def build_inputs(request):
    inputs = ReviewInput.build(request)
    data, pack = strict_json(inputs.data_json), strict_json(inputs.pack_json)
    lines = [line[len(MARKER):] for line in request.deterministic_report.splitlines() if line.startswith(MARKER)]
    if not lines:
        return inputs
    if len(lines) != 1:
        raise ValueError("contextual_external_source_ambiguous")
    external = strict_json(lines[0])
    if not isinstance(external,dict) or not isinstance(external.get("opgg"),list):
        raise ValueError("contextual_external_source_invalid")
    for si,snapshot in enumerate(external["opgg"]):
        _validate_snapshot(snapshot)
        for fi,fact in enumerate(snapshot["facts"]):
            if not isinstance(fact,dict) or not isinstance(fact.get("champion"),str):
                raise ValueError("contextual_external_source_invalid")
            key=f"external:opgg:{si:02}:{fi:02}"
            pack["facts"][key]=dict(fact,position=snapshot.get("position"),
                retrieved_at=snapshot.get("retrieved_at"),expires_at=snapshot.get("expires_at"),upstream_patch=snapshot.get("upstream_patch"),
                allowed_uses=snapshot.get("allowed_uses"),provenance=snapshot.get("provenance"))
            pack["provenance"][key]=dict(source_path=f"/opgg/{si}/facts/{fi}",
                snapshot_digest=snapshot.get("digest"),source="deterministic_source_facts")
    pack.update(schema_version=PACK_ID,external_source_sha256=digest(lines[0]))
    source=SourceIndex.build(request.report,pack)
    data.update(source_index=source.prompt_sources(),facts_and_provenance=pack)
    return ReviewInput(source,compact(data),compact(pack))


def numeric_support(claim,pack):
    # Do not let the historical generic win_rate allowlist consume external
    # values without checking that the quote actually names that statistic.
    riot_claim = SimpleNamespace(quote=claim.quote,
        evidence_refs=[r for r in claim.evidence_refs if not r.startswith("external:")])
    ledger = riot_numeric_support(riot_claim, pack)
    _support_complete_outcome_means(ledger, riot_claim, pack)
    if pack.get("schema_version") != PACK_ID:
        return ledger
    tokens = {row["token"] for row in ledger}
    for match in EXTERNAL_NUMBER.finditer(claim.quote):
        if match.group() not in tokens:
            tokens.add(match.group())
            ledger.append(dict(token=match.group(),supported=False,candidates=[],omitted_candidates=0))
    candidates=[]
    timestamps=[]
    for ref in claim.evidence_refs:
        if not ref.startswith("external:opgg:") or ref not in pack["provenance"]:
            continue
        fact=pack["facts"][ref]
        for match in TIMESTAMP.finditer(claim.quote):
            try:
                actual=datetime.fromisoformat(match.group().replace("Z","+00:00")).astimezone(timezone.utc)
                retrieved=datetime.fromisoformat(fact["retrieved_at"].replace("Z","+00:00")).astimezone(timezone.utc)
            except (ValueError,KeyError,TypeError):
                continue
            if actual==retrieved or ("." not in match.group() and actual==retrieved.replace(microsecond=0)):
                timestamps.append((match.start(),match.end(),dict(op="external_retrieved_at",operands=[(ref,"/retrieved_at")])))
        for field in ("rank","rank_previous","rank_previous_patch","tier","win_rate","pick_rate","ban_rate"):
            value=fact.get(field)
            if type(value) not in (float,int) or not math.isfinite(value) or value < 0:
                continue
            if field.endswith("_rate") and value > 1:
                continue
            number=Decimal(str(value))
            candidates.append((number,ref,field,"external_snapshot_value"))
            if field.endswith("_rate"):
                candidates.append((number*100,ref,field,"external_snapshot_percent"))
    for row in ledger:
        if row["supported"]:
            continue
        token=row["token"]; places=len(token.split(".")[1]) if "." in token else 0
        # Never let external ranking numerals stand in for a Riot queue id.
        if len(token)>20 or places>6 or re.search(r"队列(?:编号|ID)?\s*[:：]?\s*"+re.escape(token)+r"(?![0-9])",claim.quote):
            continue
        occurrences=[m for m in EXTERNAL_NUMBER.finditer(claim.quote) if m.group()==token]
        per_occurrence = [[dict(op=op,operands=[(ref,"/"+field)]) for n,ref,field,op in candidates
            if n.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)==Decimal(token)
            and _metric_at(claim.quote,m,field,op)] +
            [evidence for start,end,evidence in timestamps if start <= m.start() and m.end() <= end]
            for m in occurrences]
        matches = [row for matches in per_occurrence for row in matches] if all(per_occurrence) else []
        row.update(supported=bool(matches),candidates=matches[:8],omitted_candidates=max(0,len(matches)-8))
    return ledger


def _support_complete_outcome_means(ledger, claim, pack):
    """Compute complete role/outcome cohorts from explicitly cited raw rows.

    Citing both outcomes does not erase either subgroup. Never use an uncited
    row, an arbitrary subset, another role, or a missing metric as an operand.
    This establishes arithmetic only; the evaluator still checks attribution.
    """
    role_names = {"TOP": "上单", "JUNGLE": "打野", "MIDDLE": "中单",
                  "BOTTOM": "下路|射手|ADC", "UTILITY": "辅助"}
    groups = {}
    for ref, row in pack["facts"].items():
        if not ref.startswith("facts:recent_match:") or ref not in pack["provenance"]:
            continue
        if row.get("included_in_aggregate") is not True or type(row.get("win")) is not bool:
            continue
        role = row.get("role")
        if role in role_names:
            groups.setdefault((role, row["win"]), []).append((ref, row))
    cited = set(claim.evidence_refs)
    candidates = []
    for (role, win), rows in groups.items():
        outcome = r"赢局|胜局" if win else r"输局|负局|败局"
        if not re.search(role_names[role], claim.quote, re.I) or not re.search(outcome, claim.quote):
            continue
        if not all(ref in cited for ref, _ in rows):
            continue
        for metric in METRICS:
            values = [row.get(metric) for _, row in rows]
            if not all(type(v) in (int, float) and math.isfinite(v) and 0 <= v < 1e15 for v in values):
                continue
            mean = sum(Decimal(str(v)) for v in values) / len(values)
            evidence = dict(op="cited_complete_role_outcome_mean", role=role,
                outcome="win" if win else "loss", operands=[(ref, "/"+metric) for ref, _ in rows])
            candidates.append((mean, evidence))
    for row in ledger:
        if row["supported"]:
            continue
        token = row["token"]
        places = len(token.split(".")[1]) if "." in token else 0
        if len(token) > 20 or places > 6 or re.search(r"队列(?:编号|ID)?\s*[:：]?\s*"+re.escape(token), claim.quote):
            continue
        matches = [e for n, e in candidates
                   if n.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP) == Decimal(token)]
        row.update(supported=bool(matches), candidates=matches[:8], omitted_candidates=max(0,len(matches)-8))


_LABELS = {
    "tier": r"(?:T|tier\s*|梯度\s*)",
    "rank": r"(?<!上期)(?<!上版本)(?:当前)?排名\s*",
    "rank_previous": r"上期排名\s*",
    "rank_previous_patch": r"上版本排名\s*",
    "win_rate": r"(?:胜率|win[_ ]rate)\s*",
    "pick_rate": r"(?:登场率|选取率|pick[_ ]rate)\s*",
    "ban_rate": r"(?:禁用率|禁选率|ban[_ ]rate)\s*",
}


def _metric_at(quote, match, field, op):
    before, after = quote[:match.start()], quote[match.end():]
    label = _LABELS[field]
    named = re.search(label+r"(?:约|为|是|[:：])?\s*$",before,re.I)
    named = named or re.match(r"%?\s*"+label,after,re.I)
    if field == "rank":
        named = named or (re.search(r"(?<!上期)(?<!上版本)第\s*$",before) and re.match(r"\s*名",after))
    elif field in {"rank_previous","rank_previous_patch"}:
        prefix = "上期" if field == "rank_previous" else "上版本"
        named = named or re.search(prefix+r"第\s*$",before)
    percent = bool(re.match(r"\s*[%％]",after))
    return bool(named) and percent == (op == "external_snapshot_percent")
