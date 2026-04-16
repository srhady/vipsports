import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import re
import os
import time
from urllib.parse import urljoin

# গিটহাব ডিরেক্টরি সেটআপ
BASE_DIR = os.getcwd()
OUTPUT_DIR = os.path.join(BASE_DIR, "posters")
os.makedirs(OUTPUT_DIR, exist_ok=True)

s = requests.Session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Referer': 'https://vipboxi.net/'
})

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
    filename = f"{sanitize_filename(match_name)}.png"
    local_path = os.path.join(OUTPUT_DIR, filename)
    try:
        logos = []
        for url in logo_urls:
            print(f"      [~] Downloading: {url}")
            res = s.get(url, timeout=15)
            if res.status_code == 200:
                logos.append(Image.open(BytesIO(res.content)).convert('RGBA'))
        
        if len(logos) < 2: return False

        canvas = Image.new('RGBA', (1080, 810), (0, 0, 0, 0))
        img1 = auto_crop_and_resize(logos[0], 480, 600)
        img2 = auto_crop_and_resize(logos[1], 480, 600)
        
        canvas.paste(img1, (270 - (img1.width // 2), 405 - (img1.height // 2)), img1)
        canvas.paste(img2, (810 - (img2.width // 2), 405 - (img2.height // 2)), img2)
        
        canvas.save(local_path, "PNG", optimize=True)
        print(f"      ✅ Poster Created: {filename}")
        return True
    except Exception as e:
        print(f"      [!] Error: {e}")
        return False

def main():
    print("🚀 SCRAPER START: Tracking lightbrights -> bettingoffer chain...")
    try:
        res = s.get("https://vipboxi.net/live", timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        all_h3 = soup.find_all('h3')
        
        active_filenames = []

        for h in all_h3:
            name_spans = h.find_all('span', id='notbold')
            if len(name_spans) < 2: continue
            match_name = name_spans[1].text.strip()
            
            links_div = h.find_next('div')
            if not links_div: continue
            
            # lightbrights লিংকটি খুঁজে বের করা
            lb_link = None
            for a in links_div.find_all('a'):
                if "lightbrights" in a.get('href', ''):
                    lb_link = a['href']
                    break
            
            if lb_link:
                print(f"\n🎯 Target: {match_name}")
                print(f"    [*] Step 1: Accessing {lb_link}")
                try:
                    # রিডাইরেক্ট ফলো করে ল্যান্ডিং পেজে যাওয়ার চেষ্টা
                    ad_res = s.get(lb_link, allow_redirects=True, timeout=15)
                    
                    # যদি অটো-রিডাইরেক্ট না হয়, তবে পেজের ভেতর থেকে ম্যানুয়ালি bettingoffer লিংক খোঁজা
                    if "bettingoffer" not in ad_res.url:
                        temp_soup = BeautifulSoup(ad_res.text, 'html.parser')
                        manual_link = temp_soup.find('a', href=re.compile(r'bettingoffer\.xyz'))
                        if manual_link:
                            print(f"    [*] Step 2: Manual redirect found to {manual_link['href']}")
                            ad_res = s.get(manual_link['href'], timeout=15)

                    print(f"    [+] Final Landing Page: {ad_res.url}")
                    
                    # এবার লোগো এক্সট্রাক্ট করা
                    final_soup = BeautifulSoup(ad_res.text, 'html.parser')
                    logo_urls = [urljoin(ad_res.url, i['src']) for i in final_soup.select('.pilot img')]
                    
                    if len(logo_urls) >= 2:
                        if create_poster(match_name, logo_urls):
                            active_filenames.append(f"{sanitize_filename(match_name)}.png")
                        time.sleep(1)
                    else:
                        print("    [-] Logos still not found on landing page.")
                except Exception as e:
                    print(f"    [!] Chain Error: {e}")

        # ডিলিট লজিক
        print("\n[*] Cleaning up old posters...")
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith('.png') and f not in active_filenames:
                os.remove(os.path.join(OUTPUT_DIR, f))

        print(f"\n🎉 Active posters: {len(active_filenames)}")
                
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
