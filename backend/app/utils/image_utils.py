import os
import uuid
import base64
from typing import Optional, Tuple
from PIL import Image
from io import BytesIO


UPLOADS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads"
)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def ensure_upload_dir():
    """Ensure that the uploads directory exists"""
    os.makedirs(UPLOADS_DIR, exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Check if the file has an allowed extension"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_image(
    file_data: bytes, original_filename: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Save an uploaded image to disk

    Args:
        file_data: The binary data of the file
        original_filename: The original filename

    Returns:
        Tuple of (success, message, file_path)
    """
    try:
        # Ensure the uploads directory exists
        ensure_upload_dir()

        # Check if the file has an allowed extension
        if not allowed_file(original_filename):
            return False, "File type not allowed", None

        # Generate a unique filename
        file_extension = original_filename.rsplit(".", 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"

        # Create the full file path
        file_path = os.path.join(UPLOADS_DIR, unique_filename)

        # Validate and save the image
        try:
            img = Image.open(BytesIO(file_data))
            img.verify()  # Verify it's a valid image

            # Reopen because verify() closes the file
            img = Image.open(BytesIO(file_data))
            img.save(file_path)

            return True, "File uploaded successfully", file_path
        except Exception as e:
            return False, f"Invalid image file: {str(e)}", None

    except Exception as e:
        return False, f"Error saving image: {str(e)}", None


def decode_base64_image(
    base64_string: str, prefix: str = "data:image/"
) -> Optional[bytes]:
    """
    Decode a base64 image string to bytes

    Args:
        base64_string: The base64 encoded image string
        prefix: The expected prefix (can be used for validation)

    Returns:
        The decoded image as bytes, or None if invalid
    """
    try:
        # Handle data URLs (e.g. "data:image/png;base64,...")
        if base64_string.startswith(prefix):
            # Extract the base64 part
            img_format, base64_data = base64_string.split(";base64,")
        else:
            base64_data = base64_string

        # Decode the base64 data
        return base64.b64decode(base64_data)
    except Exception as e:
        print(f"Error decoding base64 image: {str(e)}")
        return None
