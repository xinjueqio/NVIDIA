import urllib.request
import json
import urllib.parse
import os
import time
from datetime import datetime

# Configuration
BASE_URL = "https://gfwsl.geforce.cn/services_toolkit/services/com/nvidia/services/AjaxDriverService.php"

# IDs
ID_DESKTOP = {"psid": 101, "pfid": 815} # GTX 1080
ID_NOTEBOOK = {"psid": 102, "pfid": 819} # GTX 1080 Notebook

class NvidiaFetcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch_drivers(self, psid, pfid, dch, upCRD, isWHQL=1, num_results=250):
        params = {
            "func": "DriverManualLookup",
            "psid": psid,
            "pfid": pfid,
            "osID": 57, # Win 10 64
            "languageCode": 2052, # Simplified Chinese
            "beta": 0,
            "isWHQL": isWHQL,
            "dltype": -1,
            "dch": dch, 
            "upCRD": upCRD, # 1=Studio, 0=Game Ready
            "sort1": 0,
            "numberOfResults": num_results
        }
        
        query_string = urllib.parse.urlencode(params)
        url = f"{BASE_URL}?{query_string}"
        
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=180) as response:
                data = response.read()
                return json.loads(data)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_and_merge(self, results_map):
        # results_map: list of (data, is_dch, driver_type_label, is_whql)
        
        # Key: (Version, IsDCH, DriverType) -> {ReleaseDate, Type, DesktopURL, NotebookURL, ...}
        merged_drivers = {}

        for data, is_dch, driver_type, is_whql in results_map:
            if not data or "IDS" not in data:
                continue
                
            for item in data["IDS"]:
                info = item.get("downloadInfo", {})
                version = info.get("Version")
                if not version:
                    continue
                
                # Unique key
                key = (version, is_dch, driver_type)
                
                if key not in merged_drivers:
                    merged_drivers[key] = {
                        "Version": version,
                        "ReleaseDate": info.get("ReleaseDateTime"),
                        "Type": driver_type,
                        "IsDCH": is_dch,
                        "DesktopURL": "N/A",
                        "NotebookURL": "N/A"
                    }
                
                download_url = info.get("DownloadURL")
                if download_url:
                    # We are only fetching Desktop drivers now, so this is the Desktop URL
                    merged_drivers[key]["DesktopURL"] = download_url
                    
                    # Generate Notebook URL by replacing 'desktop' with 'notebook'
                    # Verify the pattern exists before replacing to be safe
                    if "-desktop-" in download_url:
                        notebook_url = download_url.replace("-desktop-", "-notebook-")
                        merged_drivers[key]["NotebookURL"] = notebook_url
                    else:
                        # Fallback or log if pattern doesn't match (though it should for standard/dch desktop drivers)
                        # Some very old drivers might differ, but for GTX 1080 era, this is standard.
                        pass

        # Convert to list
        driver_list = list(merged_drivers.values())
        return driver_list

    def save_to_markdown(self, drivers, filename):
        # Sort by Release Date desc
        try:
            drivers.sort(key=lambda x: datetime.strptime(x['ReleaseDate'], '%Y-%m-%d'), reverse=True)
        except:
            pass 

        def is_old_notebook_dch(version):
            # Check if version < 472.12
            try:
                parts = [int(x) for x in version.split('.')]
                if len(parts) < 2: return False
                major, minor = parts[0], parts[1]
                if major < 472: return True
                if major == 472 and minor < 12: return True
                return False
            except:
                return False

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# NVIDIA 驱动历史版本列表 (GTX 1080)\n")
            f.write(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if not drivers:
                f.write("未找到驱动信息。\n")
                return

            f.write(f"共找到 {len(drivers)} 个版本（已合并双端及 Studio 数据）。\n\n")
            f.write("---\n\n")
            
            for d in drivers:
                type_str = d['Type']
                arch_str = "DCH" if d['IsDCH'] else "Standard"
                version = d['Version']
                
                # Fix Notebook DCH for old versions (remove -dch instead of hiding)
                notebook_url = d['NotebookURL']
                if d['IsDCH'] and is_old_notebook_dch(version) and notebook_url != "N/A":
                    notebook_url = notebook_url.replace("-dch", "")
                
                # Determine platform string for header
                platforms = []
                if d['DesktopURL'] != "N/A": platforms.append("台式机")
                if notebook_url != "N/A": platforms.append("笔记本")
                
                # If no platforms, skip
                if not platforms:
                    continue
                    
                platform_header = " & ".join(platforms)

                # Header Line
                f.write(f"### {version} | {d['ReleaseDate']} | {arch_str} | {type_str} | {platform_header}\n")
                
                # Download Lines
                if d['DesktopURL'] != "N/A":
                    f.write(f"> **台式机下载**: [{d['DesktopURL']}]({d['DesktopURL']})\n")
                    # Add a spacer if notebook also exists
                    if notebook_url != "N/A":
                        f.write(">\n")
                
                if notebook_url != "N/A":
                    f.write(f"> **笔记本下载**: [{notebook_url}]({notebook_url})\n")
                
                f.write("\n---\n\n")
            
        print(f"Saved results to {filename}")

def main():
    fetcher = NvidiaFetcher()
    
    # Define tasks: Only fetching DESKTOP versions now to reduce API calls.
    # Notebook links will be generated by replacing 'desktop' with 'notebook' in the URL.
    tasks_config = [
        # Game Ready (upCRD=0)
        {"name": "Desktop DCH (GRD)",      "psid": ID_DESKTOP["psid"],  "pfid": ID_DESKTOP["pfid"],  "dch": 1, "upCRD": 0, "isWHQL": 1, "type": "Game Ready"},
        {"name": "Desktop Standard (GRD)", "psid": ID_DESKTOP["psid"],  "pfid": ID_DESKTOP["pfid"],  "dch": 0, "upCRD": 0, "isWHQL": 1, "type": "Game Ready"},
        
        # Studio (upCRD=1)
        # Using isWHQL=0 for Studio based on testing
        {"name": "Desktop DCH (Studio)",   "psid": ID_DESKTOP["psid"],  "pfid": ID_DESKTOP["pfid"],  "dch": 1, "upCRD": 1, "isWHQL": 0, "type": "Studio"},
    ]
    
    results_map = []
    
    for t in tasks_config:
        print(f"Fetching {t['name']}...")
        # Note: We added isWHQL to fetch_drivers signature implicitly? No, need to update fetch_drivers signature too.
        # Let's update fetch_drivers to accept isWHQL kwarg or just pass it in params.
        # Wait, I need to update fetch_drivers method signature in the class above if I haven't.
        # I will update fetch_drivers in a separate block or assume I can edit it here? 
        # I need to edit the whole file or multiple blocks. 
        # Since I am replacing the bottom half, I should ensure fetch_drivers is updated.
        # Actually, I'll update fetch_drivers in a separate tool call or use multi_replace if needed.
        # But wait, I can just update the call here and update the method in the same file content if I replace enough.
        # The previous tool call replaced up to line 156.
        # I will replace from parse_and_merge downwards, but I also need to update fetch_drivers signature.
        # Let's do a multi_replace or just replace the whole file content to be safe and clean.
        pass

    # Re-implementing main loop correctly
    for t in tasks_config:
        print(f"Fetching {t['name']}...")
        data = fetcher.fetch_drivers(psid=t['psid'], pfid=t['pfid'], dch=t['dch'], upCRD=t['upCRD'], isWHQL=t['isWHQL'])
        if data:
            count = len(data.get("IDS", []))
            print(f"  -> Found {count} items.")
            results_map.append((data, t['dch'] == 1, t['type'], t['isWHQL']))
        else:
            print("  -> Failed or empty.")

    merged_drivers = fetcher.parse_and_merge(results_map)
    print(f"Total unique driver entries merged: {len(merged_drivers)}")
    
    fetcher.save_to_markdown(merged_drivers, "h:/0.项目/nv/README.md")

if __name__ == "__main__":
    main()
