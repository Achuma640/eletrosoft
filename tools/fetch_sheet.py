#!/usr/bin/env python3
"""Download the Electrosoft Loans Register tabs as {"values": [...]} JSON.
Needs GOOGLE_SA_KEY (service-account JSON, as text) in the environment.
Usage: python3 tools/fetch_sheet.py OUT_DIR -> loans.json, payments.json, shareholders.json"""
import json, os, sys
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

SHEET = "1cB7MrZNVaf-eirOCq13H1nNcbYOLg8Jly1Fnf_rBY20"
RANGES = {"loans.json": "Loans!A1:K500", "payments.json": "Payments!A1:F20000", "shareholders.json": "Shareholders!A1:B500"}
creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GOOGLE_SA_KEY"]), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
s = AuthorizedSession(creds)
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for fn, rng in RANGES.items():
    r = s.get("https://sheets.googleapis.com/v4/spreadsheets/%s/values/%s" % (SHEET, rng),
              params={"valueRenderOption": "UNFORMATTED_VALUE"})
    r.raise_for_status()
    vals = r.json().get("values", [])
    while vals and not any(vals[-1]):
        vals.pop()
    json.dump({"values": vals}, open(os.path.join(out, fn), "w"))
    print(fn, len(vals), "rows")
