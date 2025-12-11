"""
Augmentation recipes for image spoofing.

Goal: Change pixels enough to break PDQ hash while preserving visual quality.
Each recipe is designed for minimal visual change while maximizing PDQ hash difference.
"""

import random
import warnings
from typing import Dict, List, Callable

import albumentations as A
import numpy as np

# Suppress albumentations deprecation warnings
warnings.filterwarnings('ignore', category=UserWarning, module='albumentations')


def get_subtle_crop_color() -> A.Compose:
    """
    Recipe 1: Subtle Crop + Color
    - Tiny crop and resize back
    - Minor brightness/contrast adjustments
    - Very subtle noise
    """
    return A.Compose([
        A.RandomResizedCrop(
            size=(1, 1),  # Will be resized to match input
            scale=(0.90, 0.98),
            ratio=(0.95, 1.05),
            p=1.0
        ),
        A.RandomBrightnessContrast(
            brightness_limit=0.08,
            contrast_limit=0.08,
            p=0.9
        ),
        A.GaussNoise(
            std_range=(0.02, 0.08),
            p=0.8
        ),
    ])


def get_perspective_shift() -> A.Compose:
    """
    Recipe 2: Perspective Shift
    - Nearly invisible perspective warp
    - Subtle color adjustments
    - Light blur then sharpen
    """
    return A.Compose([
        A.Perspective(
            scale=(0.02, 0.05),
            keep_size=True,
            p=1.0
        ),
        A.HueSaturationValue(
            hue_shift_limit=8,
            sat_shift_limit=12,
            val_shift_limit=8,
            p=0.9
        ),
        A.OneOf([
            A.Blur(blur_limit=3, p=1.0),
            A.GaussianBlur(blur_limit=(3, 5), p=1.0),
        ], p=0.5),
        A.Sharpen(
            alpha=(0.1, 0.3),
            lightness=(0.9, 1.1),
            p=0.6
        ),
    ])


def get_color_temperature() -> A.Compose:
    """
    Recipe 3: Color Temperature
    - Small rotation and scale
    - RGB channel shifts
    - Gamma adjustments
    """
    return A.Compose([
        A.Affine(
            translate_percent={'x': (-0.02, 0.02), 'y': (-0.02, 0.02)},
            scale=(0.97, 1.03),
            rotate=(-3, 3),
            p=1.0
        ),
        A.RGBShift(
            r_shift_limit=15,
            g_shift_limit=15,
            b_shift_limit=15,
            p=0.9
        ),
        A.RandomGamma(
            gamma_limit=(90, 110),
            p=0.8
        ),
    ])


def get_quality_shift() -> A.Compose:
    """
    Recipe 4: Quality Shift
    - JPEG compression/recompression
    - Light sharpening
    - Subtle noise
    """
    return A.Compose([
        A.ImageCompression(
            quality_range=(85, 94),
            p=1.0
        ),
        A.UnsharpMask(
            blur_limit=(3, 5),
            sigma_limit=0.5,
            alpha=(0.2, 0.5),
            threshold=10,
            p=0.7
        ),
        A.GaussNoise(
            std_range=(0.01, 0.04),
            p=0.6
        ),
    ])


def get_micro_transform() -> A.Compose:
    """
    Recipe 5: Micro Transform
    - Tiny affine transformations
    - Occasional channel operations
    """
    return A.Compose([
        A.Affine(
            translate_percent={'x': (-0.02, 0.02), 'y': (-0.02, 0.02)},
            rotate=(-2, 2),
            scale=(0.98, 1.02),
            shear=(-1, 1),
            p=1.0
        ),
        A.ChannelShuffle(p=0.05),  # Very rare
        A.ToGray(p=0.02),  # Extremely rare - converts and loses color
        A.GaussNoise(
            std_range=(0.01, 0.03),
            p=0.5
        ),
    ])


