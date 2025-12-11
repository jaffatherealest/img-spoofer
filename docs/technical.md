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

### Key Discovery: Geometric Transforms Only

Through extensive testing, we found that **PDQ is extremely robust against pixel-level changes**:

| Transform | PDQ Distance |
|-----------|--------------|
| Pixel shift ±50 | 2-4 |
| Brightness +30 | 0-2 |
| JPEG compression | 0-2 |
| Gaussian noise | 2-8 |
| **2% crop** | **~32** |
| **3% crop** | **~64** |
| **2° rotation** | **~42** |

PDQ downsamples to ~64x64 grayscale before hashing. Pixel-level noise gets averaged out. Only **geometric transformations** (crops, rotations, perspective) reliably break the hash because they shift the spatial structure PDQ captures.

### Why geometric transforms work

PDQ's DCT operates on the overall spatial layout. When you:
- **Crop**: You shift which content maps to which DCT frequency bins
- **Rotate**: You redistribute content across the entire grid
- **Scale/shift**: You change what portion of the image dominates the hash

A 4-5% crop removes content from edges and redistributes everything inward, dramatically changing the frequency decomposition.

## Augmentation Recipes

The tool uses 6 geometric recipes. Each applies subtle spatial transformations that break PDQ hashing while remaining visually unnoticeable. All recipes use **border reflection** to avoid black edges.

### Recipe 1: Micro Crop

```
Crop 4-6% from edges randomly → resize back to original
```

Removes a small amount from each edge (randomly distributed) and resizes back. The content shift changes PDQ's frequency analysis. **Typical distance: 50-80**

### Recipe 2: Micro Rotate

```
Rotate 2-4° (random direction) → border reflection fill
```

Small rotation with mirrored edge fill. The spatial redistribution breaks the hash without visible artifacts. **Typical distance: 35-55**

### Recipe 3: Micro Perspective

```
Shift corners 3-5% inward randomly → perspective warp
```

Applies a subtle keystone/perspective effect by shifting the four corners slightly. Creates a barely perceptible warp. **Typical distance: 40-70**

### Recipe 4: Crop + Rotate

```
Crop 2-3% → then rotate 1.5-2.5°
```

Combines two transforms for stronger effect. The compound transformation produces reliably high distances. **Typical distance: 50-75**

### Recipe 5: Asymmetric Crop

```
Heavy crop (4-6%) from one random side
Light crop (1-2%) from other sides
```

Shifts the composition slightly by cropping more from one edge. Hard to notice but effective at breaking the hash. **Typical distance: 55-70**

### Recipe 6: Scale + Shift

```
Scale up 4-6% → random crop position back to original size
```

Zooms in slightly, then takes a random crop from the enlarged image. Changes which content appears at edges. **Typical distance: 50-85**

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
augmentations.py  Geometric transform recipes using OpenCV
pdq_checker.py    Hash computation, distance calculation
image_utils.py    EXIF handling, format conversion
config.yaml       Default settings
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `threatexchange` | Facebook's PDQ implementation |
| `opencv-python` | Geometric transformations |
| `Pillow` | Image I/O, format conversion |
| `numpy` | Array operations |
| `typer` | CLI framework |
| `rich` | Progress bars, tables |
| `PyYAML` | Config file parsing |

## Extending the Tool

### Adding a new recipe

In `augmentations.py`:

```python
def my_transform(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    # Apply geometric transformation using cv2
    # ...
    return result

# Add to registry
RECIPES['my_transform'] = my_transform
```

### Tuning for more aggressive changes

Increase the percentage parameters in recipes. Example:

```python
# Original (subtle)
crop_pct = random.uniform(0.04, 0.06)  # 4-6%

# More aggressive
crop_pct = random.uniform(0.06, 0.08)  # 6-8%
```

Higher percentages = more visual change = higher hash distances = potentially visible differences.

### Tuning for less visual change

Lower the percentages, but expect more retry attempts. Below ~3% crop or ~2° rotation, you may not reliably hit the distance threshold.

## Limitations

**Simple images:** Solid colors, gradients, and simple graphics produce low-quality PDQ hashes. The tool skips these.

**Platform-specific detection:** We target PDQ (Facebook's algorithm), but other platforms may use different methods. This tool doesn't guarantee evasion of all duplicate detection systems.

**Variant scaling:** The tool can generate 50+ variants per image, but efficiency drops as more variants are added (each new variant must differ from all existing ones). Sweet spot is 10-30 variants.

**Geometric changes required:** Pixel-level manipulations (brightness, noise, compression) do NOT break PDQ. Only geometric transforms work, which means very slight visual changes to composition.
