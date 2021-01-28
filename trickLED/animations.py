import time
from . import trickLED
from . import generators
from random import getrandbits

try:
    from random import randrange
except ImportError:
    randrange = trickLED.randrange

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio


def default_palette(n, brightness=200):
    rn = getrandbits(8)
    pal = trickLED.ByteMap(n)
    sa = 255 // n
    for i in range(n):
        pal[i] = trickLED.color_wheel((rn + sa * i) % 255, brightness)
    return pal


class AnimationBase:
    """ Animation base class. """
    FILL_MODE_SOLID = 'solid'
    FILL_MODE_MULTI = 'multi'

    def __init__(self, leds, interval=50, palette=None, generator=None, brightness=200, **kwargs):
        """
        :param leds: TrickLED object
        :param interval: millisecond pause between each frame
        :param palette: color palette
        :param generator: color generator
        :param brightness: set brightness 0-255
        :param kwargs: additional keywords will be saved to self.settings
        """
        if not isinstance(leds, trickLED.TrickLED):
            raise ValueError('leds must be an instance of TrickLED')
        self.leds = leds
        self.frame = 0
        self.palette = palette
        self.generator = generator
        # configuration values can also be set as keyword arguments to __init__ or run
        self.settings = {'interval': int(interval), 'stripe_size': int(1),
                         'scroll_speed': int(1), 'brightness': trickLED.uint8(brightness)}
        # stores run time information needed for the animation
        self.state = {}
        # number of pixels to calculate before copying from buffer
        if self.leds.repeat_n:
            self.calc_n = self.leds.repeat_n
        else:
            self.calc_n = self.leds.n
        for kw in kwargs:
            self.settings[kw] = kwargs[kw]

    def setup(self):
        """ Called once at the start of animation.  """
        pass

    def calc_frame(self):
        """ Called before rendering each frame """
        pass

    async def play(self, max_iterations=0, **kwargs):
        """
        Plays animation
        :param max_iterations: Number of frames to render
        :param kwargs: Any keys in the settings dictionary can be set by passing as keyword arguments
        """
        for kw in kwargs:
            self.settings[kw] = kwargs[kw]
        self.leds.fill(0)
        self.setup()
        self.frame = 0        
        ival = self.settings['interval']
        self.state['start_ticks'] = time.ticks_ms()
        try:
            while max_iterations == 0 or self.frame < max_iterations:
                self.frame += 1
                self.calc_frame()
                self.leds.write()
                await asyncio.sleep_ms(ival)
            self._print_fps()
        except KeyboardInterrupt:
            self._print_fps()
            return

    def _print_fps(self):
        st = self.state.get('start_ticks')
        if st is None:
            return
        et = time.ticks_ms()
        ival = self.settings.get('interval')
        fps = self.frame / time.ticks_diff(et, st) * 1000
        ifps = 1000 / ival if ival > 0 else 1000
        print('Actual fps: {:0.02f} - interval fps: {:0.02f}\n'.format(fps, ifps))


class LitBits(AnimationBase):
    """ Animation where only some pixels are lit.  You can scroll the colors and lit_bits independently at different
        speeds or in different directions. If you set lit_percent the lit pixels will be random instead of a
        repeating pattern.
    """
    def __init__(self, leds, scroll_speed=1, lit_scroll_speed=-1, lit_percent=None, **kwargs):
        """
        :param leds: TrickLED
        :param scroll_speed: Set speed and direction of color scroll.
        :param lit_scroll_speed: Set speed and direction of lit_bits.
        :param lit_percent: Approx percent of leds that will be lit when calling lit_bits.randomize().
                            If set lit_bits will be randomized instead of having a repeating pattern.
        :param kwargs:
        """
        super().__init__(leds, **kwargs)
        self.settings['scroll_speed'] = int(scroll_speed)
        self.settings['lit_scroll_speed'] = int(lit_scroll_speed)
        self.settings['lit_percent'] = lit_percent
        # controls which leds are lit and which are off
        self.lit = trickLED.BitMap(self.calc_n)
        if not self.settings['lit_percent']:
            self.lit.repeat(119)  # three on one off

    def setup(self):
        if self.palette is None:
            self.palette = default_palette(20)
        if self.settings.get('lit_percent'):
            self.lit.pct = self.settings.get('lit_percent')
            self.lit.randomize()

    def calc_frame(self):
        if self.settings['lit_percent'] and self.frame % 30 == 0:
            self.lit.randomize()
        pl = len(self.palette)
        for i in range(self.calc_n):
            if self.lit[i] == 1:
                col = self.palette[i % pl]
            else:
                col = 0
            self.leds[i] = col
        self.palette.scroll(self.settings.get('scroll_speed', 1))
        self.lit.scroll(self.settings.get('lit_scroll_speed', -1))


