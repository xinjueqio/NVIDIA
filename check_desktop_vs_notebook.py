import urllib.request
import urllib.error

def get_file_info(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                size = int(response.headers.get('Content-Length', 0))
                return size, response.url # response.url might show redirect
            return -1, url
    except Exception as e:
        print(f"Error checking {url}: {e}")
        return -1, url

def format_size(size_bytes):
    if size_bytes < 0: return "Unknown"
    return f"{size_bytes / 1024 / 1024:.2f} MB"

def check_version(version):
    base = f"http://cn.download.nvidia.com/Windows/{version}/{version}"
    
    # Define URLs
    urls = {
        "Desktop DCH": f"{base}-desktop-win10-64bit-international-dch-whql.exe",
        "Notebook DCH": f"{base}-notebook-win10-64bit-international-dch-whql.exe",
        "Desktop Std": f"{base}-desktop-win10-64bit-international-whql.exe",
        "Notebook Std": f"{base}-notebook-win10-64bit-international-whql.exe"
    }
    
    print(f"--- Analyzing Version {version} ---")
    results = {}
    
    for name, url in urls.items():
        size, final_url = get_file_info(url)
        results[name] = size
        print(f"{name}: {format_size(size)} ({size} bytes)")
        # print(f"  URL: {url}")
    
    # Comparisons
    print("\n--- Comparisons ---")
    
    # 1. DCH: Desktop vs Notebook
    d_dch = results["Desktop DCH"]
    n_dch = results["Notebook DCH"]
    if d_dch > 0 and n_dch > 0:
        if d_dch == n_dch:
            print(f"Desktop DCH == Notebook DCH (IDENTICAL)")
        else:
            print(f"Desktop DCH != Notebook DCH (Diff: {format_size(abs(d_dch - n_dch))})")
            
    # 2. Std: Desktop vs Notebook
    d_std = results["Desktop Std"]
    n_std = results["Notebook Std"]
    if d_std > 0 and n_std > 0:
        if d_std == n_std:
            print(f"Desktop Std == Notebook Std (IDENTICAL)")
        else:
            print(f"Desktop Std != Notebook Std (Diff: {format_size(abs(d_std - n_std))})")

    # 3. Notebook: DCH vs Std
    if n_dch > 0 and n_std > 0:
        if n_dch == n_std:
            print(f"Notebook DCH == Notebook Std (IDENTICAL)")
        else:
            print(f"Notebook DCH != Notebook Std (Diff: {format_size(abs(n_dch - n_std))})")

if __name__ == "__main__":
    check_version("430.86")
