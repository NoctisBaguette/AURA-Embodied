"""Exhaustive exact comparisons; differences are evidence, never tolerance passes."""
import hashlib
import json
from pathlib import Path
import numpy as np


def compare(actual, expected):
    a, b = np.asarray(actual), np.asarray(expected)
    result = dict(actual_shape=list(a.shape), expected_shape=list(b.shape),
                  actual_dtype=str(a.dtype), expected_dtype=str(b.dtype))
    result['layout_equal'] = a.shape == b.shape and a.dtype == b.dtype
    result['exact'] = bool(result['layout_equal'] and np.array_equal(a, b))
    if a.shape != b.shape:
        return result
    result['different_elements'] = int(np.count_nonzero(a != b))
    if a.dtype.kind in 'bifu' and b.dtype.kind in 'bifu':
        result['finite'] = bool(np.isfinite(a).all() and np.isfinite(b).all())
        if result['finite'] and a.size:
            delta = a.astype(np.float64) - b.astype(np.float64)
            result.update(max_abs=float(np.abs(delta).max()),
                          mean_abs=float(np.abs(delta).mean()),
                          rmse=float(np.sqrt(np.square(delta).mean())))
            index = np.unravel_index(np.abs(delta).argmax(), a.shape)
            result['max_index'] = [int(x) for x in index]
            result['actual_at_max'] = float(a[index])
            result['expected_at_max'] = float(b[index])
    return result


def compare_sets(actual, expected):
    return {key: compare(actual[key], expected[key]) for key in sorted(set(actual) & set(expected))}


def summarize(first, second, reference):
    required = {'normalized', 'commands', 'lang_tokens', 'lang_masks', 'images', 'state', 'noise'}
    missing = {name: sorted(required - set(value)) for name, value in
               [('first', first), ('second', second), ('reference', reference)]}
    reference_cmp = compare_sets(first, reference)
    repeated_cmp = compare_sets(first, second)
    passed = (not any(missing.values()) and set(first)==set(second)
              and all(reference_cmp[k]['exact'] for k in required)
              and all(value['exact'] for value in repeated_cmp.values()))
    result = dict(status='PASS' if passed else 'MISMATCH', reference=reference_cmp,
                  same_input_repeat=repeated_cmp, missing=missing,
                  scope='Saved-request inference only; no policy rollout or tolerance relaxation')
    if (first.get('commands', np.empty(0)).shape == reference.get('commands', np.empty(0)).shape == (50,14)
            and np.isfinite(first['commands']).all() and np.isfinite(reference['commands']).all()):
        arm = [*range(6), *range(7,13)]
        delta = first['commands'].astype(np.float64) - reference['commands'].astype(np.float64)
        result['command_units'] = dict(arm_max_abs_degrees=float(np.rad2deg(np.abs(delta[:,arm]).max())),
                                      gripper_max_abs=float(np.abs(delta[:,[6,13]]).max()))
    return result


def save_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.partial')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    temp.replace(path)


def load_arrays(path):
    with np.load(path, allow_pickle=False) as values:
        return {key: values[key].copy() for key in values.files}
