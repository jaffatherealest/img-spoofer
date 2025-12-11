#!/usr/bin/env python3
"""
Image Spoofing Tool - CLI Entry Point

Generate unique image variants that evade PDQ hash matching while
maintaining visual quality for marketing purposes.
"""

from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.table import Table

from image_utils import get_supported_images, get_image_size_mb
from spoofer import SpoofingConfig, process_images, save_manifest
from augmentations import get_recipe_names


app = typer.Typer(
    name="img-spoofer",
    help="Generate unique image variants that evade PDQ hash matching.",
    add_completion=False,
)
console = Console()


@app.command()
def spoof(
    input_dir: Path = typer.Option(
        Path("input"),
        "--input-dir", "-i",
        help="Directory containing original images",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    output_dir: Path = typer.Option(
        Path("output"),
        "--output-dir", "-o",
        help="Directory to save variant subfolders",
    ),
    variants: int = typer.Option(
        10,
        "--variants", "-n",
        help="Number of unique variants to generate per image",
        min=1,
        max=100,
    ),
    min_distance: int = typer.Option(
        32,
        "--min-distance",
        help="Minimum PDQ hamming distance from original (>31 = different)",
        min=1,
        max=256,
    ),
    max_attempts: int = typer.Option(
        100,
        "--max-attempts",
        help="Maximum augmentation attempts per variant before giving up",
        min=10,
        max=1000,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview mode - calculate hashes but don't write files",
    ),
    target_size: Optional[str] = typer.Option(
        None,
        "--target-size",
        help="Output size (e.g., '1080x1350' for Threads). Default: keep original",
    ),
    quality: int = typer.Option(
        95,
        "--quality", "-q",
        help="JPEG output quality (1-100)",
        min=1,
        max=100,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Show detailed logging",
    ),
):
    """
    Generate spoofed image variants.

    Takes images from INPUT_DIR and generates N variants per image,
    each with a PDQ hash distance >= MIN_DISTANCE from the original.
    Variants are saved to per-image subfolders in OUTPUT_DIR.
    """
    # Validate target size format if provided
    if target_size:
        try:
            parts = target_size.lower().split('x')
            if len(parts) != 2:
                raise ValueError()
            int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            console.print(f"[red]Invalid target size format: {target_size}[/red]")
            console.print("Expected format: WIDTHxHEIGHT (e.g., 1080x1350)")
            raise typer.Exit(1)

    # Find input images
    try:
        image_paths = get_supported_images(str(input_dir))
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if not image_paths:
        console.print(f"[yellow]No supported images found in {input_dir}[/yellow]")
        console.print("Supported formats: jpg, jpeg, png, webp, heic")
        raise typer.Exit(1)

    # Print summary
    console.print()
    console.print("[bold]Image Spoofing Tool[/bold]")
    console.print("=" * 40)
    console.print(f"Input directory:  {input_dir}")
    console.print(f"Output directory: {output_dir}")
    console.print(f"Images found:     {len(image_paths)}")
    console.print(f"Variants/image:   {variants}")
    console.print(f"Min PDQ distance: {min_distance}")
    console.print(f"Output quality:   {quality}%")
    if target_size:
        console.print(f"Target size:      {target_size}")
    if dry_run:
        console.print("[yellow]DRY RUN - no files will be written[/yellow]")
    console.print()

    # Warn about large images
    for img_path in image_paths:
        size_mb = get_image_size_mb(str(img_path))
        if size_mb > 10:
            console.print(f"[yellow]Warning: {img_path.name} is {size_mb:.1f}MB[/yellow]")

    # Create output directory
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Build config
    config = SpoofingConfig(
        variants_per_image=variants,
        min_distance_from_original=min_distance,
        min_distance_between_variants=20,
        max_attempts_per_variant=max_attempts,
        quality_threshold=50,
        output_quality=quality,
        target_size=target_size,
        enabled_recipes=None,  # Use all recipes
        dry_run=dry_run,
        verbose=verbose,
    )

    # Process images
    manifest = process_images(input_dir, output_dir, image_paths, config)

    # Save manifest (unless dry run)
    if not dry_run:
        save_manifest(manifest, output_dir)

    # Print summary table
    console.print()
    table = Table(title="Results Summary")
    table.add_column("Image", style="cyan")
    table.add_column("Variants", justify="right")
    table.add_column("Avg Distance", justify="right")
    table.add_column("Attempts", justify="right")
    table.add_column("Status", justify="center")

    for name, data in manifest["images"].items():
        if data["skipped_reason"]:
            status = f"[red]Skipped: {data['skipped_reason']}[/red]"
            table.add_row(name, "-", "-", "-", status)
        else:
            num_variants = len(data["variants"])
            avg_dist = sum(v["distance_from_original"] for v in data["variants"]) / max(num_variants, 1)
            attempts = data["total_attempts"]

            if num_variants == variants:
                status = "[green]OK[/green]"
            elif num_variants > 0:
                status = f"[yellow]{num_variants}/{variants}[/yellow]"
            else:
                status = "[red]Failed[/red]"

            table.add_row(
                name,
                str(num_variants),
                f"{avg_dist:.0f}",
                str(attempts),
                status,
            )

    console.print(table)

    # Final summary
    summary = manifest["summary"]
    console.print()
    console.print(f"[bold]Total:[/bold] {summary['total_variants']} variants from {summary['total_images']} images")
    console.print(f"[bold]Average PDQ distance:[/bold] {summary['avg_distance']}")
    console.print(f"[bold]Success rate:[/bold] {summary['success_rate']}")

    if not dry_run:
        console.print(f"[bold]Output:[/bold] {output_dir}/")
        console.print(f"[bold]Manifest:[/bold] {output_dir}/manifest.json")
    else:
        console.print("[yellow]DRY RUN complete - no files written[/yellow]")


@app.command()
def list_recipes():
    """List available augmentation recipes."""
    console.print("[bold]Available Augmentation Recipes[/bold]")
    console.print()

    recipes = get_recipe_names()
    for recipe in recipes:
        console.print(f"  - {recipe}")


@app.command()
def check(
    image_path: Path = typer.Argument(
        ...,
        help="Path to image file",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
):
    """Check PDQ hash and quality for a single image."""
    from pdq_checker import get_pdq_hash_from_path

    console.print(f"[bold]Checking: {image_path}[/bold]")

    try:
        pdq_hash, quality = get_pdq_hash_from_path(str(image_path))
        console.print(f"PDQ Hash:    {pdq_hash}")
        console.print(f"Quality:     {quality}")

        if quality < 50:
            console.print("[yellow]Warning: Quality below threshold (50)[/yellow]")
        else:
            console.print("[green]Quality OK[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def compare(
    image1: Path = typer.Argument(
        ...,
        help="Path to first image",
        exists=True,
    ),
    image2: Path = typer.Argument(
        ...,
        help="Path to second image",
        exists=True,
    ),
):
    """Compare PDQ hashes of two images."""
    from pdq_checker import get_pdq_hash_from_path, hamming_distance

    console.print(f"[bold]Comparing images[/bold]")
    console.print()

    try:
        hash1, qual1 = get_pdq_hash_from_path(str(image1))
        hash2, qual2 = get_pdq_hash_from_path(str(image2))

        distance = hamming_distance(hash1, hash2)

        console.print(f"Image 1: {image1.name}")
        console.print(f"  Hash:    {hash1[:32]}...")
        console.print(f"  Quality: {qual1}")
        console.print()
        console.print(f"Image 2: {image2.name}")
        console.print(f"  Hash:    {hash2[:32]}...")
        console.print(f"  Quality: {qual2}")
        console.print()
        console.print(f"[bold]Hamming Distance: {distance}[/bold]")

        if distance <= 31:
            console.print("[red]SIMILAR (distance <= 31)[/red]")
        else:
            console.print("[green]DIFFERENT (distance > 31)[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def scan(
    folder: Path = typer.Argument(
        ...,
        help="Folder containing images to scan",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    threshold: int = typer.Option(
        31,
        "--threshold", "-t",
        help="Distance threshold for 'similar' (<=threshold = similar)",
        min=0,
        max=256,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Save results to JSON file",
    ),
    show_all: bool = typer.Option(
        False,
        "--all", "-a",
        help="Show all pairs (by default only shows similar pairs)",
    ),
):
    """
    Scan a folder and compare all images against each other.

    Finds duplicate/similar images based on PDQ hash distance.
    By default only shows pairs with distance <= 31 (similar).
    """
    import json
    from itertools import combinations
    from pdq_checker import get_pdq_hash_from_path, hamming_distance
    from rich.progress import Progress

    # Find images
    try:
        image_paths = get_supported_images(str(folder))
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if len(image_paths) < 2:
        console.print(f"[yellow]Need at least 2 images to compare. Found: {len(image_paths)}[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold]Scanning {len(image_paths)} images in {folder}[/bold]")
    console.print()

    # Compute all hashes
    hashes = {}
    skipped = []

    with Progress() as progress:
        task = progress.add_task("[cyan]Computing hashes...", total=len(image_paths))

        for img_path in image_paths:
            try:
                pdq_hash, quality = get_pdq_hash_from_path(str(img_path))
                if quality >= 50:
                    hashes[img_path.name] = {
                        "path": str(img_path),
                        "hash": pdq_hash,
                        "quality": quality,
                    }
                else:
                    skipped.append((img_path.name, f"low quality ({quality})"))
            except Exception as e:
                skipped.append((img_path.name, str(e)))

            progress.update(task, advance=1)

    if skipped:
        console.print(f"[yellow]Skipped {len(skipped)} images:[/yellow]")
        for name, reason in skipped[:5]:  # Show first 5
            console.print(f"  - {name}: {reason}")
        if len(skipped) > 5:
            console.print(f"  ... and {len(skipped) - 5} more")
        console.print()

    # Compare all pairs
    image_names = list(hashes.keys())
    total_pairs = len(image_names) * (len(image_names) - 1) // 2

    console.print(f"Comparing {total_pairs} pairs...")

    results = []
    similar_count = 0

    with Progress() as progress:
        task = progress.add_task("[cyan]Comparing...", total=total_pairs)

        for img1, img2 in combinations(image_names, 2):
            distance = hamming_distance(hashes[img1]["hash"], hashes[img2]["hash"])

            is_similar = distance <= threshold
            if is_similar:
                similar_count += 1

            results.append({
                "image1": img1,
                "image2": img2,
                "distance": distance,
                "similar": is_similar,
            })

            progress.update(task, advance=1)

    # Sort by distance (most similar first)
    results.sort(key=lambda x: x["distance"])

    # Display results
    console.print()

    if show_all:
        display_results = results
        title = f"All Pairs ({len(results)} comparisons)"
    else:
        display_results = [r for r in results if r["similar"]]
        title = f"Similar Pairs (distance <= {threshold})"

    if display_results:
        table = Table(title=title)
        table.add_column("Image 1", style="cyan")
        table.add_column("Image 2", style="cyan")
        table.add_column("Distance", justify="right")
        table.add_column("Status", justify="center")

        for r in display_results[:50]:  # Limit to 50 rows
            if r["distance"] <= threshold:
                status = "[red]SIMILAR[/red]"
            elif r["distance"] <= 50:
                status = "[yellow]CLOSE[/yellow]"
            else:
                status = "[green]DIFFERENT[/green]"

            table.add_row(
                r["image1"][:30],
                r["image2"][:30],
                str(r["distance"]),
                status,
            )

        if len(display_results) > 50:
            table.add_row("...", "...", "...", f"[dim]+{len(display_results) - 50} more[/dim]")

        console.print(table)
    else:
        console.print(f"[green]No similar pairs found (all distances > {threshold})[/green]")

    # Summary
    console.print()
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  Images scanned: {len(hashes)}")
    console.print(f"  Total pairs:    {total_pairs}")
    console.print(f"  Similar pairs:  {similar_count} (distance <= {threshold})")

    if results:
        distances = [r["distance"] for r in results]
        console.print(f"  Min distance:   {min(distances)}")
        console.print(f"  Max distance:   {max(distances)}")
        console.print(f"  Avg distance:   {sum(distances) / len(distances):.1f}")

    # Save to JSON if requested
    if output:
        output_data = {
            "folder": str(folder),
            "threshold": threshold,
            "images": hashes,
            "comparisons": results,
            "summary": {
                "total_images": len(hashes),
                "skipped_images": len(skipped),
                "total_pairs": total_pairs,
                "similar_pairs": similar_count,
            }
        }
        with open(output, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[bold]Results saved to:[/bold] {output}")


if __name__ == "__main__":
    app()
