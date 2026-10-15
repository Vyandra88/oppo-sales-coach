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

def cari_spek_mandiri(nama_hp):
    """Mencari spesifikasi spesifik per unit ke Tavily secara terpisah agar data tidak tercampur"""
    if not TAVILY_API_KEY or not nama_hp:
        return ""
    try:
        url = "https://api.tavily.com/search"
        payload = json.dumps({
            "api_key": TAVILY_API_KEY,
            "query": f"{nama_hp} spesifikasi gsmarena baterai mAh supervooc fast charging chipset layar",
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
        print(f"Error Tavily {nama_hp}: {e}")
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

            tipe_oppo = (data.get("tipe_oppo") or data.get("oppoModel") or "").strip()
            tipe_kompetitor = (data.get("tipe_kompetitor") or data.get("competitorModel") or "").strip()
            harga_oppo = (data.get("harga_oppo") or data.get("oppoPrice") or "Tidak disebutkan").strip()
            harga_kompetitor = (data.get("harga_kompetitor") or data.get("competitorPrice") or "Tidak disebutkan").strip()
            gender = (data.get("gender") or "").strip()
            usia = (data.get("usia") or data.get("age") or "").strip()
            pekerjaan = (data.get("pekerjaan") or data.get("occupation") or "Umum").strip()

            # Pencarian terpisah agar data tidak tertukar
            data_oppo = cari_spek_mandiri(tipe_oppo)
            data_kompetitor = cari_spek_mandiri(tipe_kompetitor)

            prompt = f"""
Peran: Anda adalah Head Trainer & Master Sales Coach OPPO di Indonesia.
Tugas: Buat komparasi HEAD-TO-HEAD MENDALAM, RIIL, dan AKURAT antara {tipe_oppo} melawan {tipe_kompetitor}.

DATA HASIL PENCARIAN WEB RESMI:
--- DATA SPESIFIKASI {tipe_oppo} ---
{data_oppo if data_oppo else "Gunakan data spesifikasi resmi terkini dari unit " + tipe_oppo}

--- DATA SPESIFIKASI {tipe_kompetitor} ---
{data_kompetitor if data_kompetitor else "Gunakan data spesifikasi resmi terkini dari unit " + tipe_kompetitor}

PROFIL CALON PEMBELI:
- Profil: {gender}, Usia: {usia}, Aktivitas/Pekerjaan: {pekerjaan}
- Harga: {tipe_oppo} ({harga_oppo}) vs {tipe_kompetitor} ({harga_kompetitor})

ATURAN KETAT SPESIFIKASI:
1. Ekstrak dan gunakan angka metrik riil dari data di atas:
   - Kapasitas Baterai (misal: jika tertulis 8000 mAh atau 5000 mAh, wajib tulis angka aslinya, dilarang menebak angka lain!).
   - Kecepatan Cas (SUPERVOOC Watt vs Fast Charging kompetitor).
   - Layar (Panel, Refresh Rate Hz, Nits kecerahan).
   - Chipset/Prosesor & Sertifikasi Fisik (IP rating / Shock resistance).
2. DILARANG menukar spesifikasi antara OPPO dan Kompetitor.
3. Sambungkan kelebihan {tipe_oppo} langsung ke keuntungan aktivitas calon pembeli ({pekerjaan}).
4. DILARANG memunculkan kelemahan produk OPPO.

FORMAT OUTPUT:
### 1. Komparasi Spek Nyata Head-to-Head
(Bandingkan 4 sektor utama: Performa/Chipset, Layar & Bodi, Baterai & Fast Charging, serta Kamera dengan data metrik angka riil kedua HP.)

### 2. Strategi Nilai Harga (Price-to-Value)
(Analisis keuntungan investasi harga terhadap fitur riil yang didapat konsumen.)

### 3. Skrip Closing Promotor
(2-3 kalimat lisan persuasif, santai, dan meyakinkan untuk diucapkan langsung promotor ke konsumen.)
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
