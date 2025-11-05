from flask import Flask, request, render_template_string, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import mysql.connector
from collections import deque
import time
import csv
import io

app = Flask(__name__)

# ✅ Cloud Database connection (Railway)
def get_db():
    return mysql.connector.connect(
        host="yamanote.proxy.rlwy.net",
        user="root",
        password="dHUFxnHumqKaIYOjiorGkGhHcFTNmiPH",
        port=34171,
        database="railway"
    )


# ✅ Crawl function (no limits)
def crawl_site(start_url, mode="single"):
    parsed = urlparse(start_url)
    base_domain = parsed.netloc
    q = deque([(start_url, 0)])
    visited = set()
    results = []
    session = requests.Session()
    session.headers.update({"User-Agent": "seo-bot/1.0"})

    while q:
        url, depth = q.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = session.get(url, timeout=10)
            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""
            canonical_tag = soup.find("link", rel="canonical")
            canonical = canonical_tag["href"] if canonical_tag and canonical_tag.get("href") else ""
            h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]

            results.append({
                "url": url,
                "title": title,
                "canonical": canonical,
                "h1": h1s
            })

            # Only crawl more pages if "Entire Website" is selected
            if mode == "entire":
                for a in soup.find_all("a", href=True):
                    link = urljoin(url, a["href"])
                    if urlparse(link).netloc == base_domain and link not in visited:
                        q.append((link, depth + 1))

        except Exception as e:
            print("Error fetching:", url, "=>", e)
        time.sleep(0.3)

        # If single mode, only analyze the first page
        if mode == "single":
            break

    return results



# ✅ Save results to cloud DB
def save_to_db(start_url, results):
    db = get_db()
    cur = db.cursor()
    for r in results:
        cur.execute(
            "INSERT INTO crawl_results (page_url, title, canonical, h1) VALUES (%s, %s, %s, %s)",
            (r["url"], r["title"], r["canonical"], "\n".join(r["h1"]))
        )
    db.commit()
    cur.close()
    db.close()


# ✅ HTML Template (includes download link)
HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Website SEO Analyzer</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background: linear-gradient(180deg, #e8f1ff 0%, #ffffff 100%);
      color: #333;
      min-height: 100vh;
      padding-top: 40px;
    }
    .analyzer-box {
      background: #fff;
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
      border-radius: 12px;
      padding: 40px;
      max-width: 800px;
      margin: 0 auto;
    }
    .btn-analyze {
      background-color: #007bff;
      border: none;
      color: white;
      padding: 10px 20px;
      border-radius: 6px;
      transition: all 0.2s;
    }
    .btn-analyze:hover {
      background-color: #0056b3;
      transform: scale(1.03);
    }
    .loader {
      display: none;
      text-align: center;
      margin-top: 20px;
    }
    .result-card {
      background: #fff;
      border-radius: 10px;
      padding: 20px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.05);
      margin-top: 25px;
    }
    th {
      background-color: #007bff;
      color: white;
      text-align: center;
    }
    td {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div class="container text-center">
  <h1 class="fw-bold text-primary mb-4">Website SEO Analyzer</h1>

  <div class="analyzer-box">
   <form method="post" onsubmit="showLoader()">
  <div class="input-group mb-3">
    <input name="url" type="url" class="form-control form-control-lg" placeholder="Enter a website URL (e.g. https://example.com)" required>
  </div>

  <!-- 🌐 Crawl Mode Options -->
  <div class="form-check form-check-inline">
    <input class="form-check-input" type="radio" name="mode" id="single" value="single" checked>
    <label class="form-check-label" for="single">Single Page</label>
  </div>
  <div class="form-check form-check-inline">
    <input class="form-check-input" type="radio" name="mode" id="entire" value="entire">
    <label class="form-check-label" for="entire">Entire Website</label>
  </div>

  <div class="mt-3">
    <button class="btn-analyze" type="submit">Analyze Website</button>
  </div>
</form>


    <div id="loader" class="loader">
      <div class="spinner-border text-primary" role="status"></div>
      <p class="text-muted mt-3">Analyzing website... Please wait.</p>
    </div>

    <div class="text-center mt-3">
      <a href="/download" class="btn btn-success btn-sm" target="_blank">Download Results</a>
    </div>
  </div>

  {% if results %}
  <div class="result-card">
    <h4 class="text-primary mb-3">Analysis Results</h4>
    <div class="table-responsive">
      <table class="table table-bordered table-striped align-middle">
        <thead>
          <tr>
            <th>#</th>
            <th>URL</th>
            <th>Title</th>
            <th>Canonical</th>
            <th>H1 Tags</th>
          </tr>
        </thead>
        <tbody>
        {% for r in results %}
          <tr>
            <td>{{ loop.index }}</td>
            <td><a href="{{ r.url }}" target="_blank">{{ r.url }}</a></td>
            <td>{{ r.title }}</td>
            <td>{{ r.canonical }}</td>
            <td>{% for h in r.h1 %}<div>{{ h }}</div>{% endfor %}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  {% endif %}
</div>

<script>
function showLoader() {
  document.getElementById("loader").style.display = "block";
}
</script>

</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        mode = request.form.get("mode", "single")  # 🟢 Get selected mode from the form
        results = crawl_site(url, mode)            # 🟢 Pass it to the crawl function
        save_to_db(url, results)
        return render_template_string(HTML, results=results)
    return render_template_string(HTML)


# ✅ Route to download results as CSV
@app.route("/download")
def download_csv():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT page_url, title, canonical, h1 FROM crawl_results")
    rows = cur.fetchall()
    cur.close()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["URL", "Title", "Canonical", "H1 Tags"])
    writer.writerows(rows)

    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=seo_results.csv"
    return response


# ✅ Run locally
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))  # Render provides the PORT dynamically
    app.run(host="0.0.0.0", port=port, debug=False)
