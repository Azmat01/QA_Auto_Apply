import json
import urllib.error
import urllib.request

key = "sb_publishable_zxQP2aJ4Z79OuDo-0YvWPA_MwDBWBu_"
base = "https://gstjnmduuevtwlybaldm.supabase.co/rest/v1/job_postings"
headers = {"apikey": key, "Authorization": f"Bearer {key}"}

req = urllib.request.Request(
    base + "?select=id,url,title",
    headers=headers,
)
with urllib.request.urlopen(req, timeout=20) as response:
    rows = json.loads(response.read().decode())

print("before", len(rows))
for row in rows:
    print(row["title"], "->", row["url"])
    delete = urllib.request.Request(
        f"{base}?id=eq.{row['id']}",
        method="DELETE",
        headers={**headers, "Prefer": "return=representation"},
    )
    try:
        with urllib.request.urlopen(delete, timeout=20) as response:
            print(" deleted", response.status, response.read().decode()[:160])
    except urllib.error.HTTPError as exc:
        print(" delete fail", exc.code, exc.read().decode()[:300])

req = urllib.request.Request(base + "?select=id", headers=headers)
with urllib.request.urlopen(req, timeout=20) as response:
    print("after", len(json.loads(response.read().decode())))
