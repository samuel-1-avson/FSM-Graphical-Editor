# bsm_designer_project/create_dummy_icons.py

import os
from PIL import Image, ImageDraw

# Define the base path for icons relative to this script
# Assuming this script is in bsm_designer_project
icons_dir = os.path.join("dependencies", "icons")

# Create directories if they don't exist
os.makedirs(icons_dir, exist_ok=True)

def create_dummy_icon(path, color=(0,180,0,255), shape="check"):
    if not os.path.exists(path):
        try:
            img = Image.new('RGBA', (16, 16), (0, 0, 0, 0)) # Transparent background
            draw = ImageDraw.Draw(img)
            if shape == "check":
                draw.line([(4, 8), (7, 11), (12, 5)], fill=color, width=2)
            elif shape == "arrow_down":
                draw.polygon([(3,5), (13,5), (8,11)], fill=color) # Adjusted for 16x16
            elif shape == "debounce": # Simple wave-like symbol
                draw.line([(3,10), (6,6), (9,10), (12,6)], fill=color, width=2)
            elif shape == "blinker": # Simple square on/off
                draw.rectangle([(4,4), (12,12)], outline=color, width=1)
                draw.line([(4,10),(12,10)], fill=color, width=1) # Divider
            img.save(path)
            print(f"Created dummy icon: {path}")
        except Exception as e:
            print(f"Error creating {path}: {e}")
    else:
        print(f"Icon already exists: {path}")

# Create check.png
create_dummy_icon(os.path.join(icons_dir, "check.png"), shape="check")

# Create arrow_down.png
create_dummy_icon(os.path.join(icons_dir, "arrow_down.png"), color=(100,100,100,255), shape="arrow_down")

# Create debounce_icon.png (matches resource file)
create_dummy_icon(os.path.join(icons_dir, "debounce_icon.png"), color=(0,0,200,255), shape="debounce")

# Create blinker_icon.png (matches resource file)
create_dummy_icon(os.path.join(icons_dir, "blinker_icon.png"), color=(200,100,0,255), shape="blinker")


print("Icon generation script finished.")