
import struct
from math import ceil
from random import getrandbits
try:
    from neopixel import NeoPixel as _NeoPixel
except ImportError:
    class _NeoPixel:
        def __init__(self, pin, n, bpp=3):
            self.pin = pin,
            self.n = n
            self.bpp = bpp
            self.buf = bytearray(n * bpp)

        def write(self):
            pass


#from os import urandom as getrandbytes

BITS_LOW = 15  # 00001111
BITS_MID = 60  # 00111100
BITS_HIGH = 240  # 11110000
BITS_EVEN = 85  # 01010101
BITS_ODD = 170  # 10101010
BITS_ALL = 255  # 11111111
BITS_NONE = 0  # 00000000
BITS_ALL_32 = 4294967295 # 32 1s


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


def shift_color(col, steps):
    # brighten or dim a color (1 = brighten, -1 = dim)
    if steps > 0:
        return tuple([uint(c << steps) for c in col])
    elif steps < 0:
        return tuple([c >> -steps for c in col])
    else:
        return col


def color_wheel(pos, brightness=255, as_int=False):
    pos %= 360
    pa = pos % 120
    ss = brightness / 120
    ci = uint(ss * pa)
    cd = brightness - ci
    if pos < 120:
        val = (cd, ci, 0)
    elif pos < 240:
        val = (0, cd, ci)
    else:
        val = (ci, 0, cd)
    if as_int:
        return val[0] << 16 | val[1] << 8 | val[2]
    else:
        return val


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


def rand_color(bpp=3, mask=None):
    mi = 0
    bc = bpp * 8
    if mask:
        if bpp != len(mask):
            raise ValueError('The mask must contain the same number of items as bytes to be returned.')
        for i in range(bpp):
            mi = (mi << 8) | mask[i]
    else:
        mi = 2 ** bc - 1
    val = getrandbits(bc) & mi
    return tuple(val.to_bytes(bpp, 'big'))


def _colval(val, bpp=3):
    # allow the input of color values as ints (including hex) and None/0 for black
    if not val:
        val = (0, 0, 0)
    elif isinstance(val, int):
        val = tuple(val.to_bytes(bpp, 'big'))
    return val


def shift_bits(val, shift):
    # shift bits left if shift is positive, right if negative
    if shift > 0:
        return val << shift
    if shift < 0:
        return val >> -shift
    return val


class BitMap:
    """ Helper class to keep track of metadata about our pixels as a bit in a bytearray
        The values automatically wrap around instead of throwing an index error.
    """
    def __init__(self, n, pct=50):
        self.n = n
        # number of 32-bit words
        self.wc = ceil(n / 32)
        self._mi = self.wc * 32
        # Hamming weight, rough percentage of ones when randomizing
        self.pct = pct
        self.buf = bytearray(self.wc * 4)        

    def bit(self, idx, val=None):
        """ Get or set a single bit """
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
            return self.bit(i % self.n)

    def __setitem__(self, i, val):
        if 0 <= i < self._mi:
            #
            self.bit(i, val)
        else:
            raise IndexError('Index out of range')

    def scroll(self, steps):
        if steps > 0:
            src_mask = 2 ** (32 - steps) - 1
            src_shift = steps
            fill_mask = BITS_ALL_32 - src_mask
            fill_shift = steps - 32
            fill_loc = -1
        else:
            fill_mask = 2 ** -steps - 1
            fill_shift = 32 + steps
            fill_loc = 1
            src_mask = BITS_ALL_32 - fill_mask
            src_shift = steps
        if self.wc == 1:
            fill_loc = 0
        words = []
        for i in range(self.wc):
            val = struct.unpack('I', self.buf[i:i+4])[0]
            words.append(val)
        for i in range(self.wc):
            fill_idx = (i + fill_loc) % self.wc
            src = shift_bits((words[i] & src_mask), src_shift)
            fill = shift_bits((words[fill_idx] & fill_mask), fill_shift)
            self.buf[i * 4: i * 4 + 4] = struct.pack('I', src + fill)
                  
    def randomize(self, pct=None):
        """ fill buffer with random 1s and 0s. Use pct to control the approx percent of 1s """
        if pct is None:
            pct = self.pct
        buf = bytearray()
        for i in range(self.wc):
            buf += struct.pack('I', rand32(pct))
        self.buf = buf

    def repeat(self, val):
        """ fill buffer by repeating val """
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


