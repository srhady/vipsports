import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import re
import os
import time
from urllib.parse import urljoin

# আপনার রিকোয়ারমেন্ট অনুযায়ী ফোল্ডার পাথ (মেইন ডিরেক্টরি থেকে posters ফোল্ডার)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")
os.makedirs(OUTPUT_DIR, exist_ok=True)

s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def auto_crop_and_resize(img, max_w, max_h):
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    ratio = min(max_w / img.width, max_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

def create_poster(match_name, logo_urls):
    local_path = os.path.join(OUTPUT_DIR, f"{sanitize_filename(match_name)}.png")
    try:
        logos = []
        for url in logo_urls:
            res = s.get(url, timeout=10)
            if res.status_code == 200:
                logos.append(Image.open(BytesIO(res.content)).convert('RGBA'))
        
        if len(logos) < 2: return

        canvas = Image.new('RGBA', (1080, 810), (0, 0, 0, 0))
        img1 = auto_crop_and_resize(logos[0], 480, 600)
        img2 = auto_crop_and_resize(logos[1], 480, 600)
        
        # পজিশনিং
        canvas.paste(img1, (270 - (img1.width // 2), 405 - (img1.height // 2)), img1)
        canvas.paste(img2, (810 - (img2.width // 2), 405 - (img2.height // 2)), img2)
        
        canvas.save(local_path, "PNG", optimize=True)
        print(f"    ✅ Poster Saved: {local_path}")
    except Exception as e:
        print(f"    [!] Error: {e}")

def main():
    print(f"[*] Scanning VIPBOX for Live Match Logos...")
    try:
        res = s.get("https://vipboxi.net/live", timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        headers = soup.find_all('h3')
        
        current_unix = int(time.time())
        active_posters = []

        for h in headers:
            time_span = h.find('span', class_=lambda x: x and x.startswith('dt '))
            if not time_span: continue
            
            # শুধুমাত্র লাইভ ম্যাচ ফিল্টার
            if current_unix >= (int(time_span['class'][1]) - 1800):
                name_span = h.find_all('span', id='notbold')
                match_name = name_span[1].text.strip() if len(name_span) > 1 else "Unknown"
                
                links_div = h.find_next_sibling('div')
                if links_div:
                    for a in links_div.find_all('a'):
                        if any(x in a['href'] for x in ["lightbrights1", "bestgugo1"]):
                            print(f"\n🎯 Processing: {match_name}")
                            # রিডাইরেক্ট পেজ থেকে লোগো খোঁজা
                            try:
                                ad_res = s.get(a['href'], allow_redirects=True, timeout=5)
                                ad_soup = BeautifulSoup(ad_res.text, 'html.parser')
                                logo_urls = [urljoin(ad_res.url, i['src']) for i in ad_soup.select('.pilot img')]
                                if len(logo_urls) >= 2:
                                    create_poster(match_name, logo_urls)
                                    active_posters.append(f"{sanitize_filename(match_name)}.png")
                                    break
                            except: continue

        # পুরোনো বা শেষ হয়ে যাওয়া ম্যাচের পোস্টার ডিলিট করা
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith('.png') and f not in active_posters:
                os.remove(os.path.join(OUTPUT_DIR, f))
                
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