def get_texture_noise() -> A.Compose:
    """
    Recipe 6: Texture Noise
    - ISO-like noise
    - Subtle posterization
    - Light emboss
    """
    return A.Compose([
        A.ISONoise(
            color_shift=(0.01, 0.05),
            intensity=(0.1, 0.3),
            p=0.9
        ),
        A.Posterize(
            num_bits=7,  # Subtle - still 128 levels per channel
            p=0.4
        ),
        A.Emboss(
            alpha=(0.1, 0.2),
            strength=(0.3, 0.5),
            p=0.3
        ),
        A.RandomBrightnessContrast(
            brightness_limit=0.05,
            contrast_limit=0.05,
            p=0.5
        ),
    ])


# Recipe registry
RECIPES: Dict[str, Callable[[], A.Compose]] = {
    'subtle_crop_color': get_subtle_crop_color,
    'perspective_shift': get_perspective_shift,
    'color_temperature': get_color_temperature,
    'quality_shift': get_quality_shift,
    'micro_transform': get_micro_transform,
    'texture_noise': get_texture_noise,
}


def get_recipe_names() -> List[str]:
    """Return list of available recipe names."""
    return list(RECIPES.keys())


def get_random_recipe(enabled_recipes: List[str] = None) -> tuple[str, A.Compose]:
    """
    Get a random augmentation recipe.

    Args:
        enabled_recipes: List of recipe names to choose from. If None, use all.

    Returns:
        Tuple of (recipe_name, augmentation_pipeline)
    """
    if enabled_recipes is None:
        enabled_recipes = list(RECIPES.keys())

    recipe_name = random.choice(enabled_recipes)
    recipe_fn = RECIPES[recipe_name]

    return recipe_name, recipe_fn()


def apply_augmentation(
    image: np.ndarray,
    recipe_name: str = None,
    enabled_recipes: List[str] = None
) -> tuple[np.ndarray, str]:
    """
    Apply a random augmentation recipe to an image.

    Args:
        image: Input image as numpy array (H, W, C) in RGB format
        recipe_name: Specific recipe to use. If None, pick random.
        enabled_recipes: List of enabled recipes to choose from.

    Returns:
        Tuple of (augmented_image, recipe_name_used)
    """
    if recipe_name is not None:
        if recipe_name not in RECIPES:
            raise ValueError(f"Unknown recipe: {recipe_name}. Available: {list(RECIPES.keys())}")
        name = recipe_name
        transform = RECIPES[name]()
    else:
        name, transform = get_random_recipe(enabled_recipes)

    # For RandomResizedCrop, we need to set the output size to match input
    # We'll create a wrapper that handles this
    h, w = image.shape[:2]

    # Create a new compose with correct size for crop operations
    augmented = transform(image=image)['image']

    # Ensure output is same size as input (some transforms may change size)
    if augmented.shape[:2] != (h, w):
        import cv2
        augmented = cv2.resize(augmented, (w, h), interpolation=cv2.INTER_LANCZOS4)

    return augmented, name


def create_sized_recipe(recipe_name: str, height: int, width: int) -> A.Compose:
    """
    Create a recipe with correct output size.

    For recipes that include RandomResizedCrop or similar size-changing transforms,
    this ensures the output matches the desired dimensions.

    Args:
        recipe_name: Name of the recipe
        height: Target height
        width: Target width

    Returns:
        Configured augmentation pipeline
    """
    if recipe_name == 'subtle_crop_color':
        return A.Compose([
            A.RandomResizedCrop(
                size=(height, width),
                scale=(0.90, 0.98),
                ratio=(0.95, 1.05),
                p=1.0
            ),
            A.RandomBrightnessContrast(
                brightness_limit=0.08,
                contrast_limit=0.08,
                p=0.9
            ),
            A.GaussNoise(
                std_range=(0.02, 0.08),
                p=0.8
            ),
        ])
    else:
        # Other recipes don't change size, use default
        return RECIPES[recipe_name]()
