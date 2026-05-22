def build_tree(pages: list) -> list:
    by_id = {p.id: {"page": p, "children": []} for p in pages}
    roots = []
    for item in by_id.values():
        pid = item["page"].parent_id
        if pid and pid in by_id:
            by_id[pid]["children"].append(item)
        else:
            roots.append(item)

    def sort_items(items):
        items.sort(key=lambda x: (x["page"].sort_order, x["page"].title.lower()))
        for item in items:
            sort_items(item["children"])

    sort_items(roots)
    return roots


def flatten_tree(nodes: list, level: int = 0) -> list:
    result = []
    for node in nodes:
        result.append({"page": node["page"], "level": level})
        result.extend(flatten_tree(node["children"], level + 1))
    return result
