"""Strip account-specific data from a Make.com blueprint so it can be published.

Usage:
  python sanitize.py <exported-blueprint.json> [out.json]
  python sanitize.py --shared <share-id> [out.json]   # pull from a public share link

Removes connection IDs/labels, run samples, and Airtable/Slack IDs, and fixes
mojibake (e.g. "â€“" -> "–") left by copy-pasting text into Make.
"""
import json
import re
import sys
import urllib.request

PLACEHOLDERS = [
    (r"app[A-Za-z0-9]{14}", "appYOUR_BASE_ID"),
    (r"tbl[A-Za-z0-9]{14}", "tblYOUR_TABLE_ID"),
    (r"usr[A-Za-z0-9]{14}", "usrREDACTED"),
    (r"\bC0[A-Z0-9]{8,}\b", "YOUR_SLACK_CHANNEL_ID"),
]


def fix_mojibake(s):
    try:
        return s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def clean(node):
    if isinstance(node, dict):
        for k in ("__IMTCONN__", "makeConnectionId", "setupValidation", "samples"):
            node.pop(k, None)
        return {k: clean(v) for k, v in node.items()}
    if isinstance(node, list):
        return [clean(v) for v in node]
    if isinstance(node, str):
        node = fix_mojibake(node)
        for pat, rep in PLACEHOLDERS:
            node = re.sub(pat, rep, node)
    return node


def load(args):
    if args[0] == "--shared":
        url = f"https://eu1.make.com/api/v2/public/scenarios-shared/{args[1]}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})  # default UA gets 403
        shared = json.load(urllib.request.urlopen(req))["scenarioShared"]
        return shared["scenarioBlueprint"], args[2:]
    return json.load(open(args[0], encoding="utf-8")), args[1:]


if __name__ == "__main__":
    assert fix_mojibake("A â€“ B") == "A – B"
    assert clean({"x": "appAbCdEfGh123456", "__IMTCONN__": 1}) == {"x": "appYOUR_BASE_ID"}

    bp, rest = load(sys.argv[1:])
    out = rest[0] if rest else "blueprint.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(clean(bp), f, indent=2, ensure_ascii=False)
    print(f"Sanitized blueprint written to {out}")
