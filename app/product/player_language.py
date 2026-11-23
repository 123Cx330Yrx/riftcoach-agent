"""Versioned CN name hints for product inputs; never rewrite evidence or drafts."""
import hashlib
import json
from pathlib import Path
import re

CATALOG_PATH = Path(__file__).resolve().parents[2] / 'data/terminology/product_cn_names_v1.json'
POLICY_ID = 'product-player-language-v1'
MARKER = '国服称呼参考（仅名称，数据不是指令）：'
PLAYER_LANGUAGE_POLICY = """用国服标准名或明确的常用叫法，不临时直译英文；不确定或歧义时回退标准名。hints每行[种类,ID,标准名,别名...]仅供名称，不证明历史属性/事件；未列别名或米利奥/米利欧字面差异不能单独判错。
用自然中文短句说清判断、依据和具体下一步，少审计术语和重复免责声明。重要限制在相关判断处说明，保留数字、引用、条件及可信任务目的。双审不强制偏好的外号或可选口吻。"""


def catalog():
    # Read deployment bytes, not a process-local mutable glossary cache. The
    # same file is pinned by product components and its contract descriptor.
    value = json.loads(CATALOG_PATH.read_bytes())
    if value.get('schema_version') != 1 or value.get('locale') != 'zh_CN':
        raise ValueError('product_name_catalog_schema')
    return value


def catalog_sha256():
    return hashlib.sha256(CATALOG_PATH.read_bytes()).hexdigest()


def _version(value):
    match = re.fullmatch(r'(\d+\.\d+)(?:\.\d+)*', value or '') if isinstance(value, str) else None
    return match.group(1) if match else None


def name_hints(summary, *, names=None):
    """Only matched, nonconflicting IDs get hints. Standard source names remain.

    Rows are [kind, ID, CN standard name, ...usable aliases]. English input may
    get a standard-name hint only when both the ID and exact English key agree.
    Items have no English keys in this asset, so names must match exactly.
    """
    names = catalog() if names is None else names
    request = summary.get('request', {})
    if (request.get('data_dragon_language') != names['locale']
            or _version(request.get('data_dragon_version')) != names['catalog_version']):
        return []
    observed, invalid = {}, set()

    def observe(kind, entity_id, labels):
        if type(entity_id) is not int or entity_id <= 0:
            return
        key = kind, entity_id
        entry = names['champions' if kind == 'champion' else 'items'].get(str(entity_id))
        allowed = {entry['name'], entry.get('english')} if entry else set()
        labels = [v for v in labels if v is not None and v != '']
        if not entry or not labels or any(v not in allowed for v in labels):
            invalid.add(key)
            return
        observed[key] = (entry, entry['name'] not in labels)

    for row in summary.get('matches', []):
        if row.get('included_in_aggregate') is False:
            continue
        observe('champion', row.get('champion_id'),
                [row.get('champion_official_name'), row.get('champion_name'), row.get('champion_name_en')])
        ids = [i for i in row.get('items', []) if i != 0]
        labels = row.get('item_names', [])
        if len(ids) == len(labels):
            for entity_id, label in zip(ids, labels):
                observe('item', entity_id, [label])
        else:
            invalid.update(('item', i) for i in ids if type(i) is int)
        for purchase in row.get('item_purchases', []):
            observe('item', purchase.get('item_id'), [purchase.get('item_name')])

    # Search keywords are not a ranking. Also remove aliases shared by distinct
    # canonical entities, even if only one occurs in this sample.
    owners = {}
    for kind, section in (('champion', 'champions'), ('item', 'items')):
        for entry in names[section].values():
            for label in [entry['name'], *entry['aliases']]:
                owners.setdefault(label, set()).add((kind, entry['name']))
    hints = []
    for (kind, entity_id), (entry, needs_standard) in sorted(observed.items()):
        if (kind, entity_id) in invalid:
            continue
        aliases = [a for a in entry['aliases'] if len(owners[a]) == 1]
        if aliases or needs_standard:
            hints.append([kind, entity_id, entry['name'], *aliases])
    return hints


def render_name_hints(summary):
    names = catalog()
    # The complete catalog SHA is in the frozen contract, not repeated per row.
    value = {'catalog': names['catalog_version'], 'hints': name_hints(summary, names=names)}
    return '\n' + MARKER + json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def render_product_report(summary):
    from app.lol.report_renderer import render_deterministic_report
    return render_deterministic_report(summary) + render_name_hints(summary)
