import os
import ssl
import json
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

def cari_web_nyata(query):
    if not TAVILY_API_KEY:
        return ""
    try:
        url = "https://api.tavily.com/search"
        payload = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": f"{query} spesifikasi teknis lengkap baterai charging layar chipset",
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 3
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as res:
            data = json.loads(res.read().decode('utf-8'))
            ringkasan = data.get("answer", "")
            snippets = " \n".join([r.get("content", "") for r in data.get("results", [])])
            return f"{ringkasan}\n{snippets}"
    except Exception as e:
        return ""

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))

        if not GEMINI_API_KEY:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "GEMINI_API_KEY belum dikonfigurasi di Vercel"}).encode('utf-8'))
            return

        tipe_oppo = data.get("tipe_oppo", "").strip()
        tipe_kompetitor = data.get("tipe_kompetitor", "").strip()
        harga_oppo = data.get("harga_oppo", "Tidak disebutkan")
        harga_kompetitor = data.get("harga_kompetitor", "Tidak disebutkan")
        gender = data.get("gender", "")
        usia = data.get("usia", "")
        pekerjaan = data.get("pekerjaan", "Umum")

        data_oppo = cari_web_nyata(tipe_oppo)
        data_kompetitor = cari_web_nyata(tipe_kompetitor)

        prompt = f"""
Anda adalah Master Sales Coach & Product Trainer Smartphone OPPO di Indonesia.
Tugas: Buat komparasi HEAD-TO-HEAD MENDALAM & RIIL berdasarkan data internet berikut.

DATA RIIL INTERNET:
--- UNIT OPPO ({tipe_oppo}) ---
{data_oppo if data_oppo else "Gunakan data spesifikasi resmi terkini perangkat ini."}

--- UNIT PEMBANDING ({tipe_kompetitor}) ---
{data_kompetitor if data_kompetitor else "Gunakan data spesifikasi resmi terkini perangkat ini."}

PROFIL CALON PEMBELI:
- Profil: {gender}, Usia {usia}, Profesi/Aktivitas: {pekerjaan}
- Harga Pasar: {tipe_oppo} ({harga_oppo}) vs {tipe_kompetitor} ({harga_kompetitor})

ATURAN STRATEGI:
1. KOMPARASI SEKTOR NYATA (WAJIB ANGKA METRIK):
   - Ambil data pembeda riil: Chipset, Jenis/Kecerahan Layar, Kapasitas Baterai (mAh) & Kecepatan Cas (SUPERVOOC vs Charger Lawan), serta Durabilitas Fisik (IP Rating).
2. RELEVANSI AKTIVITAS:
   - Sambungkan fitur unggulan OPPO langsung ke keuntungan pekerjaan konsumen ({pekerjaan}).
3. DILARANG memunculkan kelemahan produk OPPO.

FORMAT JAWABAN:
### 1. Komparasi Spek Nyata Head-to-Head
(Bandingkan 4 sektor: Performa/Chipset, Layar & Bodi, Baterai & Charging, Kamera dengan angka metrik konkret kedua HP.)

### 2. Strategi Nilai Harga (Price-to-Value)
(Penjelasan logis perbandingan selisih harga dengan peningkatan spek riil yang didapat.)

### 3. Skrip Closing Promotor
(2-3 kalimat lisan santai, persuasif, dan percaya diri yang langsung siap diucapkan promotor di lapangan.)
"""

        payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
        models = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
        success = False
        last_error = ""

        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_API_KEY}"
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=20) as res:
                    res_json = json.loads(res.read().decode('utf-8'))
                    text = res_json['candidates'][0]['content']['parts'][0]['text']
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"result": text}).encode('utf-8'))
                    success = True
                    break
            except Exception as e:
                last_error = str(e)
                continue

        if not success:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Layanan AI gagal: {last_error}"}).encode('utf-8'))