class Jitter(LitBits):
    """ Light random pixels and slowly fade them. """
    def __init__(self, leds, fade_percent=40, sparking=25, background=0x0a0a0a,
                 lit_percent=15, fill_mode=None, **kwargs):
        """
        :param leds: TrickLED
        :param fade_percent: Percent to fade colors each cycle
        :param sparking: Odds / 255 of sparking more pixels
        :param background: Background color of unsparked pixels
        :param lit_percent: Approximate percent of pixels to be lit when sparking
        :param fill_mode: fill sparked with either same color (solid)
                   or generate new color for each (multi).
        :param kwargs:
        """
        super().__init__(leds, **kwargs)
        self.settings['fade_percent'] = fade_percent
        self.settings['sparking'] = sparking
        self.settings['background'] = background
        self.settings['lit_percent'] = lit_percent
        self.settings['fill_mode'] = fill_mode or self.FILL_MODE_MULTI

    def setup(self):
        self.lit.pct = self.settings['lit_percent']
        self.settings['background'] = trickLED.colval(self.settings['background'])
        if not self.generator:
            self.generator = generators.random_pastel(bpp=self.leds.bpp)

    def calc_frame(self):
        bg = self.settings.get('background')
        fade_percent = self.settings.get('fade_percent')
        rv = getrandbits(8)
        fill_mode = self.settings.get('fill_mode')
        if rv < self.settings.get('sparking'):
            # sparking
            self.lit.randomize()
            spark_col = next(self.generator)
            for i in range(self.calc_n):
                if self.lit[i]:
                    if fill_mode == self.FILL_MODE_SOLID:
                        col = spark_col
                    else:
                        col = next(self.generator)
                    self.leds[i] = col
                else:
                    col = self.leds[i]
                    if col != bg:
                        col = trickLED.blend(col, bg, fade_percent)
                        self.leds[i] = col
        else:
            # not sparking
            for i in range(self.calc_n):
                if self.lit[i]:
                    col = trickLED.blend(self.leds[i], bg, fade_percent)
                else:
                    col = bg
                self.leds[i] = col


class NextGen(AnimationBase):
    """ Scroll the pixels filling the end with a color from a color generator.
        setting "blanks" will insert n blank pixels between each lit one.
    """
    def __init__(self, leds, generator=None, blanks=0, **kwargs):
        """
        :param leds: TrickLED object
        :param generator: Color generator
        :param blanks: Number of blanks to insert between colors
        :param kwargs:
        """
        if generator is None:
            generator = generators.striped_color_wheel(hue_stride=10, stripe_size=1)
        super().__init__(leds, generator=generator, **kwargs)
        self.settings['blanks'] = int(blanks)

    def setup(self):
        self.leds.fill(0)
        stripe_size = self.settings.get('stripe_size', 1)
        blanks = self.settings['blanks']
        for i in range(0, self.calc_n, blanks + 1):
            self.leds[i] = next(self.generator)

    def calc_frame(self):
        self.leds.scroll(1)
        if self.settings.get('blanks'):
            cl = self.settings.get('blanks') + 1
            if self.frame % cl == 0:
                self.leds[0] = next(self.generator)
            else:
                self.leds[0] = 0
        else:
            self.leds[0] = next(self.generator)


