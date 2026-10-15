import os
import json
from http.server import BaseHTTPRequestHandler
import google.generativeai as genai
from tavily import TavilyClient

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                raw_body = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(raw_body)
            else:
                data = {}

            oppo_model = str(data.get('oppoModel', '')).strip()
            oppo_price = str(data.get('oppoPrice', '')).strip()
            comp_model = str(data.get('competitorModel', '')).strip()
            comp_price = str(data.get('competitorPrice', '')).strip()
            gender = str(data.get('gender', '')).strip()
            age = str(data.get('age', '')).strip()
            occupation = str(data.get('occupation', '')).strip()

            # 1. Pencarian Spesifikasi Terkini via Tavily
            tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
            web_context = ""
            if tavily_key and oppo_model and comp_model:
                try:
                    tavily = TavilyClient(api_key=tavily_key)
                    query = f"spesifikasi resmi GSMarena {oppo_model} vs {comp_model} Indonesia processor chipset kamera watt fast charging"
                    search_res = tavily.search(query=query, max_results=3)
                    web_context = "\n".join([r.get("content", "") for r in search_res.get("results", []) if r.get("content")])
                except Exception:
                    web_context = ""

            # 2. Setup Gemini AI
            gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not gemini_key:
                raise ValueError("GEMINI_API_KEY belum disetel di Vercel Environment Variables.")

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""
Anda adalah Sales Trainer dan Coach Retail OPPO Indonesia profesional.
Tugas Anda adalah membantu Promotor menyusun argumen penjualan dan komparasi spesifikasi yang 100% AKURAT dan ELEGAN.

Gunakan data referensi spesifikasi berikut:
--- DATA SPESIFIKASI REFERENSI ---
{web_context if web_context else "Gunakan pengetahuan faktual resmi terbaru."}
---------------------------------

DATA PERANGKAT:
- Unit OPPO: {oppo_model} (Harga: {oppo_price})
- Unit Kompetitor: {comp_model} (Harga: {comp_price})

PROFIL KONSUMEN:
- Gender: {gender}
- Rentang Usia: {age}
- Aktivitas / Pekerjaan: {occupation}

INSTRUKSI WAJIB:
1. Pastikan seluruh spesifikasi (Chipset/Prosesor, Layar, Baterai, Kecepatan Watt Charging, dan Kamera) BENAR-BENAR SESUAI FAKTA PRODUK. JANGAN TUKAR SPESIFIKASI ANTARA KEDUA HP.
2. Sajikan Tabel Komparasi Spesifikasi Kunci yang jelas dan mudah dipahami.
3. Berikan Value Selling & Keunggulan OPPO yang menjawab kebutuhan aktivitas profil konsumen ({occupation}).
4. Buat Skrip Penanganan Keberatan (Handling Objection) elegan tanpa menjelekkan kompetitor secara kasar.

Gunakan format teks Markdown yang rapi.
"""

            response = model.generate_content(prompt)
            result_text = response.text if response and response.text else "Maaf, respon tidak dapat dihasilkan. Silakan coba kembali."

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"result": result_text}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
