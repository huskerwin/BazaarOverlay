"""
Generate app icon for Bazaar Overlay.
Creates a 256x256 PNG icon with Bazaar-themed design.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_icon():
    """Create a nice icon for the app."""
    # Size for the icon (256x256 for high quality)
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Colors inspired by The Bazaar game
    gold = (218, 165, 32, 255)      # Gold color
    dark_gold = (184, 134, 11, 255)  # Dark gold
    brown = (101, 67, 33, 255)       # Brown
    dark_bg = (30, 30, 40, 255)      # Dark background
    
    # Draw rounded rectangle background
    margin = 20
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=40,
        fill=dark_bg,
        outline=gold,
        width=4
    )
    
    # Draw a stylized "B" letter
    # Using simple shapes to create a Bazaar-style B
    center_x = size // 2
    center_y = size // 2
    
    # Draw outer circle (like a bazaar stall roof)
    draw.ellipse(
        [center_x - 70, center_y - 80, center_x + 70, center_y + 60],
        outline=gold,
        width=6,
        fill=None
    )
    
    # Draw vertical line (the B stem)
    draw.rectangle(
        [center_x - 50, center_y - 70, center_x - 30, center_y + 50],
        fill=gold
    )
    
    # Draw top curve of B
    draw.arc(
        [center_x - 50, center_y - 70, center_x + 30, center_y - 10],
        start=270,
        end=90,
        fill=gold,
        width=8
    )
    
    # Draw bottom curve of B  
    draw.arc(
        [center_x - 50, center_y - 10, center_x + 40, center_y + 60],
        start=270,
        end=90,
        fill=gold,
        width=8
    )
    
    # Add small sparkle/star elements (bazaar magic)
    # Top right sparkle
    draw.polygon(
        [
            (200, 50), (205, 65), (220, 70), (205, 75), 
            (200, 90), (195, 75), (180, 70), (195, 65)
        ],
        fill=gold
    )
    
    # Bottom left small sparkle
    draw.polygon(
        [
            (50, 180), (53, 188), (61, 191), (53, 194),
            (50, 202), (47, 194), (39, 191), (47, 188)
        ],
        fill=dark_gold
    )
    
    return img


def main():
    """Generate and save the icon."""
    # Create assets directory if it doesn't exist
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)
    
    # Create icon
    icon = create_icon()
    
    # Save as PNG
    png_path = assets_dir / "icon.png"
    icon.save(png_path, "PNG")
    print(f"Created: {png_path}")
    
    # Also create a simple .ico file (Windows icon)
    # For simplicity, we'll create a multi-resolution PNG that Windows can use
    ico_path = assets_dir / "icon.ico"
    
    # Create different sizes for ICO
    sizes = [256, 128, 64, 48, 32, 16]
    icons = []
    for s in sizes:
        resized = icon.resize((s, s), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # Save as ICO (using PIL's ICO format)
    icon.save(ico_path, format='ICO', sizes=[(i.width, i.height) for i in icons])
    print(f"Created: {ico_path}")
    
    print("Icon generation complete!")


if __name__ == "__main__":
    main()
