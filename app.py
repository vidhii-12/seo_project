from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import mysql.connector
from collections import deque
import time

app = Flask(__name__)

# Database connection
def get_db():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",       # change if you set password
        password="",       # leave empty for default XAMPP
        database="seo_tool"
    )

# Crawler function
def crawl_site(start_url, max_pages=5, max_depth=1):
    parsed = urlparse(start_url)
    base_domain = parsed.netloc
    q = deque([(start_url, 0)])
    visited = set()
    results = []
    session = requests.Session()
    session.headers.update({"User-Agent": "seo-bot/1.0"})

    while q and len(results) < max_pages:
        url, depth = q.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        try:
            resp = session.get(url, timeout=10)
            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue

            soup = BeautifulSoup(resp.text, "html.parser")  # using built-in parser
            title = soup.title.string.strip() if soup.title else ""
            canonical_tag = soup.find("link", rel="canonical")
            canonical = canonical_tag["href"] if canonical_tag and canonical_tag.get("href") else ""
            h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]

            results.append({"url": url, "title": title, "canonical": canonical, "h1": h1s})

            for a in soup.find_all("a", href=True):
                link = urljoin(url, a["href"])
                if urlparse(link).netloc == base_domain and link not in visited:
                    q.append((link, depth + 1))

        except Exception as e:
            print("Error fetching:", url, "=>", e)
        time.sleep(0.3)

    return results

# Save to DB
def save_to_db(start_url, results):
    db = get_db()
    cur = db.cursor()
    for r in results:
        cur.execute(
            "INSERT INTO crawl_results (start_url, page_url, title, canonical, h1) VALUES (%s,%s,%s,%s,%s)",
            (start_url, r["url"], r["title"], r["canonical"], "\n".join(r["h1"]))
        )
    db.commit()
    cur.close()
    db.close()

# HTML Template
HTML = """
<!doctype html>
<title>SEO Crawler</title>
<h2>SEO Tool - Crawl Title, Canonical & H1</h2>
<form method="post">
  <input name="url" placeholder="https://example.com" style="width:400px" required>
  Max Pages: <input name="max_pages" value="5" size="3">
  Max Depth: <input name="max_depth" value="1" size="3">
  <input type="submit" value="Crawl">
</form>
{% if results %}
  <h3>Results:</h3>
  <table border=1 cellpadding=5>
    <tr><th>#</th><th>URL</th><th>Title</th><th>Canonical</th><th>H1 Tags</th></tr>
   {% for r in results %}
<tr>
  <td>{{ loop.index }}</td>
  <td><a href="{{ r.url }}" target="_blank">{{ r.url }}</a></td>
  <td>{{ r.title }}</td>
  <td>{{ r.canonical }}</td>
  <td>{% for h in r.h1 %}<div>{{ h }}</div>{% endfor %}</td>
</tr>
{% endfor %}

  </table>
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        max_pages = int(request.form.get("max_pages", 5))
        max_depth = int(request.form.get("max_depth", 1))
        results = crawl_site(url, max_pages, max_depth)
        save_to_db(url, results)
        return render_template_string(HTML, results=results)
    return render_template_string(HTML)

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
