"""
Core spoofing logic: generate image variants that pass PDQ uniqueness checks.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from PIL import Image
from rich.console import Console
from rich.progress import Progress, TaskID

from image_utils import (
    normalize_exif_orientation,
    pil_to_numpy,
    numpy_to_pil,
    save_as_jpeg,
    resize_to_target,
    parse_target_size,
)
from pdq_checker import (
    get_pdq_hash_from_pil,
    hamming_distance,
    is_unique,
    check_quality,
)
from augmentations import (
    apply_augmentation,
    get_recipe_names,
    create_sized_recipe,
)


console = Console()


@dataclass
class VariantResult:
    """Result for a single generated variant."""
    filename: str
    hash: str
    distance_from_original: int
    recipe_used: str
    attempts: int


@dataclass
class ImageResult:
    """Result for processing a single input image."""
    original_path: str
    original_hash: str
    original_quality: int
    variants: List[VariantResult] = field(default_factory=list)
    failed_variants: int = 0
    total_attempts: int = 0
    skipped_reason: Optional[str] = None


@dataclass
class SpoofingConfig:
    """Configuration for spoofing operation."""
    variants_per_image: int = 10
    min_distance_from_original: int = 32
    min_distance_between_variants: int = 20
    max_attempts_per_variant: int = 100
    quality_threshold: int = 50
    output_quality: int = 95
    target_size: Optional[str] = None
    enabled_recipes: Optional[List[str]] = None
    dry_run: bool = False
    verbose: bool = False


def generate_variants_for_image(
    image_path: Path,
    output_dir: Path,
    config: SpoofingConfig,
    progress: Optional[Progress] = None,
    task_id: Optional[TaskID] = None,
) -> ImageResult:
    """
    Generate unique variants for a single image.

    Args:
        image_path: Path to input image
        output_dir: Directory to save variants
        config: Spoofing configuration
        progress: Optional rich Progress instance for updates
        task_id: Optional task ID for progress updates

    Returns:
        ImageResult with all generated variants and stats
    """
    result = ImageResult(
        original_path=str(image_path),
        original_hash="",
        original_quality=0,
    )

    # Load and normalize image
    try:
        original_pil = normalize_exif_orientation(str(image_path))
    except Exception as e:
        result.skipped_reason = f"Failed to load image: {e}"
        return result

    # Apply target size if specified
    target_size = parse_target_size(config.target_size)
    if target_size:
        original_pil = resize_to_target(original_pil, target_size)

    # Get original PDQ hash
    original_hash, original_quality = get_pdq_hash_from_pil(original_pil, config.output_quality)
    result.original_hash = original_hash
    result.original_quality = original_quality

    # Check quality threshold
    quality_ok, reason = check_quality(original_quality, config.quality_threshold)
    if not quality_ok:
        result.skipped_reason = reason
        return result

    # Convert to numpy for augmentation
    original_np = pil_to_numpy(original_pil)
    h, w = original_np.shape[:2]

    # Determine enabled recipes
    enabled_recipes = config.enabled_recipes or get_recipe_names()

    # Accepted variant hashes
    accepted_hashes: List[str] = []

    # Create output subfolder
    stem = image_path.stem
    image_output_dir = output_dir / stem
    if not config.dry_run:
        image_output_dir.mkdir(parents=True, exist_ok=True)

    # Generate variants
    variants_needed = config.variants_per_image
    variant_num = 0

    while len(result.variants) < variants_needed:
        variant_num += 1

        # Track attempts for this variant
        attempts_for_variant = 0
        variant_accepted = False

        while attempts_for_variant < config.max_attempts_per_variant:
            attempts_for_variant += 1
            result.total_attempts += 1

            # Apply random augmentation
            augmented_np, recipe_name = apply_augmentation(
                original_np,
                enabled_recipes=enabled_recipes
            )

            # Ensure correct size
            if augmented_np.shape[:2] != (h, w):
                import cv2
                augmented_np = cv2.resize(augmented_np, (w, h), interpolation=cv2.INTER_LANCZOS4)

            # Convert to PIL and get hash
            augmented_pil = numpy_to_pil(augmented_np)
            candidate_hash, candidate_quality = get_pdq_hash_from_pil(augmented_pil, config.output_quality)

            # Check quality
            if candidate_quality < config.quality_threshold:
                if config.verbose:
                    console.print(f"  [dim]Attempt {attempts_for_variant}: quality too low ({candidate_quality})[/dim]")
                continue

            # Check uniqueness
            unique, reject_reason = is_unique(
                candidate_hash,
                original_hash,
                accepted_hashes,
                config.min_distance_from_original,
                config.min_distance_between_variants,
            )

            if not unique:
                if config.verbose:
                    console.print(f"  [dim]Attempt {attempts_for_variant}: {reject_reason}[/dim]")
                continue

            # Variant accepted!
            distance = hamming_distance(candidate_hash, original_hash)
            variant_filename = f"{stem}_v{len(result.variants) + 1:02d}.jpg"
            variant_path = image_output_dir / variant_filename

            # Save (unless dry run)
            if not config.dry_run:
                save_as_jpeg(augmented_pil, str(variant_path), config.output_quality)

            # Record result
            variant_result = VariantResult(
                filename=variant_filename,
                hash=candidate_hash,
                distance_from_original=distance,
                recipe_used=recipe_name,
                attempts=attempts_for_variant,
            )
            result.variants.append(variant_result)
            accepted_hashes.append(candidate_hash)

            if config.verbose:
                console.print(
                    f"  [green]Variant {len(result.variants)}: "
                    f"distance={distance}, recipe={recipe_name}, "
                    f"attempts={attempts_for_variant}[/green]"
                )

            # Update progress
            if progress and task_id:
                progress.update(task_id, advance=1)

            variant_accepted = True
            break

        if not variant_accepted:
            # Failed to generate this variant after max attempts
            result.failed_variants += 1
            if config.verbose:
                console.print(
                    f"  [yellow]Failed to generate variant {variant_num} "
                    f"after {config.max_attempts_per_variant} attempts[/yellow]"
                )

            # Don't keep trying forever if we're struggling
            if result.failed_variants >= 3:
                if config.verbose:
                    console.print("  [red]Too many failures, stopping early[/red]")
                break

    return result


def process_images(
    input_dir: Path,
    output_dir: Path,
    image_paths: List[Path],
    config: SpoofingConfig,
) -> Dict[str, Any]:
    """
    Process multiple images and generate variants.

    Args:
        input_dir: Input directory path
        output_dir: Output directory path
        image_paths: List of image paths to process
        config: Spoofing configuration

    Returns:
        Manifest dictionary with all results
    """
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "config": {
            "min_distance": config.min_distance_from_original,
            "variants_per_image": config.variants_per_image,
            "output_quality": config.output_quality,
            "target_size": config.target_size,
        },
        "images": {},
        "summary": {
            "total_images": 0,
            "total_variants": 0,
            "skipped_images": 0,
            "avg_distance": 0,
            "success_rate": "0%",
        },
    }

    total_variants = 0
    total_distance = 0
    successful_images = 0

    with Progress() as progress:
        # Overall progress
        overall_task = progress.add_task(
            "[cyan]Processing images...",
            total=len(image_paths)
        )

        for image_path in image_paths:
            if config.verbose:
                console.print(f"\n[bold]Processing: {image_path.name}[/bold]")

            # Per-image variant progress
            variant_task = progress.add_task(
                f"  [dim]{image_path.name}[/dim]",
                total=config.variants_per_image
            )

            result = generate_variants_for_image(
                image_path,
                output_dir,
                config,
                progress,
                variant_task,
            )

            # Store in manifest
            manifest["images"][image_path.name] = {
                "original_hash": result.original_hash,
                "original_quality": result.original_quality,
                "variants": [asdict(v) for v in result.variants],
                "failed_variants": result.failed_variants,
                "total_attempts": result.total_attempts,
                "skipped_reason": result.skipped_reason,
            }

            # Update stats
            if result.skipped_reason:
                manifest["summary"]["skipped_images"] += 1
            else:
                successful_images += 1
                total_variants += len(result.variants)
                for v in result.variants:
                    total_distance += v.distance_from_original

            progress.update(overall_task, advance=1)
            progress.remove_task(variant_task)

    # Finalize summary
    manifest["summary"]["total_images"] = len(image_paths)
    manifest["summary"]["total_variants"] = total_variants

    if total_variants > 0:
        manifest["summary"]["avg_distance"] = round(total_distance / total_variants, 1)

    expected_variants = successful_images * config.variants_per_image
    if expected_variants > 0:
        success_pct = (total_variants / expected_variants) * 100
        manifest["summary"]["success_rate"] = f"{success_pct:.1f}%"

    return manifest


def save_manifest(manifest: Dict[str, Any], output_dir: Path) -> None:
    """Save manifest to JSON file."""
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
