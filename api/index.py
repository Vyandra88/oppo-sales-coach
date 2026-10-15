import os
import json
from http.server import BaseHTTPRequestHandler
import google.generativeai as genai
from tavily import TavilyClient

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)

            oppo_model = data.get('oppoModel', '').strip()
            oppo_price = data.get('oppoPrice', '').strip()
            comp_model = data.get('competitorModel', '').strip()
            comp_price = data.get('competitorPrice', '').strip()
            gender = data.get('gender', '').strip()
            age = data.get('age', '').strip()
            occupation = data.get('occupation', '').strip()

            # 1. Tarik Data Spesifikasi Resmi Lewat Tavily
            tavily_key = os.environ.get("TAVILY_API_KEY")
            web_context = ""
            if tavily_key:
                try:
                    tavily = TavilyClient(api_key=tavily_key)
                    query = f"spesifikasi resmi GSMarena {oppo_model} vs {comp_model} Indonesia processor kamera fast charging"
                    search_res = tavily.search(query=query, max_results=3)
                    web_context = "\n".join([r.get("content", "") for r in search_res.get("results", [])])
                except Exception:
                    web_context = ""

            # 2. Setup Gemini AI
            gemini_key = os.environ.get("GEMINI_API_KEY")
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""
Anda adalah Sales Trainer dan Coach Retail OPPO Indonesia.
Gunakan data spesifikasi akurat berikut untuk membandingkan perangkat:
--- DATA SPESIFIKASI DARI INTERNET ---
{web_context}
-------------------------------------

DATA PERANGKAT:
- Unit OPPO: {oppo_model} (Harga: {oppo_price})
- Unit Kompetitor: {comp_model} (Harga: {comp_price})

PROFIL KONSUMEN:
- Gender: {gender}
- Rentang Usia: {age}
- Aktivitas/Pekerjaan: {occupation}

INSTRUKSI PENTING:
1. Pastikan chipset, kapasitas baterai, kecepatan pengisian daya (Watt), sensor kamera, dan layar kedua HP BENAR-BENAR SESUAI FAKTA SPESIFIKASI. JANGAN MENEBAK ATAU MENUKAR SPESIFIKASI.
2. Buat tabel perbandingan spesifikasi kunci.
3. Buat skrip percakapan penanganan keberatan yang elegan, mengarahkan konsumen agar mantap memilih {oppo_model} sesuai kebutuhan aktivitasnya ({occupation}).

Berikan format output rapi menggunakan Markdown.
"""

            response = model.generate_content(prompt)
            result_text = response.text

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"result": result_text}).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
