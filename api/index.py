import os
import json
from http.server import BaseHTTPRequestHandler
import requests

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-goog-api-key')
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

            # 1. Tarik Data Web via REST API Tavily
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
                        web_context = "\n".join([r.get("content", "") for r in results if r.get("content")])
                except Exception:
                    web_context = ""

            # 2. Cek API Key Gemini
            gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not gemini_key:
                raise Exception("GEMINI_API_KEY belum terpasang di Environment Variables Vercel")

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

            # 3. Model Gemini Resmi Terbaru (Mengatasi 404 pada model usang)
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.0-flash-exp",
                "gemini-1.5-flash-002",
                "gemini-1.5-pro-002"
            ]

            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": gemini_key
            }
            body = {
                "contents": [{"parts": [{"text": prompt}]}]
            }

            output_text = ""
            last_err = ""

            for m in models_to_try:
                # Coba dengan parameter query ?key=
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gemini_key}"
                res = requests.post(url, headers=headers, json=body, timeout=25)

                if res.status_code == 200:
                    candidates = res.json().get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            output_text = parts[0].get("text", "")
                            break
                else:
                    last_err = res.text

            if not output_text:
                raise Exception(f"Gagal generate dari Gemini: {last_err}")

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
