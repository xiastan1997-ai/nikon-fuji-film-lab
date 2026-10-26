"""Inventory TIFF-based NEFs without claiming sensor-data decoding."""
from pathlib import Path
import csv
import hashlib
import io
import json
import shutil
import struct
import sys
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1])
DEST = ROOT / 'data/originals/nikon/downloaded_raw_batch02'
PREVIEWS = ROOT / 'data/derived/raw_batch02_embedded_previews'
DEST.mkdir(parents=True, exist_ok=True)
PREVIEWS.mkdir(parents=True, exist_ok=True)
TYPES = {1:1, 2:1, 3:2, 4:4, 5:8, 7:1, 9:4, 10:8, 11:4, 12:8}

def inspect(data):
    if data[:2] not in (b'II', b'MM'):
        raise ValueError('Not a TIFF byte order header')
    order = '<' if data[:2] == b'II' else '>'
    def unpack(fmt, offset):
        size = struct.calcsize(order + fmt)
        if offset < 0 or offset + size > len(data):
            raise ValueError('TIFF structure out of file bounds')
        return struct.unpack_from(order + fmt, data, offset)
    if unpack('H', 2)[0] != 42:
        raise ValueError('Unsupported TIFF header')
    def value(pos):
        tag, typ, count, off = unpack('HHII', pos)
        if typ not in TYPES:
            return tag, None
        size = TYPES[typ] * count
        start = pos + 8 if size <= 4 else off
        if start + size > len(data):
            raise ValueError('TIFF value out of file bounds')
        raw = data[start:start+size]
        if typ == 2:
            result = raw.decode('ascii', errors='replace').rstrip('\0')
        elif typ in (1, 7):
            result = list(raw) if count <= 64 else {'bytes': count}
        elif typ in (3, 4, 9, 11, 12):
            result = list(struct.unpack(order + str(count) + {3:'H',4:'I',9:'i',11:'f',12:'d'}[typ], raw))
        elif typ in (5, 10):
            nums = struct.unpack(order + str(count*2) + ('I' if typ == 5 else 'i'), raw)
            result = [nums[i]/nums[i+1] if nums[i+1] else None for i in range(0, len(nums), 2)]
        else:
            result = None
        if isinstance(result, list) and len(result) == 1:
            result = result[0]
        return tag, result
    queue = [(unpack('I', 4)[0], 'IFD0')]
    visited, ifds, preview_data = set(), [], []
    while queue:
        off, label = queue.pop(0)
        if not off or off in visited:
            continue
        if len(visited) > 64:
            raise ValueError('Too many IFDs')
        visited.add(off)
        count = unpack('H', off)[0]
        if count > 4096:
            raise ValueError('Unreasonable IFD count')
        tags = dict(value(off+2+i*12) for i in range(count))
        nextoff = unpack('I', off+2+count*12)[0]
        for tag in (330, 34665):
            pointers = tags.get(tag, [])
            if not isinstance(pointers, list):
                pointers = [pointers]
            for j, ptr in enumerate(pointers):
                if isinstance(ptr, int):
                    queue.append((ptr, f'{label}/{tag}:{j}'))
        queue.append((nextoff, label+'/next'))
        spans = []
        for a,b in ((273,279),(324,325),(513,514)):
            if a not in tags or b not in tags:
                continue
            starts, sizes = tags[a], tags[b]
            if not isinstance(starts,list): starts=[starts]
            if not isinstance(sizes,list): sizes=[sizes]
            if len(starts) != len(sizes):
                raise ValueError('Data offset/count array mismatch')
            for start,size in zip(starts,sizes):
                if start < 0 or size < 0 or start+size > len(data):
                    raise ValueError('Image payload out of file bounds')
                spans.append({'offset':start,'bytes':size})
                block = data[start:start+size]
                if block[:2] == b'\xff\xd8':
                    try:
                        with Image.open(io.BytesIO(block)) as image:
                            image.load()
                            preview_data.append((image.width*image.height, block, list(image.size)))
                    except Exception:
                        pass
        keep = (254,256,257,258,259,271,272,305,306,33434,33437,34855,36867,37380,37386,40961,41987,42036)
        ifds.append({'label':label,'offset':off,'tags':{str(k):tags[k] for k in keep if k in tags},'payload_ranges':spans})
    return ifds, max(preview_data, key=lambda x:x[0]) if preview_data else None

manifest = ROOT / 'data/manifests/captures.csv'
with manifest.open(encoding='utf-8-sig', newline='') as f:
    reader = csv.DictReader(f)
    fields, rows = reader.fieldnames, list(reader)
records = []
sheet = Image.new('RGB', (1800, 1260), '#202020')
draw = ImageDraw.Draw(sheet)
for i, path in enumerate(sorted(SOURCE.glob('*.NEF'))):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    ifds, preview = inspect(data)
    target = DEST / path.name
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            raise ValueError('Existing project copy differs; refusing overwrite')
    else:
        shutil.copy2(path, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == sha
    tags = {k:v for entry in ifds for k,v in entry['tags'].items()}
    item = {'id':f'DLR{i+1:03}', 'source_path':str(path), 'relative_path':target.relative_to(ROOT).as_posix(),
            'bytes':len(data),'sha256':sha,'ifds':ifds,'same_stem_jpeg':(SOURCE/(path.stem+'.JPG')).exists(),
            'raw_pixel_decode':'not_performed','embedded_preview':None}
    if preview:
        preview_path = PREVIEWS / (path.stem+'.jpg')
        preview_path.write_bytes(preview[1])
        item['embedded_preview']={'relative_path':preview_path.relative_to(ROOT).as_posix(),'dimensions':preview[2], 'type':'camera-rendered JPEG, not newly developed RAW'}
        with Image.open(io.BytesIO(preview[1])) as im:
            thumb = ImageOps.exif_transpose(im)
            thumb.thumbnail((580,370))
            x,y=(i%3)*600,(i//3)*420
            sheet.paste(thumb,(x+(600-thumb.width)//2,y+35))
            draw.text((x+10,y+10),path.name+' [embedded JPEG]',fill='white')
    records.append(item)
    row={'capture_id':item['id'],'relative_path':item['relative_path'],'sha256':sha,
         'camera_model':tags.get('272',''),'scene_id':'unclassified_'+path.stem,
         'iso':tags.get('34855',''),'shutter':tags.get('33434',''),'aperture':tags.get('33437',''),
         'exposure_compensation':tags.get('37380',''),'picture_control':'unknown',
         'wb_mode':'auto' if tags.get('41987')==0 else 'unknown','split':'unassigned',
         'status':'nef_structure_checked_raw_decode_pending',
         'notes':'Downloaded sample; Software='+str(tags.get('305',''))+'; not user firmware; embedded preview not RAW decode; no same-stem JPEG'}
    rows=[x for x in rows if x['capture_id']!=item['id']]+[row]
with manifest.open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields)
    writer.writeheader();writer.writerows(rows)
(ROOT/'reports/raw-batch02-inventory.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sheet.crop((0,0,1800,840)).save(ROOT/'reports/raw-batch02-contact-sheet.jpg',quality=90)
for record in records:
    print(json.dumps({k:record[k] for k in ('id','source_path','bytes','same_stem_jpeg','raw_pixel_decode','embedded_preview')},ensure_ascii=False))
