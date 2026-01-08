import os
from PIL import Image, ImageOps

def crop_signature(path):
    try:
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return

        print(f"Processing {path}...")
        img = Image.open(path).convert("RGB")
        
        # Invert color to find the black signature (which becomes bright) on the white background (which becomes dark)
        # logic: we want to find the bounding box of the "content"
        # If content is dark on light bg:
        inverted = ImageOps.invert(img)
        
        # We might need to threshold it to avoid JPEG noise
        # Convert to grayscale
        gray = inverted.convert("L")
        # Threshold: any pixel < 30 becomes 0, else 255 (cleanup noise)
        # Actually simplest is typical getbbox() on inverted usually works for distinct signatures
        
        bbox = inverted.getbbox()
        
        if bbox:
            print(f"  Found bounding box: {bbox}")
            # Crop the ORIGINAL image
            cropped = img.crop(bbox)
            
            # Save it back
            cropped.save(path)
            print("  Required whitespace removed. Saved.")
        else:
            print("  No bounding box found (image might be empty or full white).")

    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    base_dir = r"e:\quizmaster\quizsite\media\certificates"
    # Target the NEW files
    crop_signature(os.path.join(base_dir, "sig_jamal_new.png"))
    crop_signature(os.path.join(base_dir, "sig_najish_new.png"))
