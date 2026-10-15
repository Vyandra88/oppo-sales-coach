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
    if not TAVILY_API_KEY or not query:
        return ""
    try:
        url = "https://api.tavily.com/search"
        payload = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": f"{query} spesifikasi teknis lengkap gsmarena baterai charging layar chipset",
            "search_depth": "advanced",
            "include_answer": True,
            "max_results": 3
        }).encode('utf-8')
        
        req = urllib.request.Request(
            url, 
            data=payload, 
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=12) as res:
            data = json.loads(res.read().decode('utf-8'))
            ringkasan = data.get("answer", "")
            snippets = " \n".join([r.get("content", "") for r in data.get("results", [])])
            return f"{ringkasan}\n{snippets}"
    except Exception as e:
        print(f"Error Tavily: {e}")
        return ""

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if not GEMINI_API_KEY:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "GEMINI_API_KEY belum terpasang di Vercel"}).encode('utf-8'))
                return

            # Menangani kedua variasi format penamaan input agar tidak kosong
            tipe_oppo = (data.get("tipe_oppo") or data.get("oppoModel") or "").strip()
            tipe_kompetitor = (data.get("tipe_kompetitor") or data.get("competitorModel") or "").strip()
            harga_oppo = (data.get("harga_oppo") or data.get("oppoPrice") or "Tidak disebutkan").strip()
            harga_kompetitor = (data.get("harga_kompetitor") or data.get("competitorPrice") or "Tidak disebutkan").strip()
            gender = (data.get("gender") or "").strip()
            usia = (data.get("usia") or data.get("age") or "").strip()
            pekerjaan = (data.get("pekerjaan") or data.get("occupation") or "Umum").strip()

            data_oppo = cari_web_nyata(tipe_oppo)
            data_kompetitor = cari_web_nyata(tipe_kompetitor)

            prompt = f"""
Anda adalah Master Sales Coach & Product Trainer Smartphone OPPO di Indonesia.
Tugas Anda: Membuat komparasi HEAD-TO-HEAD MENDALAM & RIIL antara {tipe_oppo} melawan {tipe_kompetitor}.

PERINGATAN KERAS:
- DILARANG MENGGANTI perangkat ke model lain (misal Reno12 atau A55). Anda WAJIB membahas secara eksklusif {tipe_oppo} melawan {tipe_kompetitor}.
- JANGAN menuliskan catatan bahwa unit tidak ditemukan atau menggunakan benchmark lain.

DATA RIIL DARI HASIL PENCARIAN WEB:
--- SPESIFIKASI {tipe_oppo} ---
{data_oppo if data_oppo else "Gunakan data spesifikasi teknis resmi dari " + tipe_oppo}

--- SPESIFIKASI {tipe_kompetitor} ---
{data_kompetitor if data_kompetitor else "Gunakan data spesifikasi teknis resmi dari " + tipe_kompetitor}

PROFIL CALON PEMBELI:
- Profil: {gender}, Rentang Usia: {usia}, Aktivitas/Pekerjaan: {pekerjaan}
- Harga Pasar: {tipe_oppo} ({harga_oppo}) vs {tipe_kompetitor} ({harga_kompetitor})

PANDUAN STRATEGI:
1. Cantumkan angka metrik riil spesifikasi (Chipset, nits kecerahan layar, kapasitas baterai mAh, dan Watt charging resmi).
2. Hubungkan fitur unggulan {tipe_oppo} langsung dengan relevansi pekerjaan/kegiatan konsumen ({pekerjaan}).
3. DILARANG memunculkan kelemahan produk OPPO.

FORMAT JAWABAN:
### 1. Komparasi Spek Nyata Head-to-Head
(Tabel/Poin komparasi konkret: Performa/Chipset, Layar & Bodi, Baterai & Charging, Kamera dengan angka metrik konkret kedua HP.)

### 2. Strategi Nilai Harga (Price-to-Value)
(Penjelasan logis perbandingan selisih harga dengan peningkatan spek riil yang didapat.)

### 3. Skrip Closing Promotor
(2-3 kalimat lisan santai, persuasif, dan percaya diri yang langsung siap diucapkan promotor di lantai toko.)
"""

            payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode('utf-8')
            models = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
            output_text = ""
            last_error = ""

            for m in models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_API_KEY}"
                req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
                try:
                    with urllib.request.urlopen(req, context=ctx, timeout=25) as res:
                        res_json = json.loads(res.read().decode('utf-8'))
                        output_text = res_json['candidates'][0]['content']['parts'][0]['text']
                        break
                except Exception as e:
                    last_error = str(e)
                    continue

            if not output_text:
                raise Exception(f"Gagal generate dari Gemini: {last_error}")

            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"result": output_text}).encode('utf-8'))

        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Kendala teknis backend: {str(e)}"}).encode('utf-8'))
