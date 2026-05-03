import difflib
from typing import List, Dict, Any


def compare_files(content1: str, content2: str) -> Dict[str, Any]:
    lines1 = content1.splitlines()
    lines2 = content2.splitlines()

    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    diff_result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for line in lines1[i1:i2]:
                diff_result.append({
                    'type': 'equal',
                    'line_num1': i1 + diff_result.count({'type': 'equal', 'line_num1': i1}) + 1 if i1 < i2 else None,
                    'line_num2': j1 + diff_result.count({'type': 'equal', 'line_num2': j1}) + 1 if j1 < j2 else None,
                    'content': line
                })
        elif tag == 'insert':
            for line in lines2[j1:j2]:
                diff_result.append({
                    'type': 'insert',
                    'line_num1': None,
                    'line_num2': j1 + 1 + lines2[j1:j2].index(line),
                    'content': line
                })
        elif tag == 'delete':
            for line in lines1[i1:i2]:
                diff_result.append({
                    'type': 'delete',
                    'line_num1': i1 + 1 + lines1[i1:i2].index(line),
                    'line_num2': None,
                    'content': line
                })
        elif tag == 'replace':
            for line in lines1[i1:i2]:
                diff_result.append({
                    'type': 'delete',
                    'line_num1': i1 + 1 + lines1[i1:i2].index(line),
                    'line_num2': None,
                    'content': line
                })
            for line in lines2[j1:j2]:
                diff_result.append({
                    'type': 'insert',
                    'line_num1': None,
                    'line_num2': j1 + 1 + lines2[j1:j2].index(line),
                    'content': line
                })

    stats = calculate_stats(lines1, lines2, diff_result)

    return {
        'lines1': lines1,
        'lines2': lines2,
        'diff': diff_result,
        'stats': stats
    }


def calculate_stats(lines1: List[str], lines2: List[str], diff: List[Dict]) -> Dict[str, int]:
    inserted = sum(1 for item in diff if item['type'] == 'insert')
    deleted = sum(1 for item in diff if item['type'] == 'delete')
    equal = sum(1 for item in diff if item['type'] == 'equal')

    total_lines = max(len(lines1), len(lines2))
    similarity = equal / total_lines * 100 if total_lines > 0 else 0

    return {
        'total_lines1': len(lines1),
        'total_lines2': len(lines2),
        'inserted': inserted,
        'deleted': deleted,
        'equal': equal,
        'similarity': round(similarity, 2)
    }


def generate_html_diff(content1: str, content2: str) -> str:
    lines1 = content1.splitlines()
    lines2 = content2.splitlines()

    diff = difflib.HtmlDiff()
    html_result = diff.make_file(lines1, lines2, context=True, numlines=3)
    return html_result
