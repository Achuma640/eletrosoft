#!/usr/bin/env python3
"""Build the PIN-locked members page from the Sheet export.
Usage: ES_PIN=.... python3 tools/build.py SHEET_DIR [--check]
Reads loans.json, payments.json, shareholders.json (from fetch_sheet.py), encrypts the
payload into index.html (var ENC=...). The page itself does all the loan arithmetic."""
import base64, datetime, json, os, re, sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

N = 600000
PAGE = os.path.join(os.path.dirname(__file__), "..", "index.html")
src = sys.argv[1]
rows = lambda f: json.load(open(os.path.join(src, f)))["values"][1:]
num = lambda v: float(str(v).replace(",", "")) if str(v).strip() not in ("", "-") else 0.0

def month(v):
    s = str(v).strip().lstrip("'")
    if re.fullmatch(r"\d{4}-\d{2}", s): return s
    if re.fullmatch(r"\d+(\.\d+)?", s):  # a Sheets date serial
        d = datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(s)))
        return d.strftime("%Y-%m")
    raise SystemExit("Unreadable month: %r" % v)

def date(v):
    s = str(v).strip()
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(s)))).isoformat()
    d, m, y = re.split(r"[/.-]", s); return "%04d-%02d-%02d" % (int(y), int(m), int(d))

loans, idx = [], {}
for r in rows("loans.json"):
    r = r + [""] * (11 - len(r))
    if not r[0]: continue
    L = dict(id=str(r[0]), sheet=str(r[1]), name=str(r[2]).strip(), no=int(num(r[3])), date=date(r[4]),
             P=num(r[5]), n=int(num(r[6])), I=num(r[7]), first=month(r[10]), pay={}, pen={})
    idx[L["id"]] = L; loans.append(L)
for r in rows("payments.json"):
    r = r + [""] * (6 - len(r))
    if not r[0]: continue
    if r[0] not in idx: raise SystemExit("Payment for unknown loan ID %r" % r[0])
    L, m = idx[r[0]], month(r[2])
    if num(r[3]): L["pay"][m] = L["pay"].get(m, 0) + num(r[3])
    if num(r[4]): L["pen"][m] = L["pen"].get(m, 0) + num(r[4])
shares = [[str(r[0]).strip(), num(r[1])] for r in rows("shareholders.json") if len(r) > 1 and str(r[0]).strip() and num(r[1]) > 0]
settings = {}
if os.path.exists(os.path.join(src, "settings.json")):
    for r in rows("settings.json"):
        if len(r) > 1 and str(r[0]).strip() and str(r[1]).strip():
            settings[str(r[0]).strip()] = r[1]
now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
payload = {"loans": loans, "shares": shares, "settings": settings, "built": now.strftime("%-d %b %Y %H:%M")}
print(len(loans), "loans,", sum(len(l["pay"]) for l in loans), "payment months,", len(shares), "shareholders")
if "--check" in sys.argv: sys.exit(0)

pin = os.environ.get("ES_PIN", "").strip()
if len(pin) < 4:
    raise SystemExit("ES_PIN secret is missing or shorter than 4 characters: refusing to publish the page")
html = open(PAGE).read()
m = re.search(r"var ENC=(\{.*?\});", html)
if m:  # skip the commit when nothing in the Sheet changed
    E = json.loads(m.group(1)); d = base64.b64decode
    try:
        k0 = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=d(E["s"]), iterations=E["n"]).derive(pin.encode())
        old = json.loads(AESGCM(k0).decrypt(d(E["i"]), d(E["c"]), None))
        if all(old.get(k) == payload.get(k) for k in ("loans", "shares", "settings")):
            print("No changes in the Sheet"); sys.exit(0)
    except Exception:
        pass  # PIN changed: rebuild
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=N).derive(pin.encode())
ct = AESGCM(key).encrypt(iv, json.dumps(payload, separators=(",", ":")).encode(), None)
e = lambda b: base64.b64encode(b).decode()
enc = "var ENC=%s;" % json.dumps({"s": e(salt), "i": e(iv), "c": e(ct), "n": N}, separators=(",", ":"))
html, k = re.subn(r"var ENC=(null|\{.*?\});", lambda _: enc, html, count=1)
assert k == 1, "ENC marker not found"
open(PAGE, "w").write(html)
print("index.html updated")
