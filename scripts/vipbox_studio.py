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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

def sanitize_filename(name):
    # ফাইলের নাম থেকে অবৈধ ক্যারেক্টার সরানো
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def auto_crop_and_resize(img, max_w, max_h):
    # আপনার সিগনেচার ক্রপ লজিক
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
            print(f"      [~] Fetching Logo: {url}")
            res = s.get(url, timeout=15)
            if res.status_code == 200:
                logos.append(Image.open(BytesIO(res.content)).convert('RGBA'))
        
        if len(logos) < 2:
            return False

        # ১০৮০x৮১০ ট্রান্সপারেন্ট ক্যানভাস (আপনার রিকোয়ারমেন্ট অনুযায়ী)
        canvas = Image.new('RGBA', (1080, 810), (0, 0, 0, 0))
        img1 = auto_crop_and_resize(logos[0], 480, 600)
        img2 = auto_crop_and_resize(logos[1], 480, 600)
        
        # বাম ও ডানে লোগো বসানো
        canvas.paste(img1, (270 - (img1.width // 2), 405 - (img1.height // 2)), img1)
        canvas.paste(img2, (810 - (img2.width // 2), 405 - (img2.height // 2)), img2)
        
        canvas.save(local_path, "PNG", optimize=True)
        print(f"      ✅ Poster Created: {filename}")
        return True
    except Exception as e:
        print(f"      [!] Error: {e}")
        return False

def main():
    print("🚀 TARGETING: lightbrights links for Match Logos...")
    try:
        res = s.get("https://vipboxi.net/live", timeout=25)
        soup = BeautifulSoup(res.text, 'html.parser')
        all_h3 = soup.find_all('h3')
        
        active_filenames = []

        for h in all_h3:
            name_spans = h.find_all('span', id='notbold')
            if len(name_spans) < 2: continue
            match_name = name_spans[1].text.strip()
            
            # পরবর্তী লিংকের ডিব খোঁজা
            links_div = h.find_next('div')
            if not links_div: continue
            
            # শুধু lightbrights লিংকটি টার্গেট করা
            lb_link = None
            for a in links_div.find_all('a'):
                href = a.get('href', '')
                if "lightbrights" in href: # এখানে আপনার শর্ত বসানো হয়েছে
                    lb_link = href
                    break
            
            if lb_link:
                print(f"\n🎯 Processing Match: {match_name}")
                try:
                    # রিডাইরেক্ট ফলো করে আসল পেজে যাওয়া
                    ad_res = s.get(lb_link, allow_redirects=True, timeout=15)
                    ad_soup = BeautifulSoup(ad_res.text, 'html.parser')
                    
                    # লোগোর ইমেজগুলো খোঁজা (.pilot img)
                    logo_urls = [urljoin(ad_res.url, i['src']) for i in ad_soup.select('.pilot img')]
                    
                    if len(logo_urls) >= 2:
                        if create_poster(match_name, logo_urls):
                            active_filenames.append(f"{sanitize_filename(match_name)}.png")
                        time.sleep(1) # ছোট বিরতি
                    else:
                        print("    [-] No logos found in lightbrights page.")
                except:
                    print(f"    [!] Failed to load lightbrights link.")
            else:
                # যদি lightbrights না থাকে, আমরা এটা স্কিপ করব
                pass

        # অটো ক্লিনআপ: যেসব ম্যাচের লোগো এখন আর লিঙ্কে নেই, সেগুলো ডিলিট করা
        print("\n[*] Cleaning up old posters...")
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith('.png') and f not in active_filenames:
                os.remove(os.path.join(OUTPUT_DIR, f))
                print(f"    [-] Deleted: {f}")

        print(f"\n🎉 Finished! Current active posters: {len(active_filenames)}")
                
    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
