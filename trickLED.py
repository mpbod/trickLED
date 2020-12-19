
import struct
from math import ceil
from random import getrandbits
from neopixel import NeoPixel as _NeoPixel
#from os import urandom as getrandbytes

BITS_LOW = 15  # 00001111
BITS_MID = 60  # 00111100
BITS_HIGH = 240  # 11110000
BITS_EVEN = 85  # 01010101
BITS_ODD = 170  # 10101010
BITS_ALL = 255  # 11111111
BITS_NONE = 0  # 00000000


def blend(col1, col2, pct=50):
    if 0 <= pct <= 100:      
        result = [0, 0, 0]
        for i in (0,1,2):
            result[i] = uint(col1[i] + (col2[i] - col1[i]) / 100 * pct)
        return tuple(result)
    else:
        return col1
    

def step_inc(c1, c2, steps):
    """ Calculate step increment to blend colors in n steps """
    return tuple((c2[i] - c1[i]) / steps for i in range(len(c1)))  


def uint(val):
    if 0 <= val <= 255:
        return int(val)
    if val < 0:
        return 0
    else:
        return 255  


def col_shift(col, steps):
    # brighten or dim a color (1 = brighten, -1 = dim)
    if steps > 0:
        return tuple([uint(c << steps) for c in col])
    elif steps < 0:
        return tuple([c >> -steps for c in col])
    else:
        return col


def color_wheel(pos, brightness=255):
    pos %= 360
    pa = pos % 120
    ss = 3 if brightness == 255 else brightness / 120
    ci = uint(ss * pa)
    cd = brightness - ci
    if pos < 120:
        return (cd, ci, 0)
    elif pos < 240:
        return (0, cd, ci)
    else:
        return (ci, 0, cd)


def rand32(pct):
    """Return a random 32 bit int with approximate percentage of ones."""
    # grb = random.getrandbits() ~ 50% 1's
    grb = getrandbits
    if pct < 1:
        return 0
    elif pct <= 6:
        return grb(32) & grb(32) & grb(32) & grb(32)
    elif pct <= 19:
        return grb(32) & grb(32) & grb(32)
    elif pct <= 31:
        return grb(32) & grb(32)
    elif pct <= 44:
        return grb(32) & (grb(32) | grb(32))
    elif pct <= 56:
        return grb(32)
    elif pct <= 69:
        return grb(32) | (grb(32) & grb(32))
    elif pct <= 81:
        return grb(32) | grb(32)
    elif pct <= 94:
        return grb(32) | grb(32) | grb(32)
    elif pct >= 100:
        return 2 ** 32 - 1
    else:
        return grb(32) | grb(32) | grb(32) | grb(32)


class BitMap():
    """ Helper class to keep track of metadata about our pixels as a bit in a bytearray """

    def __init__(self, n, pct=50):
        self.n = n
        # number of 32-bit words
        self.wc = ceil(n / 32)
        self._mi = self.wc * 32
        # Hamming weight, rough percentage of ones when randomizing
        self.pct = pct
        self.buf = bytearray(self.wc * 4)        

    def bit(self, idx, val=None):
        byte_idx = idx // 8
        bit_idx = idx % 8
        mask = 1 << bit_idx
        if val is None:
            return (self.buf[byte_idx] & mask) >> bit_idx
        if val == 0:
            self.buf[byte_idx] &= ~mask
        elif val == 1:
            self.buf[byte_idx] |= mask

    def __getitem__(self, i):
        if 0 <= i < self._mi:
            return self.bit(i)
        else:
            raise IndexError('Index out of range')

    def __setitem__(self, i, val):
        if 0 <= i < self._mi:
            #
            self.bit(i, val)
        else:
            raise IndexError('Index out of range')
                  
    def randomize(self):
        buf = bytearray()
        for i in range(self.wc):
            buf += struct.pack('I', rand32(self.pct))
        self.buf = buf

    def repeat(self, val):
        if not isinstance(val, int) or val >= 1 << 32:
            raise ValueError('Value error must be int')
        if val < 256:
            n = self.wc * 4
            v = val
            self.buf = bytearray([v] * n)
            return
        elif val < 1 << 16:
            n = self.wc * 2
            v = val.to_bytes(2, 'little')
        elif val < 1 << 24:
            n = ceil(self.wc * 3 / 4)
            v = val.to_bytes(3, 'little')
        else:
            n = self.wc
            v = struct.pack('I', val)

        buf = bytearray()
        for i in range(n):
            buf += v
        self.buf = buf[0:self.wc * 4]

    def print(self):
        p = '{:4d} | {:08b} {:08b} {:08b} {:08b} | {:4d}'
        print('     | ' + '76543210 ' * 4 + '|     ')
        print('-' * 49)
        for i in range(0, self.wc * 4, 4):
            bts = list(reversed(self.buf[i:i+4]))
            vals =[i * 8 + 31] + bts + [i * 8]
            print(p.format(*vals))


