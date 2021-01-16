import time
from . import trickLED
from . import generators
from random import getrandbits, randrange

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

    
class AnimationBase:
    """ Animation base class. """
    def __init__(self, leds, interval=100, palette=None, generator=None, **kwargs):
        """

        :param leds: TrickLED pixels
        :param interval: millisecond pause between each frame
        :param palette: Color palette
        :param kwargs:
        """
        if not isinstance(leds, trickLED.TrickLED):
            raise ValueError('pxl must be an instance of TrickLED')
        self.leds = leds
        self.frame = 0
        self.interval = interval
        self.palette = palette
        self.generator = generator
        self.settings = {'stripe_size': 1}
        if 'speed' in kwargs:
            self.speed = kwargs['speed']
        else:
            self.speed = 1
        # number of pixels to calculate before copying from buffer
        if self.leds.repeat_n:
            self.calc_n = self.leds.repeat_n
        else:
            self.calc_n = self.leds.n

    def setup(self, **kwargs):
        """ Called once at the start of animation.  """
        if self.palette and len(self.palette) > 0:
            pl = len(self.palette)
            ss = self.settings['stripe_size'] = self.leds.n / pl
            for i in range(self.leds.n):
                pi = trickLED.int8(i // ss) % pl
                self.leds[i] = self.palette[pi]
        elif self.generator:
            self.leds.fill_gen(self.generator)
        else:
            loc = trickLED.getrandbits(8)
            c1 = trickLED.color_wheel(loc, 200)
            c2 = trickLED.color_wheel(loc + 30, 50)
            self.leds.fill_gradient(c1, c2)

    def calc_frame(self):
        """ Called before rendering each frame """
        self.leds.scroll(self.speed)

    async def play(self, max_iterations=0, **kwargs):
        self.setup(**kwargs)
        self.frame = 0
        st = time.ticks_ms()
        try:
            while max_iterations == 0 or self.frame < max_iterations:
                self.frame += 1
                self.calc_frame()
                self.leds.write()
                await asyncio.sleep_ms(self.interval)
            self._print_fps(st)
        except KeyboardInterrupt:
            self._print_fps(st)
            return

    def _print_fps(self, start_ticks):
        et = time.ticks_ms()
        fps = self.frame / time.ticks_diff(et, start_ticks) * 1000
        ifps = 1000 / self.interval if self.interval > 0 else 1000
        print('Actual fps: {:0.02f} - Interval fps: {:0.02f}'.format(fps, ifps))


class LitBits(AnimationBase):
    """ Animation where only some pixels are lit """
    def __init__(self, lit_bits=None, **kwargs):
        super().__init__(**kwargs)
        if lit_bits:
            if isinstance(lit_bits, trickLED.BitMap):
                self.lit_bits = lit_bits
            else:
                raise ValueError('lit_bits must be an instance of BitMap')
        else:
            self.lit_bits = trickLED.BitMap(self.leds.n)

    def setup(self, **kwargs):
        self.stripe_size = 6
        if not self.lit_bits:
            self.lit_bits = trickLED.BitMap(self.leds.n)
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
            self.leds[i] = col
        self.lit_bits.scroll(1)


class RandomJitter(AnimationBase):
    """ Generate random colors. Random colors will generally be pastels. """
    pass


class GenScroll(AnimationBase):
    """ Scroll the pixels filling the end with a color from a color generator  """
    def setup(self, **kwargs):
        self.leds.fill(0)
        stripe_size = self.settings['stripe_size'] if self.settings['stripe_size'] else 10
        if self.generator is None:
            self.generator = generators.stepped_color_wheel(stripe_size)
        for i in range(self.calc_n):
            self.leds[i] = next(self.generator)

    def calc_frame(self):
        self.leds.scroll(1)
        self.leds[0] = next(self.generator)


class SideSwipe(AnimationBase):
    """ Step back and forth through pixels while cycling through color generators at each direction change."""
    def __init__(self, leds, color_generators=None, **kwargs):
        super().__init__(leds, **kwargs)
        if color_generators:
            self.color_generators = color_generators
        else:
            self.color_generators = []
            self.color_generators.append(generators.random_vivid())
            self.color_generators.append(generators.striped_color_wheel(skip=20, stripe_size=10))

    def setup(self, **kwargs):
        self.settings['cycle'] = 0
        self.settings['direction'] = 1
        self.settings['loc'] = 0
        self.settings['gen_idx'] = 0
        
    def calc_frame(self):
        gen = self.color_generators[self.settings['gen_idx']]  
        self.leds[self.settings['loc']] = next(gen)
        nloc = self.settings['loc'] + self.settings['direction']
        if 0 <= nloc < self.calc_n:
            self.settings['loc'] = nloc
        else:
            # reached the end increment cycle and reverse direction
            self.settings['cycle'] += 1
            self.settings['gen_idx'] = self.settings['cycle'] % len(self.color_generators)
            self.settings['direction'] *= -1


class Fire(AnimationBase):
    def __init__(self, leds, sparking=64, cooling=30, speed=1, hotspots=1, **kwargs):
        """

        :param leds: TrickLED strip
        :param sparking: Odds / 255 of generating a new spark
        :param cooling: How much the flames are cooled.
        :param speed: Speed and direction that flames rise.
        :param hotspots: Number of spark locations. One will always be placed on the edge.
        :param kwargs:
        """
        super().__init__(leds, **kwargs)
        self.heat_map = trickLED.ByteMap(leds.n, bpi=1)
        # Blend map keeps track of which positions need blended
        self.blend_map = trickLED.BitMap(self.calc_n)
        self.sparking = sparking
        self.cooling = cooling
        self.speed = speed
        self.settings['hotspots'] = max(hotspots, 1)
        # we map 256 heat levels to a palette of 64, 128 or 256, calculated in setup()
        self.settings['palette_shift'] = 0
        self.insert_points = []
        if 'palette' in kwargs:
            if len(kwargs['palette']) >= 64:
                self.palette = kwargs['palette']
            else:
                raise ValueError('Palette length should be at least 64')
        else:
            self.palette = trickLED.ByteMap(64, bpi=3)
            for i in range(64):
                self.palette[i] = trickLED.heat_color(i * 4)

    def setup(self, **kwargs):
        self.blend_map.repeat(0)
        self.heat_map.fill(0)
        # add insertion points and calculate ranges to blend
        self.insert_points = []
        if self.speed > 0:
            self.settings['insert_points'].append(0)
            bmin = 0
            bmax = 10
        elif self.speed < 0:
            self.insert_points.append(self.calc_n - 1)
            bmin = -10
            bmax = 0
        else:
            self.insert_points.append(randrange(0, self.calc_n - 1))
            bmin = -5
            bmax = 5

        sect_size = self.calc_n // self.settings['hotspots']
        for i in range(1, self.settings['hotspots']):
            rn = getrandbits(4) - 8
            self.insert_points.append(sect_size * i + rn)
        self.blend_map.repeat(7)

        for ip in self.insert_points:
            si = max(ip + bmin, 0)
            ei = min(ip + bmax + 1, self.calc_n - 1)
            for i in range(si, ei):
                val = 0 if i == ip else 1
                self.blend_map[i] = val

        # determine if we are mapping 256 levels of heat to 64, 128 or 256 colors
        if len(self.palette) >= 256:
            self.settings['palette_shift'] = 0
        elif len(self.palette) >= 128:
            self.settings['palette_shift'] = 1
        else:
            self.settings['palette_shift'] = 2

    def calc_frame(self):
        cn = self.calc_n
        mi = cn - 1
        self.heat_map.scroll(self.speed)

        # calculate sparks at insertion points
        for ip in self.settings['insert_points']:
            spark = getrandbits(8)
            if spark <= self.sparking:
                # add a spark at insert_point with random heat between 192 and 255
                val = 224 + (spark & 31)
            else:
                val = (spark & 127) | 64
            self.heat_map[ip] = val
            if self.settings.get('debug'):
                print('Adding {} at {}'.format(val, ip))

        # cool and blend strip
        if self.speed < 0:
            rg = range(self.calc_n)
        else:
            rg = range(self.calc_n - 1, 0, -1)
        for i in rg:
            if self.blend_map[i]:
                si = i - 1 if i > 1 else 0
                ei = i + 1 if i < mi else i
                val = sum(self.heat_map[si:ei]) // (ei - si)
            else:
                val = self.heat_map[i]
            self.heat_map[i] = trickLED.int8(val - self.cooling)

        ps = self.settings['palette_shift']
        for i in range(self.calc_n):
            self.leds[i] = self.palette[self.heat_map[i] >> ps]


