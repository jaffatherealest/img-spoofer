# Technical Documentation

How img-spoofer actually works under the hood.

## PDQ Hashing

PDQ (Perceptual hashing using DCT and Quality) is Facebook's image fingerprinting algorithm. It's designed to identify "the same" image even after modifications like cropping, resizing, or compression.

### How PDQ works

1. **Resize** the image to a small fixed size (ignoring aspect ratio)
2. **Convert to grayscale** (luminance only)
3. **Apply DCT** (Discrete Cosine Transform) to get frequency components
4. **Extract 256 bits** from the DCT output based on threshold comparisons
5. **Output a 64-character hex string** (256 bits)

The result is a "fingerprint" that's:
- **Compact:** Just 64 hex characters
- **Perceptually stable:** Similar images produce similar hashes
- **Fast to compare:** Just count differing bits (Hamming distance)

### Hamming Distance

Two PDQ hashes are compared by counting how many bits differ between them. This is the Hamming distance.

```
Hash A: a1b2c3d4...
Hash B: a1b2c3e5...
         differs here → distance increases
```

**Facebook's threshold:** Distance ≤ 31 = "same image"

So to make an image appear "different," we need to push the hash distance above 31. This tool typically achieves distances of 80-130+.

### Quality Score

PDQ also outputs a quality score (0-100) indicating how "hashable" the image is. Low scores mean the image lacks distinctive features (solid colors, simple gradients). Images with quality < 50 are skipped because their hashes aren't reliable.

## The Spoofing Strategy

The goal: **change enough pixels to break the hash, but not enough for humans to notice.**

PDQ is robust to many transformations (it's designed to be), but it has limits. By combining multiple subtle changes, we can push past the similarity threshold while preserving visual quality.

### Why it works

PDQ operates on a heavily downsampled, grayscale version of the image. It captures the overall structure, not fine details. So we target changes that:

1. **Alter low-frequency structure** (crops, perspective shifts)
2. **Shift color distributions** (which affect grayscale conversion)
3. **Add pixel-level noise** (accumulates into hash differences)

Any single change might not be enough. Stacking multiple subtle transforms compounds the effect.

## Augmentation Recipes

The tool uses 6 "recipes" — predefined combinations of image transforms. Each run randomly selects a recipe and applies it with randomized parameters.

### Recipe 1: Subtle Crop + Color

```
RandomResizedCrop (scale 0.90-0.98)  → tiny edge crop, resize back
RandomBrightnessContrast (±0.08)    → slight exposure shift
GaussNoise (std 0.02-0.08)          → fine grain
```

Crops change the spatial layout PDQ sees. Even removing 5% from edges can shift the hash significantly.

### Recipe 2: Perspective Shift

```
Perspective (scale 0.02-0.05)       → nearly invisible keystone
HueSaturationValue                  → color cast
Blur then Sharpen                   → removes exact pixel patterns
```

Perspective transforms warp the image grid. Combined with blur/sharpen, this disrupts the DCT frequency patterns.

### Recipe 3: Color Temperature

```
Affine (translate ±2%, rotate ±3°)  → micro shift
RGBShift (±15 per channel)          → warm/cool cast
RandomGamma (0.9-1.1)               → midtone adjustment
```

Color shifts affect how the image converts to grayscale, which is what PDQ actually hashes.

### Recipe 4: Quality Shift

```
ImageCompression (quality 85-94)    → JPEG re-encode
UnsharpMask                         → edge enhancement
GaussNoise (std 0.01-0.04)          → light grain
```

JPEG recompression introduces block artifacts that change pixel values. Combined with sharpening, this creates a different texture.

### Recipe 5: Micro Transform

```
Affine (translate/rotate/scale/shear) → geometric wobble
ChannelShuffle (5% chance)            → rare RGB swap
ToGray (2% chance)                    → very rare desaturation
GaussNoise                            → texture
```

The affine transform with all parameters active creates compound spatial distortion.

### Recipe 6: Texture Noise

```
ISONoise                            → camera sensor-style noise
Posterize (7 bits)                  → subtle quantization
Emboss (low alpha)                  → faint edge highlight
RandomBrightnessContrast            → exposure tweak
```

ISO noise simulates real camera noise patterns, which are effective at breaking hash similarity.

## The Generation Loop

For each input image:

```
1. Load and normalize (EXIF orientation, RGB conversion)
2. Compute original PDQ hash
3. For each variant needed:
   a. Pick random recipe
   b. Apply augmentation
   c. Compute candidate PDQ hash
   d. Check distance from original (need ≥32)
   e. Check distance from already-accepted variants (need ≥20)
   f. If passes: save and record
   g. If fails: retry with different recipe/seed
   h. Give up after 100 attempts
4. Write manifest.json with all metadata
```

The inter-variant distance check (≥20) prevents generating near-duplicate variants. You want 10 different images, not 10 copies of the same variant.

## File Structure

```
main.py           CLI entry point (typer-based)
spoofer.py        Core generation loop, manifest writing
augmentations.py  Recipe definitions using albumentations
pdq_checker.py    Hash computation, distance calculation
image_utils.py    EXIF handling, format conversion
config.yaml       Default settings
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `threatexchange` | Facebook's PDQ implementation |
| `albumentations` | Image augmentation pipelines |
| `Pillow` | Image I/O, format conversion |
| `opencv-python` | Backend for albumentations |
| `numpy` | Array operations |
| `typer` | CLI framework |
| `rich` | Progress bars, tables |
| `PyYAML` | Config file parsing |

## Extending the Tool

### Adding a new recipe

In `augmentations.py`:

```python
def get_my_recipe() -> A.Compose:
    return A.Compose([
        A.SomeTransform(...),
        A.AnotherTransform(...),
    ])

# Add to registry
RECIPES['my_recipe'] = get_my_recipe
```

Enable it in `config.yaml`:

```yaml
generation:
  recipes_enabled:
    - subtle_crop_color
    - my_recipe
```

### Tuning for more aggressive changes

Increase transform parameters in the recipe functions. Example:

```python
# Original (subtle)
A.RandomBrightnessContrast(brightness_limit=0.08, ...)

# More aggressive
A.RandomBrightnessContrast(brightness_limit=0.15, ...)
```

Higher values = more visual change = higher hash distances = potentially visible differences.

### Tuning for less visual change

Lower transform parameters, but expect more retry attempts and potentially lower success rates for hitting the distance threshold.

## Limitations

**Simple images:** Solid colors, gradients, and simple graphics produce low-quality PDQ hashes. The tool skips these.

**Platform-specific detection:** We target PDQ (Facebook's algorithm), but other platforms may use different methods. This tool doesn't guarantee evasion of all duplicate detection systems.

**Diminishing returns:** After ~10 variants, you're likely to see more retries as the "unique hash space" for subtle modifications gets crowded.
