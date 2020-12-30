from . import trickLED

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


def gen_color_wheel(skip=0, stripe_size=1, brightness=10):
    """
    Generator that cycles through the color wheel.

    :param skip: Number of steps on the color wheel to skip
    :param stripe_size: Number of times to repeat each color
    :param brightness: Brightness (1-10)
    :return: color generator
    """
    pos = 0
    mv = trickLED.int8(brightness * 25)
    while True:
        for i in range(stripe_size):
            yield trickLED.colval(pos, mv)
        pos = (pos + 1 + skip) % 360


def gen_stepped_color_wheel(stripe_size=20, brightness=10):
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

    
class AnimationBase:
    """ Animation base class. """
    def __init__(self, pxl, interval=100, palette=None, **kwargs):
        """

        :param pxl: TrickLED pixels
        :param interval: millisecond pause between each frame
        :param palette: Color palette
        :param kwargs:
        """
        if not isinstance(pxl, trickLED.TrickLED):
            raise ValueError('pxl must be an instance of TrickLED')
        self.pxl = pxl
        self.frame = 0
        self.interval = interval #delay between frames in ms
        self.palette = palette
        self.stripe_size = kwargs.get('stripe_size', 1)
        # number of pixels to calculate before copying from buffer
        self.calc_n = self.pxl.n
        self.color_gen = None
        self.setup(**kwargs)

    def setup(self, **kwargs):
        """ Called once at the start of animation """
        if self.palette and len(self.palette):
            self.stripe_size = self.pxl.n / len(self.palette)
            for i in range(self.pxl.n):
                pi = trickLED.int8(i // self.stripe_size) % len(self.palette)
                self.pxl[i] = self.palette[pi]
        else:
            loc = trickLED.getrandbits(8)
            c1 = trickLED.color_wheel(loc, 200)
            c2 = trickLED.color_wheel(loc + 30, 50)
            self.pxl.fill_gradient(c1, c2)

    def calc_pixel(self, pos):
        """ Return the color for this position / frame """
        pass

    def calc_frame(self):
        """ Called before rendering each frame """
        pass

    async def play(self, max_iterations=0):
        self.frame = 0
        while max_iterations == 0 or self.frame < max_iterations:
            self.frame += 1
            self.calc_frame()
            self.pxl.write()
            await asyncio.sleep_ms(self.interval)


class LitBitsBase(AnimationBase):
    """ Animation where only some pixels are lit """
    def __init__(self, lit_bits=None, **kwargs):
        super().__init__(**kwargs)
        if lit_bits:
            if isinstance(lit_bits, trickLED.BitMap):
                self.lit_bits = lit_bits
            else:
                raise ValueError('lit_bits must be an instance of BitMap')
        else:
            self.lit_bits = trickLED.BitMap(self.pxl.n)

    def setup(self, **kwargs):
        self.stripe_size = 6
        if not self.lit_bits:
            self.lit_bits = trickLED.BitMap(self.pxl.n)
            self.lit_bits.repeat(trickLED.BITS_HIGH)

    def calc_pixel(self, pos):
        return self.palette[pos // self.stripe_size]

    def calc_frame(self):
        def_col = self.palette[self.frame]
        for i in range(self.calc_n):
            if self.lit_bits[i]:
                col = def_col
            else:
                col = (0, 0, 0)
            self.pxl[i] = col
        self.lit_bits.scroll(1)


class RandomJitter(AnimationBase):
    """ Generate random colors. Random colors will generally be pastels. """
    pass


class SpinningWheel(AnimationBase):
    def setup(self, **kwargs):
        self.pxl.fill(0)
        self.color_gen = gen_stepped_color_wheel(self.stripe_size)
        for i in range(self.pxl.n):
            self.pxl[i] = next(self.color_gen)

    def calc_frame(self):
        self.pxl.scroll(1)
        self.pxl[0] = next(self.color_gen)