class SideSwipe(AnimationBase):
    """ Step back and forth through pixels while cycling through color generators at each direction change."""
    def __init__(self, leds, color_generators=None, **kwargs):
        super().__init__(leds, **kwargs)
        if color_generators:
            self.generators = color_generators
        else:
            self.generators = []
            self.generators.append(generators.random_vivid())
            self.generators.append(generators.striped_color_wheel(hue_stride=20, stripe_size=10))

    def setup(self):
        self.state['cycle'] = 0
        self.state['direction'] = 1
        self.state['loc'] = 0
        self.state['gen_idx'] = 0
        
    def calc_frame(self):
        gen = self.generators[self.state['gen_idx']]
        self.leds[self.state['loc']] = next(gen)
        nloc = self.state['loc'] + self.state['direction']
        if 0 <= nloc < self.calc_n:
            self.state['loc'] = nloc
        else:
            # reached the end increment cycle and reverse direction
            self.state['cycle'] += 1
            self.state['gen_idx'] = self.state['cycle'] % len(self.generators)
            self.state['direction'] *= -1


class Fire(AnimationBase):
    def __init__(self, leds, sparking=64, cooling=15, scroll_speed=1, hotspots=1, **kwargs):
        """
        :param leds: TrickLED object
        :param sparking: Odds / 255 of generating a new spark
        :param cooling: How much the flames are cooled.
        :param scroll_speed: Speed and direction that flames move.
        :param hotspots: Number of spark locations. One will always be placed on the edge.
        :param kwargs:
        """
        super().__init__(leds, **kwargs)
        self.heat_map = trickLED.ByteMap(leds.n, bpi=1)
        # Blend map keeps track of which positions need blended
        self._blend_map = trickLED.BitMap(self.calc_n)
        self.settings['sparking'] = sparking
        self.settings['cooling'] = cooling
        self.settings['scroll_speed'] = int(scroll_speed)
        self.settings['hotspots'] = max(hotspots, 1)
        # we map 256 heat levels to a palette of 64, 128 or 256, calculated in setup()
        self.settings['palette_shift'] = 0
        self._flash_points = None
        if 'palette' in kwargs:
            if len(kwargs['palette']) >= 64:
                self.palette = kwargs['palette']
            else:
                raise ValueError('Palette length should be at least 64')
        else:
            self.palette = trickLED.ByteMap(64, bpi=3)
            for i in range(64):
                self.palette[i] = trickLED.heat_color(i * 4)

    def setup(self):
        self.heat_map.fill(0)
        # add insertion points and calculate ranges to blend
        self._flash_points = set()
        if self.settings['scroll_speed'] > 0:
            # fire ascending
            self._flash_points.add(0)
            bmin = 0
            bmax = 11
        elif self.settings['scroll_speed'] < 0:
            # fire descending
            self._flash_points.add(self.calc_n - 1)
            bmin = -10
            bmax = 1
        else:
            self._flash_points.add(randrange(0, self.calc_n - 1))
            bmin = -5
            bmax = 6

        sect_size = self.calc_n // self.settings['hotspots']
        for i in range(1, self.settings['hotspots']):
            # add additional flash_points with some randomness so they are not exactly evenly spaced
            rn = getrandbits(4) - 8
            ip = sect_size * i + rn
            if not 0 < ip < self.calc_n:
                ip = min(max(ip, 0), self.calc_n - 1)
            self._flash_points.add(ip)

        # calculate blend_map
        self._blend_map.repeat(0)
        for fp in self._flash_points:
            for i in range(fp + bmin, fp + bmax):
                if 0 <= i < self.calc_n and i not in self._flash_points:
                    self._blend_map[i] = 1

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
        if self.settings['scroll_speed'] != 0:
            self.heat_map.scroll(self.settings['scroll_speed'])

        # calculate sparks at insertion points
        for ip in self._flash_points:
            spark = getrandbits(8)
            if spark <= self.settings['sparking']:
                # add a spark at insert_point with random heat between 192 and 255
                val = 224 + (spark & 31)
            else:
                val = (spark & 127) | 64
            self.heat_map[ip] = val
            if self.settings.get('debug'):
                print('Adding {} at {}'.format(val, ip))

        # cool and blend
        heat_map = trickLED.ByteMap(self.calc_n, bpi=1)
        cooling = self.settings['cooling']
        for i in range(self.calc_n):
            if self._blend_map[i]:
                if 0 < i < mi:
                    val = sum(self.heat_map[i-1:i+2]) / 3 - cooling
                elif i == 0:
                    val = sum(self.heat_map[0:2]) / 2 - cooling
                else:
                    val = sum(self.heat_map[-2:]) / 2 - cooling
            elif i in self._flash_points:
                # No cooling at flash points
                val = self.heat_map[i]
            else:
                val = self.heat_map[i] - cooling
            heat_map[i] = trickLED.uint8(val)
        self.heat_map = heat_map

        # convert heat map to colors
        ps = self.settings['palette_shift']
        for i in range(self.calc_n):
            self.leds[i] = self.palette[self.heat_map[i] >> ps]


