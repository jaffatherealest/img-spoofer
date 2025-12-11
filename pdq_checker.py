"""
PDQ hashing and similarity verification using Facebook's threatexchange library.
"""

from typing import Tuple, List, Optional
from io import BytesIO

from PIL import Image
from threatexchange.signal_type.pdq.pdq_hasher import pdq_from_bytes


def get_pdq_hash_from_bytes(image_bytes: bytes) -> Tuple[str, int]:
    """
    Compute PDQ hash from image bytes.

    Args:
        image_bytes: Raw image bytes (JPEG, PNG, etc.)

    Returns:
        Tuple of (hex_hash, quality_score)
        hex_hash is 64-character hex string (256 bits)
        quality_score is 0-100, higher is better
    """
    pdq_hash, quality = pdq_from_bytes(image_bytes)
    return pdq_hash, quality


def get_pdq_hash_from_path(image_path: str) -> Tuple[str, int]:
    """
    Compute PDQ hash from image file path.

    Args:
        image_path: Path to image file

    Returns:
        Tuple of (hex_hash, quality_score)
    """
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    return get_pdq_hash_from_bytes(image_bytes)


def get_pdq_hash_from_pil(image: Image.Image, quality: int = 95) -> Tuple[str, int]:
    """
    Compute PDQ hash from PIL Image.

    Args:
        image: PIL Image object
        quality: JPEG quality for internal conversion

    Returns:
        Tuple of (hex_hash, quality_score)
    """
    # Convert PIL image to bytes (PDQ works on raw image bytes)
    buffer = BytesIO()

    # Ensure RGB mode
    if image.mode != 'RGB':
        image = image.convert('RGB')

    image.save(buffer, format='JPEG', quality=quality)
    image_bytes = buffer.getvalue()

    return get_pdq_hash_from_bytes(image_bytes)


def hamming_distance(hash1: str, hash2: str) -> int:
    """
    Compute hamming distance between two PDQ hashes.

    PDQ hashes are 64-character hex strings (256 bits).
    Hamming distance = number of differing bits.

    Args:
        hash1: First PDQ hash (64 hex chars)
        hash2: Second PDQ hash (64 hex chars)

    Returns:
        Number of differing bits (0-256)
    """
    if len(hash1) != 64 or len(hash2) != 64:
        raise ValueError(f"PDQ hashes must be 64 hex characters. Got {len(hash1)} and {len(hash2)}")

    # Convert hex to integers
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)

    # XOR and count bits
    xor_result = int1 ^ int2

    # Count number of 1 bits (differing positions)
    return bin(xor_result).count('1')


def is_unique(
    candidate_hash: str,
    original_hash: str,
    existing_hashes: List[str],
    min_dist_original: int = 32,
    min_dist_variants: int = 20
) -> Tuple[bool, Optional[str]]:
    """
    Check if candidate hash is unique enough from original and existing variants.

    Args:
        candidate_hash: Hash of the candidate variant
        original_hash: Hash of the original image
        existing_hashes: List of already-accepted variant hashes
        min_dist_original: Minimum hamming distance from original (>31 = "different")
        min_dist_variants: Minimum hamming distance between variants

    Returns:
        Tuple of (is_unique, reason)
        - is_unique: True if candidate passes all checks
        - reason: String explaining why it failed (None if passed)
    """
    # Check distance from original
    dist_from_original = hamming_distance(candidate_hash, original_hash)
    if dist_from_original < min_dist_original:
        return False, f"Too similar to original (distance={dist_from_original}, need >={min_dist_original})"

    # Check distance from all existing variants
    for i, existing_hash in enumerate(existing_hashes):
        dist_from_variant = hamming_distance(candidate_hash, existing_hash)
        if dist_from_variant < min_dist_variants:
            return False, f"Too similar to variant {i+1} (distance={dist_from_variant}, need >={min_dist_variants})"

    return True, None


def check_quality(quality_score: int, threshold: int = 50) -> Tuple[bool, Optional[str]]:
    """
    Check if PDQ quality score meets threshold.

    Args:
        quality_score: PDQ quality score (0-100)
        threshold: Minimum acceptable quality

    Returns:
        Tuple of (passes, reason)
    """
    if quality_score < threshold:
        return False, f"PDQ quality too low ({quality_score} < {threshold})"
    return True, None
