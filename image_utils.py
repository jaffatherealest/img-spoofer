"""
Image utilities for EXIF handling, format conversion, and resizing.
"""

from pathlib import Path
from typing import Optional, Tuple, List
from io import BytesIO

from PIL import Image, ExifTags, ImageOps
import numpy as np


SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}


def get_supported_images(directory: str) -> List[Path]:
    """
    Return list of supported image files in directory.

    Args:
        directory: Path to directory to scan

    Returns:
        List of Path objects for supported image files
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    images = []
    for ext in SUPPORTED_EXTENSIONS:
        images.extend(dir_path.glob(f"*{ext}"))
        images.extend(dir_path.glob(f"*{ext.upper()}"))

    return sorted(images, key=lambda p: p.name.lower())


def normalize_exif_orientation(image_path: str) -> Image.Image:
    """
    Load image and apply EXIF orientation, return normalized PIL Image.

    Args:
        image_path: Path to image file

    Returns:
        PIL Image with correct orientation
    """
    img = Image.open(image_path)

    # Apply EXIF orientation using ImageOps
    img = ImageOps.exif_transpose(img)

    # Convert to RGB if necessary (handles RGBA, P, L modes)
    if img.mode in ('RGBA', 'P', 'LA'):
        # Create white background for transparency
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            img = background
        else:
            img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    return img


def resize_to_target(
    image: Image.Image,
    target_size: Optional[Tuple[int, int]],
    preserve_aspect: bool = True
) -> Image.Image:
    """
    Resize image to target dimensions.

    Args:
        image: PIL Image to resize
        target_size: (width, height) tuple, or None to keep original
        preserve_aspect: If True, resize to fit within target while preserving aspect ratio

    Returns:
        Resized PIL Image
    """
    if target_size is None:
        return image

    target_w, target_h = target_size

    if preserve_aspect:
        # Resize to fit within target while preserving aspect ratio
        image.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        return image
    else:
        # Force exact dimensions
        return image.resize((target_w, target_h), Image.Resampling.LANCZOS)


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array (RGB format for albumentations)."""
    return np.array(image)


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert numpy array back to PIL Image."""
    return Image.fromarray(array.astype(np.uint8))


def save_as_jpeg(
    image: Image.Image,
    output_path: str,
    quality: int = 95
) -> None:
    """
    Save image as high-quality JPEG.

    Args:
        image: PIL Image to save
        output_path: Path to save to
        quality: JPEG quality (1-100)
    """
    # Ensure RGB mode
    if image.mode != 'RGB':
        image = image.convert('RGB')

    image.save(
        output_path,
        'JPEG',
        quality=quality,
        optimize=True,
        progressive=True
    )


def get_image_size_mb(image_path: str) -> float:
    """Get image file size in megabytes."""
    return Path(image_path).stat().st_size / (1024 * 1024)


def parse_target_size(size_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """
    Parse target size string like '1080x1350' into (width, height) tuple.

    Args:
        size_str: Size string in format 'WIDTHxHEIGHT' or None

    Returns:
        (width, height) tuple or None
    """
    if size_str is None:
        return None

    try:
        parts = size_str.lower().split('x')
        if len(parts) != 2:
            raise ValueError(f"Invalid size format: {size_str}")
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid size format '{size_str}'. Expected format: WIDTHxHEIGHT (e.g., 1080x1350)")
