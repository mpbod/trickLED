#import random
import struct
from math import ceil
from os import urandom as getrandbytes

from . import NPixel, uint, col_shift, rand32, Bits

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

    
class AnimationBase:
    """ Animation base class.  """
    def __init__(self, np, pallette=None, interval=100):
        if not isinstance(np, NPixel):
            raise ValueError('np must be an instance of NPixel')
        self.np = np
        self.frame = 0
        self.interval = interval #delay between frames in ms
        self.pallette = pallette
        self.init()

    def init(self):
        """ Initialization, called once as the start of animation """
        self.np.fill((50, 50, 50))

    def calc_frame(self):
        """ Called before rendering each frame """
        pass 

    async def animate(self, max_iterations=0):
        self.frame = 0
        while max_iterations == 0 or self.frame < max_iterations:
            self.frame += 1
            self.calc_frame()
            self.np.write()
            await asyncio.sleep_ms(self.interval)


class LitBitsBase(AnimationBase):
    """ Animation where only some pixels are lit """
    pass


class PalletteWalk(AnimationBase):
    def init(self):
        if self.pallette:
            pl = len(self.pallette)
            n = self.np.n
            for i in range(self.np.n):
                pi = i * pl // n
                self.np[i] = self.pallette[pi]
        else:
            self.np.fill((0, 0, 0))

    def calc_frame(self):
        self.np.scroll(1)


class RandomJitter(AnimationBase):
    """
    Generate random colors. Random colors will generally be pastels.
    Use shifts parameter to get more or less reds, greens and blues.
    This shifts bits right or left so +2 to -2 are plenty
    """
    def __init__(self, np, interval=100, pct=10, rgb_shifts=(0, 0, 0)):
        super().__init__(np, interval=interval)
        # Replacements per frame
        self.rpf = np.n
        if 1 <= replace_pct <= 99:
            self.rpf = np.n * replace_pct // 100
        if self.rpf < 1:
            self.rpf = 1
        # buffer is typically GRB but we want to take shifts as RGB
        rgb_shifts = (rgb_shifts[np.ORDER[0]],
                       rgb_shifts[np.ORDER[1]],
                       rgb_shifts[np.ORDER[2]])
        shift_fns = [None] * 3
        for i in range(3):
            val = rgb_shifts[i]
            if val < -8 or val > 8:
                raise ValueError('rgb_shift values must be between -8 and +8 (-2 to +2 is typical)')           
            if val > 0:
                shift_fns[i] = lambda x, s=val: uint(x << s)
            elif val < 0:
                shift_fns[i] = lambda x, s=val: x >> abs(s)
            else:
                shift_fns[i] = lambda x: x
            self.shift_fns = shift_fns

        
    def calc_frame(self):
        # determine which pixels we will replace
        bpp = self.np.bpp
        rep = choices(range(self.np.n), self.rpf)
        for i in range(self.np.n):
            if i in rep:
                # replace w/ random color
                col = getrandbytes(bpp)
                self.np[i] = col
            else:
                #dim
                self.np[i] = col_shift(self.np[i], -1)
