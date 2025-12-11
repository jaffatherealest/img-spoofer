# img-spoofer

Generate multiple image variants that pass perceptual hash checks while looking identical to humans. Built for marketing teams who need to post similar content without triggering duplicate detection.

## What it does

Takes your images and creates N variants of each. Every variant:
- Looks the same to human eyes (marketing-quality output)
- Has a different PDQ hash (Facebook's perceptual hashing algorithm)
- Gets saved to organized subfolders with full metadata

PDQ hashes with distance ≤31 are considered "similar" by most platforms. This tool generates variants with distances of 80-130+, making them register as completely different images.

## Quick Start

**Choose your OS for full setup:**
- [macOS Setup Guide](docs/setup-macos.md)
- [Windows Setup Guide](docs/setup-windows.md)

**Already have Python 3.10+ and git?**

```bash
git clone https://github.com/jaffatherealest/img-spoofer.git
cd img-spoofer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Drop images in `input/`, then:

```bash
python main.py spoof --input-dir input --output-dir output --variants 10
```

## Usage

### Basic Commands

```bash
# Generate 10 variants per image (default)
python main.py spoof --input-dir input --variants 10

# Dry run - see what would be generated without saving files
python main.py spoof --input-dir input --variants 10 --dry-run

# Target size for Threads/Instagram (1080x1350)
python main.py spoof --input-dir input --variants 12 --target-size 1080x1350

# Higher PDQ distance threshold (stricter uniqueness)
python main.py spoof --input-dir input --min-distance 50

# Check a single image's PDQ hash
python main.py check path/to/image.jpg

# Compare two images
python main.py compare original.jpg variant.jpg
```

### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input-dir`, `-i` | Folder with your original images | `input/` |
| `--output-dir`, `-o` | Where variants get saved | `output/` |
| `--variants`, `-n` | How many variants per image | 10 |
| `--min-distance` | Minimum PDQ distance from original | 32 |
| `--dry-run` | Preview mode, no files written | off |
| `--target-size` | Resize output (e.g., `1080x1350`) | original size |
| `--quality`, `-q` | JPEG quality 1-100 | 95 |
| `--verbose`, `-v` | Show detailed progress | off |

### Output Structure

```
output/
├── beach_photo/
│   ├── beach_photo_v01.jpg
│   ├── beach_photo_v02.jpg
│   └── ...
├── product_shot/
│   ├── product_shot_v01.jpg
│   └── ...
└── manifest.json
```

The `manifest.json` contains PDQ hashes, distances, and which augmentation recipe was used for each variant. Useful for tracking and debugging.

## Configuration

Most settings work via CLI flags. For repeated workflows, edit `config.yaml`:

```yaml
pdq:
  min_distance_from_original: 32
  min_distance_between_variants: 20

output:
  quality: 95
  target_size: null  # or "1080x1350"

generation:
  variants_per_image: 10
  max_attempts_per_variant: 100
```

## Examples

**Weekly content batch for Threads:**
```bash
python main.py spoof -i ~/Downloads/weekly_photos -o ~/Content/variants -n 12 --target-size 1080x1350
```

**Test run on a few images:**
```bash
python main.py spoof -i input -n 3 --dry-run --verbose
```

**Verify a variant is different enough:**
```bash
python main.py compare input/original.jpg output/original/original_v01.jpg
# Output: Hamming Distance: 98 - DIFFERENT (distance > 31)
```

## Supported Formats

**Input:** JPG, JPEG, PNG, WebP, HEIC
**Output:** JPEG (high quality, optimized)

## Troubleshooting

**"No supported images found"**
Check your input folder has images with supported extensions. The tool scans for `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`.

**Variants look too different**
The augmentation recipes are tuned for subtlety, but you can reduce intensity by editing `augmentations.py`. The `micro_transform` and `quality_shift` recipes make the smallest visual changes.

**Low PDQ quality warnings**
Some images (very simple, solid colors, tiny) produce low-quality PDQ hashes. These get skipped automatically. Use images with actual content/texture.

**High attempt counts**
If it's taking many attempts per variant, your images might be very uniform. This is normal for solid backgrounds or simple graphics.

## How It Works

See [Technical Documentation](docs/technical.md) for details on PDQ hashing and the augmentation pipeline.

## License

MIT
