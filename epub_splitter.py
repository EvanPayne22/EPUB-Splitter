# -*- coding: utf-8 -*-
"""
EPUB Splitter with:
  - Optional custom title
  - Optional single range output
  - Keeps cover
  - Adds styles.css with paragraph indent + header styling
  - Valid TOC
  - Uses filename for chapter titles
"""

import zipfile
from bs4 import BeautifulSoup
import argparse
import os
import re

# ------------------------------
# 1. Parse CLI args
# ------------------------------
parser = argparse.ArgumentParser(description="Split a large EPUB file into parts",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("epub", nargs='?', help="Path to the EPUB file")
parser.add_argument("-splitsize", nargs='?', type=int, default=100, help="Number of chapters per split")
parser.add_argument("-outdir", nargs='?', default=None, help="Optional output directory for split files")
parser.add_argument("-title", nargs='?', default=None, help="Optional custom title for output EPUB(s)")
parser.add_argument("-singlerange", nargs=2, type=int, metavar=('START', 'END'),
                    help="Create a single file for chapters START to END (inclusive)")
args = parser.parse_args()
config = vars(args)

epub_file = config["epub"]
split_size = config["splitsize"]
output_dir = config["outdir"]

# ------------------------------
# 2. Helpers
# ------------------------------
def get_base_name(input_path):
    if input_path.lower().endswith(".epub"):
        input_path = input_path[:-5]
    for i in range(len(input_path) - 1, -1, -1):
        if input_path[i] == '/' or input_path[i] == '\\':
            return input_path[i+1:]
    return input_path

def get_base_dir(input_path):
    for i in range(len(input_path) - 1, -1, -1):
        if input_path[i] == '/' or input_path[i] == '\\':
            return input_path[:i+1]
    return "./"

base_name = get_base_name(epub_file)

if output_dir:
    if not (output_dir.endswith('/') or output_dir.endswith('\\')):
        output_dir += '/'
else:
    output_dir = get_base_dir(epub_file)

os.makedirs(output_dir, exist_ok=True)

print(f"Base file name: {base_name}")
print(f"Output directory: {output_dir}")

# ------------------------------
# 3. Extract chapters + cover image
# ------------------------------
chapters = []
cover_image = None
cover_image_name = None
cover_media_type = None

with zipfile.ZipFile(epub_file, 'r') as z:
    files = z.namelist()
    html_files = [f for f in files if f.endswith(('.html', '.xhtml'))]
    html_files.sort()

    for file_name in html_files:
        with z.open(file_name) as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.decode_contents()

            # ✅ Use filename for chapter title
            base_file = file_name.split('/')[-1]
            chapter_title = base_file
            if chapter_title.endswith('.html') or chapter_title.endswith('.xhtml'):
                chapter_title = chapter_title.rsplit('.', 1)[0]
            chapter_title = re.sub(r'^\d+-', '', chapter_title)
            chapter_title = chapter_title.replace('-', ' ').strip()

            chapters.append({
                'file_name': base_file,
                'content': text,
                'title': chapter_title
            })

    # Look for a cover image
    for file_name in files:
        lower_name = file_name.lower()
        if "cover" in lower_name and lower_name.endswith(('.jpg', '.jpeg', '.png')):
            cover_image = z.read(file_name)
            cover_image_name = file_name.split('/')[-1]
            if cover_image_name.endswith('.jpg') or cover_image_name.endswith('.jpeg'):
                cover_media_type = "image/jpeg"
            elif cover_image_name.endswith('.png'):
                cover_media_type = "image/png"
            print(f"✔️ Found cover image: {cover_image_name}")
            break

print(f"Found {len(chapters)} chapters.")

# ------------------------------
# 4. Split logic
# ------------------------------
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

if config["singlerange"]:
    start, end = config["singlerange"]
    if start < 1 or end > len(chapters) or start > end:
        raise ValueError(f"Invalid range: {start}-{end}. Total chapters: {len(chapters)}")
    chapter_batches = [chapters[start-1:end]]
    print(f"Creating 1 file for chapters {start}-{end}...")
else:
    chapter_batches = list(chunks(chapters, split_size))
    print(f"Creating {len(chapter_batches)} split files...")

# ------------------------------
# 5. Write each EPUB file
# ------------------------------
for i, batch in enumerate(chapter_batches, start=1):
    start_chapter = (i - 1) * split_size + 1
    end_chapter = start_chapter + len(batch) - 1

    if config["singlerange"]:
        start_chapter = config["singlerange"][0]
        end_chapter = config["singlerange"][1]

    # Determine final display title
    if config["title"]:
        part_title = config["title"]
    else:
        part_title = f"{base_name} {start_chapter}-{end_chapter}"

    # Use custom file name as save file name
    if config["title"]:
        safe_title = re.sub(r'\s+', '_', config["title"].strip())
        output_name = f"{output_dir}{safe_title}.epub"
    else:
        output_name = f"{output_dir}{base_name}_{start_chapter}_{end_chapter}.epub"


    print(f"Writing {output_name} with title '{part_title}'...")

    with zipfile.ZipFile(output_name, 'w') as outzip:
        # mimetype
        outzip.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)

        # META-INF/container.xml
        container_xml = '''<?xml version="1.0"?>
<container version="1.0"
  xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
   <rootfiles>
      <rootfile full-path="content.opf"
         media-type="application/oebps-package+xml"/>
   </rootfiles>
</container>'''
        outzip.writestr('META-INF/container.xml', container_xml)

        # Cover image
        if cover_image and cover_image_name:
            outzip.writestr(cover_image_name, cover_image)

        # styles.css
        css_content = '''
body {
  text-align: justify;
}

h1 {
    font-size: 160%;
    padding: 1em;   
}

p {
  text-indent: 2em;
  margin: 0 0 1em 0;
}
'''
        outzip.writestr('styles.css', css_content)

        # Manifest & spine
        manifest_items = ''
        spine_items = ''
        idx_offset = 1

        if cover_image_name and cover_media_type:
            manifest_items += f'<item id="cover" href="{cover_image_name}" media-type="{cover_media_type}" properties="cover-image"/>\n'

        manifest_items += '<item id="css" href="styles.css" media-type="text/css"/>\n'

        for idx, chapter in enumerate(batch, start=idx_offset):
            manifest_items += f'<item id="chap{idx}" href="{chapter["file_name"]}" media-type="application/xhtml+xml"/>\n'
            spine_items += f'<itemref idref="chap{idx}"/>\n'

            # Just use original content (wrapped with CSS)
            chapter_html = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>{chapter["title"]}</title>
  <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
{chapter["content"]}
</body>
</html>
'''
            outzip.writestr(chapter["file_name"], chapter_html)

        manifest_items += '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'

        # content.opf
        metadata = f'''
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{part_title}</dc:title>
    <dc:language>en</dc:language>
    <dc:identifier id="BookId">{base_name}_part_{i}</dc:identifier>
  '''
        if cover_image_name:
            metadata += '<meta name="cover" content="cover"/>'
        metadata += '\n  </metadata>'

        content_opf = f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="2.0">
{metadata}
  <manifest>
    {manifest_items}
  </manifest>
  <spine toc="ncx">
    {spine_items}
  </spine>
</package>'''
        outzip.writestr('content.opf', content_opf)

        # TOC navPoints
        nav_points = ''
        nav_index = 1

        if cover_image_name:
            nav_points += f'''
    <navPoint id="navPoint-0" playOrder="0">
      <navLabel><text>Cover</text></navLabel>
      <content src="{cover_image_name}"/>
    </navPoint>'''

        for idx, chapter in enumerate(batch, start=1):
            nav_points += f'''
    <navPoint id="navPoint-{nav_index}" playOrder="{nav_index}">
      <navLabel><text>{chapter["title"]}</text></navLabel>
      <content src="{chapter["file_name"]}"/>
    </navPoint>'''
            nav_index += 1

        toc_ncx = f'''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="{base_name}_part_{i}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{part_title}</text></docTitle>
  <navMap>
    {nav_points}
  </navMap>
</ncx>'''
        outzip.writestr('toc.ncx', toc_ncx)

    print(f"✅ Wrote {output_name} with {len(batch)} chapters.")