class TrickLED(_NeoPixel): 
    """ """
    def __setitem__(self, i, val):
        if 0 <= i < self.n:
            # allow input of int, including hex (0xFFAA99)
            if isinstance(val, int):
                val = val.to_bytes(self.bpp, 'big')
            super().__setitem__(i, val)
        else:
            raise IndexError('Index out of range')

    def scroll(self, step=1):
        """ Scroll the pixels n steps in +/- direction """
        cut = self.bpp * -step
        self.buf = self.buf[cut:] + self.buf[:cut]

    def fill_gradient(self, col1, col2, start_pos=0, end_pos=None):
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        steps = end_pos - start_pos      
        inc = step_inc(col1, col2, steps)
        for i in range(steps + 1):
            col = tuple(uint(col1[n] + inc[n] * i) for n in range(len(col1)))
            self[start_pos + i] = col

    def fill_solid(self, color, start_pos=0, end_pos=None):
        if end_pos is None or end_pos >= self.n:
                end_pos = self.n - 1
        for i in range(start_pos, end_pos + 1):
                self[i] = color

    def fill_random(self, start_pos=0, end_pos=None, mask=(BITS_MID, BITS_MID, BITS_MID)):
        """ """
        mi = mask[0] << 16 | mask[1] << 8 | mask[2]
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        bl = self.bpp * 8
        for i in range(start_pos, end_pos + 1):
            val = getrandbits(bl) & mi
            self[i] = val.to_bytes(3, 'big')

    def blend_to_color(self, color, pct=25, start_pos=0, end_pos=None):
        """ For each pixel between start_pos and end_pos, blend current color and parameter color """
        last_col = (0, 0, 0)
        blend_col = (0, 0, 0)
        if end_pos is None:
            end_pos = self.n - 1
        for i in range(start_pos, end_pos + 1):
            if self[i] == blend_col:
                continue
            elif self[i] == last_col:
                self[i] = blend_col
            else:
                last_col = self[i]
                blend_col = blend(self[i], color, pct)
                self[i] = blend_col
    
    def dim(self, steps=1):
        if steps < 1 or steps > 7:
            return
        for i in range(len(self.buf)):
            self.buf[i] = self.buf[i] >> steps

    def brighten(self, steps=1):
        if steps < 1 or steps > 7:
            return
        for i in range(len(self.buf)):
            self.buf[i] = (self.buf[i] << steps) & 255
        

class TrickMatrix(_NeoPixel):
    # All rows run in the same direction
    LAYOUT_STRAIGHT = 1
    # Direction of rows alternate from right to left
    LAYOUT_SNAKE = 2
    
    def __init__(self, pin, width, height, shape=None, **kwargs):
        if shape is None:
            self.shape = self.LAYOUT_SNAKE
        else:
            self.shape = shape
        self.width = width
        self.height = height
        super().__init__(pin, width * height, **kwargs)    
    
    def _idx(self, x, y):
        """ Return the index of the x, y coordinate """
        if x >= self.width or y >= self.height:
            raise IndexError('Out of bounds error. Dimensions are %d x %d' % (self.width, self.height))
        if y % 2 == 0 or self.shape == self.LAYOUT_STRAIGHT:
            return self.width * y + x
        else:
            return self.width * (y + 1) - x - 1          
        
    def pixel(self, x, y, color=None):
        idx = self._idx(x, y)
        if color is None:
            return self[idx]
        else:
            if isinstance(color, int):
                color = color.to_bytes(self.bpp, 'big')
            self[idx] = color
            
    def hline(self, x, y, width, color):
        for ix in range(x, x + width):
            self.pixel(ix, y, color)
    
    def vline(self, x, y, height, color):
        for iy in range(y, y + height):
            self.pixel(x, iy, color)
    
    def fill_rect(self, x, y, width, height, color):
        for iy in range(y, y + height):
            for ix in range(x, x + width):
                self.pixel(ix, iy, color)
    
    def hscroll(self, step):
        if step == 0 or abs(step) > self.width:
            return
        buf = self.buf
        w = self.width * self.bpp
        cut_odd = self.bpp * -step
        if self.shape == self.LAYOUT_SNAKE:
            cut_even = self.bpp * (self.width - step)
        else:
            cut_even = cut_odd
        for y in range(self.height):
            pass              

    def vscroll(self, step):
        pass
