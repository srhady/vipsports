import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import re
import os
import time
from urllib.parse import urljoin

# গিটহাবের জন্য পাথ সেটআপ
BASE_DIR = os.getcwd()
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
            print(f"      [~] Downloading logo: {url}")
            res = s.get(url, timeout=15)
            if res.status_code == 200:
                logos.append(Image.open(BytesIO(res.content)).convert('RGBA'))
        
        if len(logos) < 2:
            print("      [!] Not enough logos downloaded.")
            return False

        canvas = Image.new('RGBA', (1080, 810), (0, 0, 0, 0))
        img1 = auto_crop_and_resize(logos[0], 480, 600)
        img2 = auto_crop_and_resize(logos[1], 480, 600)
        
        canvas.paste(img1, (270 - (img1.width // 2), 405 - (img1.height // 2)), img1)
        canvas.paste(img2, (810 - (img2.width // 2), 405 - (img2.height // 2)), img2)
        
        canvas.save(local_path, "PNG", optimize=True)
        print(f"      ✅ Success! Saved to: {local_path}")
        return True
    except Exception as e:
        print(f"      [!] Error making poster: {e}")
        return False

def main():
    print(f"[*] Scanning VIPBOX for matches...")
    try:
        res = s.get("https://vipboxi.net/live", timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        headers = soup.find_all('h3')
        
        print(f"[*] Found {len(headers)} matches total.")
        active_posters = []

        for h in headers:
            name_span = h.find_all('span', id='notbold')
            if len(name_span) < 2: continue
            
            match_name = name_span[1].text.strip()
            print(f"\n[>] Checking: {match_name}")
            
            links_div = h.find_next_sibling('div')
            if links_div:
                # যে কোনো অ্যাড লিংক খুঁজে বের করা
                ad_a = None
                for a in links_div.find_all('a'):
                    href = a.get('href', '')
                    if "lightbrights" in href or "bestgugo" in href or "reffpa" in href:
                        ad_a = a
                        break
                
                if ad_a:
                    ad_url = ad_a['href']
                    print(f"    [*] Found Ad link, following: {ad_url}")
                    try:
                        ad_res = s.get(ad_url, allow_redirects=True, timeout=15)
                        ad_soup = BeautifulSoup(ad_res.text, 'html.parser')
                        # লোগো ইউআরএল কালেক্ট করা
                        logo_urls = [urljoin(ad_res.url, i['src']) for i in ad_soup.select('.pilot img')]
                        
                        if len(logo_urls) >= 2:
                            if create_poster(match_name, logo_urls):
                                active_posters.append(f"{sanitize_filename(match_name)}.png")
                        else:
                            print("    [-] Could not find team logos on the redirect page.")
                    except Exception as e:
                        print(f"    [!] Failed to reach redirect page: {e}")
                else:
                    print("    [-] No usable ad/logo link found for this match.")

        print(f"\n[*] All done. Total new posters created: {len(active_posters)}")
                
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
