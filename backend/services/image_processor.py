"""Image processing service."""
from PIL import Image
import io
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Process images and extract metadata."""
    
    def process_image(self, file_path: str) -> Tuple[Image.Image, Dict]:
        """
        Process image and extract metadata.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Tuple of (PIL Image, metadata)
        """
        try:
            image = Image.open(file_path)
            
            # Extract metadata
            metadata = {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
                "size_bytes": None
            }
            
            # Get file size
            try:
                with open(file_path, 'rb') as f:
                    metadata["size_bytes"] = len(f.read())
            except Exception as e:
                logger.warning(f"Could not get file size: {e}")
            
            # Extract EXIF data if available
            if hasattr(image, '_getexif') and image._getexif():
                exif_data = image._getexif()
                metadata["exif"] = {k: str(v) for k, v in exif_data.items() if k and v}
            
            # Convert to RGB if necessary (for embedding generation)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            logger.info(f"Processed image: {metadata['width']}x{metadata['height']}, format: {metadata['format']}")
            
            return image, metadata
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    def resize_image(self, image: Image.Image, max_size: int = 512) -> Image.Image:
        """
        Resize image while maintaining aspect ratio.
        
        Args:
            image: PIL Image
            max_size: Maximum dimension size
            
        Returns:
            Resized PIL Image
        """
        if max(image.size) <= max_size:
            return image
        
        ratio = max_size / max(image.size)
        new_size = tuple([int(dim * ratio) for dim in image.size])
        
        return image.resize(new_size, Image.Resampling.LANCZOS)
    
    def image_to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """
        Convert PIL Image to bytes.
        
        Args:
            image: PIL Image
            format: Image format (PNG, JPEG, etc.)
            
        Returns:
            Image bytes
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()


# Global instance
_image_processor = None


def get_image_processor() -> ImageProcessor:
    """Get singleton image processor instance."""
    global _image_processor
    if _image_processor is None:
        _image_processor = ImageProcessor()
    return _image_processor
