import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import re
import os
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, quote

# কনফিগারেশন
OUTPUT_DIR = "posters"
PLAYLIST_FILE = "playlist.m3u"
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
        
        if len(logos) < 2: return False

        canvas = Image.new('RGBA', (1080, 810), (0, 0, 0, 0))
        img1 = auto_crop_and_resize(logos[0], 480, 600)
        img2 = auto_crop_and_resize(logos[1], 480, 600)
        
        canvas.paste(img1, (270 - (img1.width // 2), 405 - (img1.height // 2)), img1)
        canvas.paste(img2, (810 - (img2.width // 2), 405 - (img2.height // 2)), img2)
        
        canvas.save(local_path, "PNG", optimize=True)
        return True
    except:
        return False

def extract_m3u8(vipbox_url):
    try:
        res1 = s.get(vipbox_url, timeout=10).text
        iframe = re.search(r"src=['\"](https?://dungatv[^'\"]+)['\"]", res1, re.IGNORECASE)
        if not iframe: return None
        
        res2 = s.get(iframe.group(1), headers={'Referer': vipbox_url}, timeout=10).text
        js = re.search(r"src=['\"](https?://aquaaqua\.top[^'\"]+)['\"]", res2, re.IGNORECASE)
        if not js: return None
        
        res3 = s.get(js.group(1), headers={'Referer': iframe.group(1)}, timeout=10).text
        player = re.search(r'src=["\'](https?://[^"\']+page\.php[^"\']+)["\']', res3, re.IGNORECASE)
        if not player: return None
        
        res4 = s.get(player.group(1), headers={'Referer': iframe.group(1)}, timeout=10).text
        m3u8 = re.search(r'source:\s*["\']([^"\']+\.m3u8)["\']', res4, re.IGNORECASE)
        return m3u8.group(1) if m3u8 else None
    except:
        return None

def main():
    bd_tz = timezone(timedelta(hours=6))
    last_update = datetime.now(bd_tz).strftime("%I:%M %p %d-%m-%Y")
    
    m3u_content = f'#EXTM3U\n#name: VIPBOX Auto Poster Playlist\n#owner: Md Sohanur Rahman Hady\n#update: {last_update}\n\n'
    
    active_posters = []
    
    print("[*] Scraping VIPBOX Live...")
    res = s.get("https://vipboxi.net/live", timeout=15)
    soup = BeautifulSoup(res.text, 'html.parser')
    current_unix = int(time.time())
    
    for header in soup.find_all('h3'):
        time_span = header.find('span', class_=lambda x: x and x.startswith('dt '))
        if not time_span: continue
        
        # শুধু লাইভ ম্যাচ (শুরুর ৩০ মিনিট আগে থেকে)
        if current_unix < (int(time_span['class'][1]) - 1800): continue
        
        match_name = header.find_all('span', id='notbold')[1].text.strip()
        links_div = header.find_next_sibling('div')
        
        m3u8_link = None
        logo_urls = []
        
        if links_div:
            # ১. লোগো খোঁজা (অ্যাড লিংক থেকে)
            for a in links_div.find_all('a'):
                if any(x in a['href'] for x in ["lightbrights1", "bestgugo1"]):
                    try:
                        ad_res = s.get(a['href'], allow_redirects=True, timeout=5)
                        ad_soup = BeautifulSoup(ad_res.text, 'html.parser')
                        logo_urls = [urljoin(ad_res.url, i['src']) for i in ad_soup.select('.pilot img')]
                        break
                    except: continue
            
            # ২. স্ট্রিমিং লিংক খোঁজা
            for a in links_div.find_all('a'):
                if "vipboxi.net" in a['href']:
                    m3u8_link = extract_m3u8(a['href'])
                    if m3u8_link: break
        
        if m3u8_link:
            poster_name = f"{sanitize_filename(match_name)}.png"
            logo_gen = False
            if len(logo_urls) >= 2:
                logo_gen = create_poster(match_name, logo_urls)
            
            logo_final = f"https://raw.githubusercontent.com/{os.environ.get('GITHUB_REPOSITORY')}/main/posters/{quote(poster_name)}" if logo_gen else ""
            active_posters.append(poster_name)
            
            m3u_content += f'#EXTINF:-1 tvg-logo="{logo_final}" group-title="VIPBOX LIVE", {match_name}\n'
            m3u_content += f'#EXTVLCOPT:http-referrer=https://vipbox1.com/\n{m3u8_link}\n\n'
            print(f"✅ Processed: {match_name}")

    with open(PLAYLIST_FILE, "w") as f: f.write(m3u_content)
    
    # পুরোনো পোস্টার ডিলিট করা
    for f in os.listdir(OUTPUT_DIR):
        if f not in active_posters: os.remove(os.path.join(OUTPUT_DIR, f))

if __name__ == "__main__":
    main()
