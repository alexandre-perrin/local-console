import io

import qrcode
from kivy.core.image import Image as CoreImage
from kivy.core.image import Texture
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers import SquareModuleDrawer

# Color tuple, whose components value range is [0, 255]
Color = tuple[int, ...]


def qr_object_as_texture(
    qr: qrcode.main.QRCode, background_color: Color, fill_color: Color
) -> Texture:
    """
    This function renders a QR code as a Kivy texture, so that an uix.Image widget
    can be updated without involving the filesystem
    :param qr: QR code object
    :param background_color: Background (i.e. space between cells) color for the QR code
    :param fill_color: Foreground (i.e. cell) color for the QR code
    :return: object that can be assigned to the .texture property of a kivy.uix.Image object
    """
    img = qr.make_image(
        image_factory=StyledPilImage,  # type: ignore[type-abstract]
        module_drawer=SquareModuleDrawer(),
        color_mask=SolidFillColorMask(
            front_color=fill_color, back_color=background_color
        ),
    )
    img_data = io.BytesIO()
    img_ext = "PNG"
    img.save(img_data, format=img_ext)
    img_data.seek(0)
    cim = CoreImage(img_data, ext=img_ext.lower())
    return cim.texture
