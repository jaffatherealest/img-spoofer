"""
Image spoofing recipes that actually break PDQ hashing.

Reality: PDQ is robust against pixel-level changes. Only geometric
transformations (crops, rotations) reliably break the hash.

These recipes use minimal geometric changes that are hard to notice
in social media feeds but sufficient to evade duplicate detection.
"""

import random
from typing import Dict, List, Callable, Tuple

import cv2
import numpy as np


def micro_crop(image: np.ndarray) -> np.ndarray:
    """
    Recipe 1: Micro Crop (3-5% from edges)

    Crops a small amount from edges and resizes back.
    3% crop = distance ~64, 5% crop = distance ~80+
    """
    h, w = image.shape[:2]
    crop_pct = random.uniform(0.04, 0.06)  # 4-6%

    margin_h = int(h * crop_pct)
    margin_w = int(w * crop_pct)

    # Random which edges to crop more
    top = random.randint(0, margin_h)
    bottom = random.randint(0, margin_h)
    left = random.randint(0, margin_w)
    right = random.randint(0, margin_w)

    cropped = image[top:h-bottom, left:w-right]
    result = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

    return result


def micro_rotate(image: np.ndarray) -> np.ndarray:
    """
    Recipe 2: Micro Rotation (2-4 degrees)

    Rotates image by a small amount using border reflection
    to avoid black corners.
    """
    h, w = image.shape[:2]
    angle = random.uniform(2.0, 4.0) * random.choice([-1, 1])

    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Use border reflection to fill edges with mirrored pixels (no black corners)
    result = cv2.warpAffine(
        image, matrix, (w, h),
        borderMode=cv2.BORDER_REFLECT_101
    )

    return result


def center_zoom_crop(image: np.ndarray) -> np.ndarray:
    """
    Recipe 3: Center Zoom Crop

    Zooms into center of image by cropping edges uniformly.
    Doesn't distort proportions - safe for portraits.
    """
    h, w = image.shape[:2]

    # Crop 4-6% from all edges uniformly (zooms into center)
    crop_pct = random.uniform(0.04, 0.06)
    margin_h = int(h * crop_pct)
    margin_w = int(w * crop_pct)

    # Uniform crop from all sides
    cropped = image[margin_h:h-margin_h, margin_w:w-margin_w]
    result = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

    return result


def crop_and_rotate(image: np.ndarray) -> np.ndarray:
    """
    Recipe 4: Combined Crop + Rotation

    Crop combined with rotation for stronger effect.
    """
    # First apply crop
    h, w = image.shape[:2]
    crop_pct = random.uniform(0.02, 0.03)  # 2-3%
    margin = int(min(h, w) * crop_pct)

    cropped = image[margin:h-margin, margin:w-margin]
    cropped = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

    # Then apply rotation with border reflection (no black corners)
    angle = random.uniform(1.5, 2.5) * random.choice([-1, 1])
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    result = cv2.warpAffine(cropped, matrix, (w, h), borderMode=cv2.BORDER_REFLECT_101)

    return result


def asymmetric_crop(image: np.ndarray) -> np.ndarray:
    """
    Recipe 5: Asymmetric Crop

    Crops more from one side than the other.
    Changes composition slightly but hard to notice.
    """
    h, w = image.shape[:2]

    # More crop from one random side
    side = random.choice(['top', 'bottom', 'left', 'right'])
    heavy_crop = random.uniform(0.04, 0.06)  # 4-6%
    light_crop = random.uniform(0.01, 0.02)  # 1-2%

    if side == 'top':
        top = int(h * heavy_crop)
        bottom = int(h * light_crop)
        left = right = int(w * light_crop)
    elif side == 'bottom':
        bottom = int(h * heavy_crop)
        top = int(h * light_crop)
        left = right = int(w * light_crop)
    elif side == 'left':
        left = int(w * heavy_crop)
        right = int(w * light_crop)
        top = bottom = int(h * light_crop)
    else:
        right = int(w * heavy_crop)
        left = int(w * light_crop)
        top = bottom = int(h * light_crop)

    cropped = image[top:h-bottom, left:w-right]
    result = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

    return result


def scale_shift(image: np.ndarray) -> np.ndarray:
    """
    Recipe 6: Scale and Shift

    Scales up and shifts the crop window.
    """
    h, w = image.shape[:2]

    # Scale up by 4-6%
    scale = random.uniform(1.04, 1.06)
    new_h, new_w = int(h * scale), int(w * scale)

    scaled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # Random crop position
    max_offset_h = new_h - h
    max_offset_w = new_w - w

    offset_h = random.randint(0, max_offset_h)
    offset_w = random.randint(0, max_offset_w)

    result = scaled[offset_h:offset_h+h, offset_w:offset_w+w]

    return result


# Recipe registry
RECIPES: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    'micro_crop': micro_crop,
    'micro_rotate': micro_rotate,
    'center_zoom': center_zoom_crop,
    'crop_rotate': crop_and_rotate,
    'asymmetric_crop': asymmetric_crop,
    'scale_shift': scale_shift,
}


def get_recipe_names() -> List[str]:
    """Return list of available recipe names."""
    return list(RECIPES.keys())


def get_random_recipe(enabled_recipes: List[str] = None) -> Tuple[str, Callable]:
    """Get a random augmentation recipe."""
    if enabled_recipes is None:
        enabled_recipes = list(RECIPES.keys())

    recipe_name = random.choice(enabled_recipes)
    recipe_fn = RECIPES[recipe_name]

    return recipe_name, recipe_fn


def apply_augmentation(
    image: np.ndarray,
    recipe_name: str = None,
    enabled_recipes: List[str] = None
) -> Tuple[np.ndarray, str]:
    """
    Apply a geometric augmentation to break PDQ hash.
    """
    if recipe_name is not None:
        if recipe_name not in RECIPES:
            raise ValueError(f"Unknown recipe: {recipe_name}")
        return RECIPES[recipe_name](image), recipe_name

    # Pick a random recipe
    available = enabled_recipes or list(RECIPES.keys())
    name = random.choice(available)

    return RECIPES[name](image), name


def create_sized_recipe(recipe_name: str, height: int, width: int):
    """Compatibility function."""
    return RECIPES.get(recipe_name, micro_crop)
