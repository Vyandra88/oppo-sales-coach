import os
import json
from http.server import BaseHTTPRequestHandler
import requests
import google.generativeai as genai

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
            post_body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_body) if post_body else {}

            oppo_model = data.get('oppoModel', '').strip()
            oppo_price = data.get('oppoPrice', '').strip()
            comp_model = data.get('competitorModel', '').strip()
            comp_price = data.get('competitorPrice', '').strip()
            gender = data.get('gender', '').strip()
            age = data.get('age', '').strip()
            occupation = data.get('occupation', '').strip()

            # 1. Tarik Data Web via REST API Tavily (Ringan & Aman di Serverless)
            web_context = ""
            tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
            if tavily_key and oppo_model and comp_model:
                try:
                    payload = {
                        "api_key": tavily_key,
                        "query": f"spesifikasi resmi GSMarena {oppo_model} vs {comp_model} Indonesia processor kamera watt",
                        "max_results": 3
                    }
                    res = requests.post("https://api.tavily.com/search", json=payload, timeout=6)
                    if res.status_code == 200:
                        results = res.json().get("results", [])
                        web_context = "\n".join([r.get("content", "") for r in results])
                except Exception:
                    web_context = ""

            # 2. Hubungkan ke Gemini
            gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not gemini_key:
                raise Exception("GEMINI_API_KEY belum terdaftar di Environment Variables Vercel")

            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""
Anda adalah Sales Trainer dan Coach Retail OPPO Indonesia.
Bantu Promotor menyusun argumen penjualan dan tabel komparasi spesifikasi yang 100% AKURAT.

DATA PERANGKAT:
- Unit OPPO: {oppo_model} (Harga: {oppo_price})
- Unit Kompetitor: {comp_model} (Harga: {comp_price})

PROFIL KONSUMEN:
- Gender: {gender}
- Usia: {age}
- Pekerjaan: {occupation}

REFERENSI SPESIFIKASI DARI INTERNET:
{web_context if web_context else "Gunakan data spesifikasi resmi terkini."}

INSTRUKSI:
1. Pastikan spesifikasi kedua perangkat (Chipset, Baterai, Charging Watt, Kamera, dan Layar) benar-benar akurat sesuai fakta dan tidak tertukar.
2. Sajikan Tabel Komparasi Spesifikasi Kunci.
3. Jelaskan Keunggulan OPPO yang relevan bagi profil konsumen ini ({occupation}).
4. Susun Skrip Handling Objection elegan untuk meyakinkan pembeli memilih {oppo_model}.

Gunakan format teks Markdown yang rapi.
"""

            response = model.generate_content(prompt)
            output_text = response.text if response and response.text else "Tidak ada respon dari model."

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"result": output_text}).encode('utf-8'))

        except Exception as e:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Kendala teknis backend: {str(e)}"}).encode('utf-8'))
