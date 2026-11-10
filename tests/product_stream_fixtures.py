"""Synthetic SSE fixtures, never described as captured provider events."""
from copy import deepcopy
from tests.test_reviewer_responses_transport import Bytes


def events_for_response(value, *, preamble=False, omit_done_name=True):
    value = deepcopy(value)
    base = dict(value, output=[], usage=None, status='in_progress')
    rows = []
    if preamble:
        prefix = dict(base, id='' if preamble == 'anonymous' else 'relay-placeholder', status='queued')
        rows += [dict(type='response.created',response=prefix),dict(type='response.queued',response=prefix)]
    rows += [dict(type='response.created',response=base),dict(type='response.in_progress',response=base)]
    for index,item in enumerate(value['output']):
        item.setdefault('id',f'item-{index}')
        added = deepcopy(item)
        if item['type']=='function_call':
            item.setdefault('call_id',f'call-{index}')
            added = dict(item,arguments='',status='in_progress')
        rows.append(dict(type='response.output_item.added',output_index=index,item=added))
        if item['type']=='function_call':
            raw=item['arguments']
            rows += [dict(type='response.function_call_arguments.delta',output_index=index,item_id=item['id'],delta=part)
                     for part in (raw[:len(raw)//2],raw[len(raw)//2:])]
            done=dict(type='response.function_call_arguments.done',output_index=index,item_id=item['id'],arguments=raw)
            if not omit_done_name:done['name']=item['name']
            rows.append(done)
        rows.append(dict(type='response.output_item.done',output_index=index,item=item))
    rows.append(dict(type='response.'+value['status'],response=value))
    return [dict(row,sequence_number=i-2 if preamble and i>=2 else i) for i,row in enumerate(rows)]
