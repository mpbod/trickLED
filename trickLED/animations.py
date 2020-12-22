from . import trickLED

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

    
class AnimationBase:
    """ Animation base class. """
    def __init__(self, pxl, interval=100, palette=None, **kwargs):
        if not isinstance(pxl, trickLED.TrickLED):
            raise ValueError('pxl must be an instance of TrickLED')
        self.pxl = pxl
        self.frame = 0
        self.interval = interval #delay between frames in ms
        self.palette = palette
        self.stripe_size = kwargs.get('stripe_size', 1)
        # number of pixels to calculate before copying from buffer
        self.calc_n = self.pxl.n # number of
        if 'lit_bits' in kwargs:
            if isinstance(kwargs['lit_bits'], trickLED.BitMap):
                self.lit_bits = kwargs['lit_bits']
            else:
                raise ValueError('lit_bits must be an instance of BitMap')
            self.setup(**kwargs)
        else:
            self.lit_bits = None

    def repeat_section(self, n):
        """ Copy one section of the buffer and fill the remainder with it. """

    def setup(self, **kwargs):
        """ Called once at the start of animation """
        if self.palette and len(self.palette):
            stripe_size = self.pxl.n / len(self.palette)
            for i in range(self.pxl.n):
                pi = trickLED.uint(i // stripe_size) % len(self.palette)
                self.pxl[i] = self.palette[pi]
        else:
            loc = trickLED.getrandbits(8)
            c1 = trickLED.color_wheel(loc, 200)
            c2 = trickLED.color_wheel(loc + 30, 50)
            self.pxl.fill_gradient(c1, c2)

    def calc_color(self, pos):
        """ Return the color for this position / frame """
        pass

    def calc_frame(self):
        """ Called before rendering each frame """
        self.pxl.scroll(1)

    async def play(self, max_iterations=0):
        self.frame = 0
        while max_iterations == 0 or self.frame < max_iterations:
            self.frame += 1
            self.calc_frame()
            self.pxl.write()
            await asyncio.sleep_ms(self.interval)


class LitBitsBase(AnimationBase):
    """ Animation where only some pixels are lit """
    def setup(self, **kwargs):
        self.stripe_size = 6
        if not self.lit_bits:
            self.lit_bits = trickLED.BitMap(self.pxl.n)
            self.lit_bits.repeat(trickLED.BITS_HIGH)

    def calc_color(self, pos):
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

