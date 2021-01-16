from . import trickLED
from random import getrandbits, randrange


def stepped_color_wheel(stripe_size=20, brightness=10):
    """
    Generator that cycles through the color wheel creating stripes that fade to
    a slightly different hue

    :param stripe_size: Size of fading stripe
    :param brightness: Brightness (1-10)
    :return: color generator
    """
    cycle = 0
    mv = trickLED.int8(brightness * 25)
    while True:
        cn1 = cycle % 30
        cn2 = (cycle - 4) % 30
        c1 = trickLED.color_wheel(cn1 * 12, mv)
        c2 = trickLED.color_wheel(cn2 * 12, 25)
        inc = trickLED.step_inc(c1, c2, stripe_size - 1)
        for i in range(stripe_size):
            incs = [v * i for v in inc]
            yield tuple(map(trickLED.add8, c1, incs))
        cycle += 1


def striped_color_wheel(skip=0, stripe_size=10, brightness=10, start_hue=0):
    """
    Generator that cycles through the color wheel.

    :param skip: Number of steps on the color wheel to skip
    :param stripe_size: Number of times to repeat each color
    :param brightness: Brightness (1-10)
    :return: color generator
    """
    hue = start_hue
    if brightness > 10 or brightness < 1:
        raise ValueError('brightness must be between 1 and 10')
    mv = trickLED.int8(brightness * 25)
    while True:
        col = trickLED.color_wheel(hue, mv)
        for i in range(stripe_size):
            yield col
        hue = (hue + 1 + skip) % 255


def fading_color_wheel(skip=10, stripe_size=20, start_hue=0):
    """
    Cycle through color wheel while fading in and out

    :param skip: Number of steps on the color wheel to skip
    :param strip_size: Length of the fade in, fade out cycle where hue remains the same
    :param start_hue: Location on color wheel to begin
    :return: color generator
    """
    hs = stripe_size // 2
    hue = start_hue
    if skip == 0:
        skip = 1
    while True:
        for v in range(1, hs + 1):
            yield trickLED.color_wheel(hue, v * 25)
        for v in range(hs - 1, 0, -1):
            yield trickLED.color_wheel(hue, v * 25)
        yield 0, 0, 0
        hue = (hue + skip) % 255


def random_vivid(brightness=10):
    """
    Generate random vivid colors

    :return: color generator
    """
    shifts = ((16, 8),  # (p, s, 0),
          (8, 0),   # (0, p, s)
          (0, 16))  # (s, 0, p)
    mv = brightness * 25
    while True:
        cov = randrange(0, 2)
        prime = randrange(1, mv)
        second = mv - prime
        s = shifts[cov]
        val = prime << s[0] | second << s[1]
        yield tuple(val.to_bytes(3, 'big'))


def random_pastel(bpp=3, mask=None):
    """
    Generate random pastel colors.

    :param bpp: Bytes per pixel
    :param mask: Bit masks to control hue. (255, 0, 63) would give red to purple colors.
    :return: color generator
    """
    mi = 0
    bc = bpp * 8
    if mask:
        if bpp != len(mask):
            raise ValueError('The mask must contain the same number of items as bytes to be returned.')
        for i in range(bpp):
            mi = (mi << 8) | mask[i]
    else:
        mi = 2 ** bc - 1
    while True:
        val = getrandbits(bc) & mi
        yield tuple(val.to_bytes(bpp, 'big'))
