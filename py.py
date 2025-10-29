# paste your raw URLs (each on a new line) into urls_raw.txt before running
with open("urls_raw.txt") as f:
    urls = [line.strip() for line in f if line.strip()]

with open("pdf_urls_list.py", "w") as f:
    f.write("pdf_urls = [\n")
    for url in urls:
        f.write(f'    "{url}",\n')
    f.write("]\n")

print("✅ pdf_urls_list.py created successfully!")