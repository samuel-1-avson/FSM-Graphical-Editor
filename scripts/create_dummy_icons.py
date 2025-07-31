# bsm_designer_project/create_dummy_icons.py

import os
from PIL import Image, ImageDraw, ImageFont

# Define the base path for icons relative to the project root
# This script is in fsm_designer_project/scripts, so we go up one level.
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
icons_dir = os.path.join(project_root, "dependencies", "icons")

# Create directories if they don't exist
os.makedirs(icons_dir, exist_ok=True)

def create_dummy_icon(path, color=(0, 180, 0, 255), shape="check"):
    """Creates a dummy icon image if it doesn't exist."""
    if not os.path.exists(path):
        try:
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0)) # Create larger for better drawing
            draw = ImageDraw.Draw(img)

            if shape == "check":
                draw.line([(16, 32), (28, 44), (48, 20)], fill=color, width=8)
            elif shape == "arrow_down":
                draw.polygon([(12, 20), (52, 20), (32, 44)], fill=color)
            elif shape == "debounce": # Simple wave-like symbol
                draw.line([(12, 40), (24, 24), (36, 40), (48, 24)], fill=color, width=8)
            elif shape == "blinker": # Simple square on/off
                draw.rectangle([(16, 16), (48, 48)], outline=color, width=4)
                draw.line([(16, 32), (48, 32)], fill=color, width=4) # Divider
            elif shape == "app_icon":
                # Create a simple BSM initial state-like icon
                draw.ellipse([(4, 4), (60, 60)], fill=(220, 235, 255), outline=(100, 181, 246), width=5)
                try:
                    # Attempt to load a common system font
                    font = ImageFont.truetype("arialbd.ttf", 28)
                except IOError:
                    font = ImageFont.load_default()
                draw.text((12, 16), "BSM", fill=(20, 20, 20), font=font)

            img = img.resize((32, 32), Image.Resampling.LANCZOS)
            
            # For ico, we might need specific sizes, but for png, 32x32 is fine for app icon
            if path.endswith(".ico"):
                 img.save(path, format='ICO', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (256, 256)])
            else:
                 img.save(path)
                 
            print(f"Created dummy icon: {path}")
        except Exception as e:
            print(f"Error creating {path}: {e}")
    else:
        print(f"Icon already exists: {path}")

# Create required icons
create_dummy_icon(os.path.join(icons_dir, "check.png"), shape="check")
create_dummy_icon(os.path.join(icons_dir, "arrow_down.png"), color=(100, 100, 100, 255), shape="arrow_down")
create_dummy_icon(os.path.join(icons_dir, "debounce_icon.png"), color=(0, 0, 200, 255), shape="debounce")
create_dummy_icon(os.path.join(icons_dir, "blinker_icon.png"), color=(200, 100, 0, 255), shape="blinker")
create_dummy_icon(os.path.join(icons_dir, "app_icon.ico"), shape="app_icon")

print("Icon generation script finished.")