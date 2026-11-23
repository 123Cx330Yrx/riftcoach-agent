"""Independently selectable generation context for the offline Chat compiler."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

from app.agent.context import ContextTrust
from app.product import sol_chat_contract as base
from app.product.player_language import PLAYER_LANGUAGE_POLICY
from app.product.review_purpose import ProductContextBuilder

VERSION = 'product-generation-player-wording-v2'
MANIFEST = base.ROOT / 'examples/runtime_profiles/sol_product_wording_v2/generation.json'
WORDING = '用中文短句说判断、依据和下一步。就地说清缺什么、不能断言什么，不堆状态码或重复声明；保留数字、引用、条件及任务目的。双审不强求外号或口吻。'


def generation_policy():
    parent = base.CONTRACT.context_policy
    names, separator, _ = PLAYER_LANGUAGE_POLICY.partition('\n')
    if not separator or not parent.endswith(PLAYER_LANGUAGE_POLICY):
        raise ValueError('wording_parent_policy_mismatch')
    return parent.removesuffix(PLAYER_LANGUAGE_POLICY) + names + '\n' + WORDING


def descriptor():
    manifest = base.ASSETS / 'prompt_programs/recent-form-review/manifest.json'
    return {'version': VERSION, 'scope': 'offline_generation_only',
            'parent_contract': base.CONTRACT.snapshot().model_dump(mode='json'),
            'parent_program_sha256': json.loads(manifest.read_bytes())['program_sha256'],
            'implementation_sha256': sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
            'generation_policy_sha256': sha256(generation_policy().encode()).hexdigest()}


class PlayerWordingContextBuilder(ProductContextBuilder):
    def __init__(self, *, purpose):
        if json.loads(MANIFEST.read_bytes()) != descriptor():
            raise ValueError('wording_component_drift')
        super().__init__(coach_contract=base.CONTRACT, compact_json=True, purpose=purpose)

    def _select_sections(self, sections, max_context_tokens):
        matches = [i for i, row in enumerate(sections) if row.section_id == 'candidate:policy_addendum']
        if len(matches) != 1:
            raise ValueError('wording_policy_section_count')
        i = matches[0]
        row = sections[i]
        if not row.required or row.trust != ContextTrust.INTERNAL_POLICY or row.content != base.CONTRACT.context_policy:
            raise ValueError('wording_parent_section_mismatch')
        updated = (*sections[:i], replace(row, content=generation_policy()), *sections[i+1:])
        return super()._select_sections(updated, max_context_tokens)
