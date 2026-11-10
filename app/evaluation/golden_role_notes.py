"""Role review with nonblocking notes, not unused replacement paragraphs.

The previous role workflow remains available for exact historical replay.
This contract reduces output responsibility; it does not certify source
entailment, repair returned citations or change report acceptance rules.
"""
from dataclasses import replace

from pydantic import Field

from app.evaluation import golden_native_partitioned_tool_review as partitioned
from app.evaluation.golden_explicit_source_projection import VERSION, OLD_ADDRESS, NEW_ADDRESS, project_request
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_review import RoleReviewWorkflow

CONTRACT_ID = 'golden-role-review-notes-v1'
OLD_NOTE = '每项填写block、source_ids、explanation、suggested_correction，不得把事实错误或无法消解的歧义放入advisories。'
NEW_NOTE = ('每项填写block、source_ids、explanation，简述可读性或范围澄清建议及实际依据，'
            '不另写替换段落；不得把事实错误或无法消解的歧义放入advisories。')


class AdvisoryNote(partitioned.native.previous.Strict):
    block: int = Field(ge=1, le=64)
    source_ids: list[int] = Field(max_length=48)
    explanation: str = Field(min_length=1, max_length=700)


class RoleNoteReview(partitioned.PartitionedReview):
    advisories: list[AdvisoryNote] = Field(max_length=512)


def review_policy(previous_raw=None):
    original = partitioned._review_policy(previous_raw)
    if original.count(OLD_NOTE) != 1:
        raise ValueError('role_note_policy_contract_changed')
    return original.replace(OLD_NOTE, NEW_NOTE).replace(OLD_ADDRESS, NEW_ADDRESS)


class RoleNoteReviewWorkflow(RoleReviewWorkflow):
    @staticmethod
    def make_request(inputs, **kwargs):
        prepared = partitioned.request(inputs, **kwargs)
        if kwargs.get('accepted') is not None:
            # The existing partition adapter excludes notes before editing.
            # Real issues retain their required suggested_correction.
            return project_request(prepared, inputs)
        _, marker, data = prepared.messages[1].content.partition('[UNTRUSTED DATA]\n')
        if not marker or len(prepared.tools) != 1:
            raise ValueError('role_note_request_contract_changed')
        schema = RoleNoteReview.model_json_schema()
        header = partitioned.native.schema_notation(schema) + '\n'
        prepared = replace(prepared,
            tools=(replace(prepared.tools[0], input_schema=schema),),
            messages=(prepared.messages[0],
                replace(prepared.messages[1], content=header + marker + data), prepared.messages[2]))
        projected = project_request(prepared, inputs)
        projected = replace(projected, messages=(
            replace(projected.messages[0], content=review_policy(kwargs.get('previous_raw'))),
            *projected.messages[1:]))
        return partitioned.native.budget_check(projected)

    @staticmethod
    def validate_review(raw, inputs, *, previous_raw=None):
        value = partitioned.native.strict_json(raw)
        wire = RoleNoteReview.model_validate(value, strict=True)
        base = wire.model_dump(mode='json', exclude={'advisories'})
        payload, _, base_journal = partitioned.business.validate(
            compact(base), inputs, previous_raw=previous_raw)
        selected = []
        for number, note in enumerate(wire.advisories, 1):
            if note.block > len(inputs.source.blocks):
                raise ValueError('native_advisory_block_unknown')
            refs = partitioned.native.resolve_refs(inputs, note.source_ids, computed_layout='statistic_series')
            selected.append(dict(advisory=number, block=note.block, selected_sources=refs,
                quote=inputs.source.blocks[note.block - 1][1],
                **note.model_dump(exclude={'block', 'source_ids'})))
        journal = dict(base_journal, experiment=CONTRACT_ID,
            validator_experiment=partitioned.business.EXPERIMENT_ID,
            validator_policy_sha256=base_journal['policy_sha256'],
            policy_sha256=digest(review_policy(previous_raw)), source_projection=VERSION,
            raw=raw, raw_sha256=digest(raw), parsed_review=wire.model_dump(mode='json'),
            advisories=selected, raw_representation='tool_arguments_projection')
        return payload, wire, journal