class ByteMap:
    """
    """
    def __init__(self, n, bpi=3):
        self.n = n
        self.bpi = bpi
        self.buf = bytearray(n * bpi)

    def __setitem__(self, key, value):
        value = bytes(_colval(value, self.bpi))
        idx = key * self.bpi
        if 0 <= key < self.n:
            self.buf[idx:idx + self.bpi] = value
        elif key == self.n:
            self.buf += value
            self.n += 1
        else:
            raise IndexError('Index out of range')

    def __getitem__(self, key):
        idx = (key * self.bpi) % self.n
        return tuple(self.buf[idx: idx + self.bpi])

    def __len__(self):
        return self.n

    def scroll(self, step=1):
        cut = self.bpi * -step
        self.buf = self.buf[cut:] + self.buf[:cut]


class TrickLED(_NeoPixel): 
    """ """
    def __setitem__(self, i, val):
        if 0 <= i < self.n:
            val = _colval(val, self.bpp)
            super().__setitem__(i, val)
        else:
            raise IndexError('Index out of range')

    def scroll(self, step=1):
        """ Scroll the pixels some number of steps in the given direction.

        :param step: Number and direction to shift pixels
        """
        cut = self.bpp * -step
        self.buf = self.buf[cut:] + self.buf[:cut]

    def fill_solid(self, color, start_pos=0, end_pos=None):
        """
        Fill strip with a solid color from start position to end position

        :param color: Color to fill
        :param start_pos: Start position, defaults to beginning of strip
        :param end_pos: End position, defaults to end of strip
        """
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        for i in range(start_pos, end_pos + 1):
            self[i] = color

    def fill_gradient(self, col1, col2, start_pos=0, end_pos=None):
        """
        Fill strip with a gradient from col1 to col2. If positions are not given, the entire strip will be filled.

        :param col1: Starting color
        :param col2: Ending color
        :param start_pos: Start position, defaults to beginning of strip
        :param end_pos: End position, defaults to end of strip
        """
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        steps = end_pos - start_pos
        col1 = _colval(col1, self.bpp)
        col2 = _colval(col2, self.bpp)
        inc = step_inc(col1, col2, steps)
        for i in range(steps + 1):
            col = tuple(uint(col1[n] + inc[n] * i) for n in range(len(col1)))
            self[start_pos + i] = col


    def fill_random(self, start_pos=0, end_pos=None, mask=(BITS_MID, BITS_MID, BITS_MID)):
        """
        Fill strip with random colors from start position to end position. Random colors will generally
        be pastels. Use masks to control the hue and brightness.
        (255, 0, 127) will give bright reds/purples. (0, 15, 31) will give faint blues/greens.

        :param start_pos: Start position, defaults to beginning of strip
        :param end_pos: End position, defaults to end of strip
        :param mask: Bit masks for each color channel
        """
        mi = mask[0] << 16 | mask[1] << 8 | mask[2]
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        bl = self.bpp * 8
        for i in range(start_pos, end_pos + 1):
            self[i] = getrandbits(bl) & mi

    def blend_to_color(self, color, pct=50, start_pos=0, end_pos=None):
        """
         Blend each pixel with color from start position to end position.

        :param color: Color to blend
        :param pct: Percentage of new color vs existing color
        :param start_pos: Start position, defaults to beginning of strip
        :param end_pos: End position
        """
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

    def adjust(self, shift=1, start_pos=0, end_pos=None):
        """
        Brighten or dim each pixel from start position to end position.

        :param shift: Number of steps to shift each channel. 1 doubles all values -1 halves them
        :param start_pos: Start position, defaults to beginning of strip
        :param end_pos: End position, defaults to end of strip
        """
        if shift < -7 or shift > 7:
            raise ValueError('shift must be between -7 and 7')
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        if shift < 0:
            op = lambda x: x >> -shift
        elif shift > 0:
            op = lambda x: uint(x << shift)
        for i in range(start_pos, end_pos + 1):
            self[i] = tuple(op(x) for x in self[i])
        

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
        """
        Get or set the color of pixel at x,y coordinate
        """
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
        pass

    def vscroll(self, step):
        pass
