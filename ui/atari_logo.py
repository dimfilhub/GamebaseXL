from PIL import Image, ImageDraw, ImageFont

BACKGROUND = (0, 0, 0)
FOREGROUND = (228, 0, 43)
SUPERSAMPLE = 4  # draw large, then shrink, for smooth edges


def _bezier(p0, p1, p2, steps=40):
    """Points along a quadratic Bezier curve."""
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / steps for i in range(steps + 1))]


class AtariLogo:
    """Draws the Atari 'Fuji' logo with a label ('XL') underneath on a black background."""

    # Logo drawn in a 200x200 box: a centre stem flaring into its base, and two arms
    # that sweep outward and up from the base.
    @staticmethod
    def _shapes():
        stem = (_bezier((91, 14), (92, 140), (84, 186))
                + _bezier((116, 186), (108, 140), (109, 14)))
        arm = (_bezier((4, 14), (22, 150), (66, 186))
               + _bezier((78, 186), (46, 105), (30, 14)))
        mirrored = [(200 - x, y) for x, y in arm]
        return [stem, arm, mirrored]

    @staticmethod
    def _font(size):
        for name in ("Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)

    @classmethod
    def render(cls, size, label="XL"):
        """Return an RGB image of exactly `size` (width, height)."""
        w, h = size
        big = Image.new("RGB", (w * SUPERSAMPLE, h * SUPERSAMPLE), BACKGROUND)
        draw = ImageDraw.Draw(big)
        text_h = 0.22 * h
        scale = min(w * 0.5, (h - text_h) * 0.85) / 200 * SUPERSAMPLE
        ox = (w * SUPERSAMPLE - 200 * scale) / 2
        oy = (h * SUPERSAMPLE - 200 * scale - text_h * SUPERSAMPLE) / 2 + 0.04 * h * SUPERSAMPLE
        for shape in cls._shapes():
            draw.polygon([(ox + x * scale, oy + y * scale) for x, y in shape], fill=FOREGROUND)
        font = cls._font(int(text_h * 0.8 * SUPERSAMPLE))
        draw.text((w * SUPERSAMPLE / 2, oy + 200 * scale + 0.06 * h * SUPERSAMPLE), label,
                  font=font, fill=FOREGROUND, anchor="mt")
        return big.resize((w, h), Image.LANCZOS)
