import os
import json
from http.server import BaseHTTPRequestHandler
import requests

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

            # 1. Cari info spek via Tavily
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

            # 2. Validasi API Key Gemini
            gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not gemini_key:
                raise Exception("GEMINI_API_KEY belum terpasang di Environment Variables Vercel")

            # 3. Cek otomatis model apa saja yang diizinkan untuk key ini
            list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
            list_res = requests.get(list_url, timeout=10)

            if list_res.status_code != 200:
                raise Exception(f"Google menolak API Key ini: {list_res.text}")

            models_data = list_res.json().get("models", [])
            valid_models = [
                m["name"] for m in models_data 
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]

            if not valid_models:
                raise Exception("API Key aktif, tapi tidak ada model Gemini yang punya izin generateContent.")

            # Pilih model terbaik yang tersedia (prioritaskan flash atau pro)
            chosen_model = valid_models[0]
            for m in valid_models:
                if "flash" in m.lower():
                    chosen_model = m
                    break
                elif "pro" in m.lower():
                    chosen_model = m

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

            # 4. Generate teks pakai model resmi yang terdeteksi
            gen_url = f"https://generativelanguage.googleapis.com/v1beta/{chosen_model}:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            body = {"contents": [{"parts": [{"text": prompt}]}]}

            gen_res = requests.post(gen_url, headers=headers, json=body, timeout=25)

            if gen_res.status_code != 200:
                raise Exception(f"Gagal generate pada {chosen_model}: {gen_res.text}")

            candidates = gen_res.json().get("candidates", [])
            if not candidates:
                raise Exception("AI tidak menghasilkan teks respon.")

            output_text = candidates[0]["content"]["parts"][0]["text"]

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