class Convergent(AnimationBase):
    """ Light marches two at a time and meets in the middle """

    def __init__(self, leds, fill_mode=None, **kwargs):
        super().__init__(leds, **kwargs)
        self.settings['fill_mode'] = fill_mode or self.FILL_MODE_SOLID

    def setup(self):
        if self.palette is None:
            self.palette = default_palette(20)
        self.state['insert_points'] = [0, self.calc_n - 1]
        self.state['palette_idx'] = 0
        self.start_cycle()

    def start_cycle(self):
        self.state['movers'] = self.state['insert_points'][:]
        self.leds.fill(0)
        self.state['palette_idx'] = (self.state['palette_idx'] + 1) % len(self.palette)
        self.state['color'] = self.palette[self.state['palette_idx']]
        for ip in self.state['insert_points']:
            self.leds[ip] = self.state['color']

    def calc_frame(self):
        idir = 1
        mvr = []
        new_insert = False
        new_cycle = False
        for mv in self.state['movers']:
            ni = mv + idir
            idir *= -1
            if 0 <= ni < self.calc_n:
                if not any(self.leds[ni]):
                    self.leds[ni] = self.leds[mv]
                    self.leds[mv] = 0
                    mvr.append(ni)
                elif mv in self.state['insert_points']:
                    new_cycle = True
                else:
                    new_insert = True
            else:
                print("{} + {} out of range".format(mv, idir))
        if new_cycle:
            self.start_cycle()
            return
        if new_insert:
            if self.settings['fill_mode'] == self.FILL_MODE_MULTI:
                self.state['palette_idx'] = (self.state['palette_idx'] + 1) % len(self.palette)
                self.state['color'] = self.palette[self.state['palette_idx']]
            for ip in self.state['insert_points']:
                self.leds[ip] = self.state['color']
            mvr = self.state['insert_points'][:]
        self.state['movers'] = mvr


class Divergent(AnimationBase):

    def __init__(self, leds, fill_mode=None, **kwargs):
        super().__init__(leds, **kwargs)
        self.settings['fill_mode'] = fill_mode or self.FILL_MODE_SOLID

    def setup(self):
        if self.palette is None:
            self.palette = default_palette(20)
        self.state['palette_idx'] = 0
        hwp = self.calc_n // 2
        self.state['insert_points'] = [hwp, hwp+1]
        self.start_cycle()

    def start_cycle(self):
        self.state['movers'] = self.state['insert_points'][:]
        self.leds.fill(0)
        self.state['palette_idx'] = (self.state['palette_idx'] + 1) % len(self.palette)
        self.state['color'] = self.palette[self.state['palette_idx']]
        for ip in self.state['insert_points']:
            self.leds[ip] = self.state['color']

    def calc_frame(self):
        idir = -1
        mvr = []
        new_insert = False
        new_cycle = False
        for mv in self.state['movers']:
            ni = mv + idir
            idir *= -1
            if 0 <= ni < self.calc_n:
                if not any(self.leds[ni]):
                    self.leds[ni] = self.leds[mv]
                    self.leds[mv] = 0
                    mvr.append(ni)
                elif mv in self.state['insert_points']:
                    new_cycle = True
                else:
                    new_insert = True
            else:
                new_insert = True
        if new_cycle:
            self.start_cycle()
            return
        if new_insert:
            if self.settings['fill_mode'] == self.FILL_MODE_MULTI:
                self.state['palette_idx'] = (self.state['palette_idx'] + 1) % len(self.palette)
                self.state['color'] = self.palette[self.state['palette_idx']]
            for ip in self.state['insert_points']:
                self.leds[ip] = self.state['color']
            mvr = self.state['insert_points'][:]
        self.state['movers'] = mvr