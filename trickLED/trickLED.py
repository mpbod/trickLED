import math
import struct

from random import getrandbits
from neopixel import NeoPixel
from micropython import const

BITS_LOW = const(15)             # 00001111
BITS_MID = const(60)             # 00111100
BITS_HIGH = const(240)           # 11110000
BITS_EVEN = const(85)            # 01010101
BITS_ODD = const(170)            # 10101010
BITS_NONE = const(0)             # 00000000
BITS_ALL = const(255)            # 11111111
BITS_ALL_32 = const(4294967295)  # 32 1s
FADE_IN = const(1)
FADE_OUT = const(2)
FADE_IN_OUT = const(3)


def blend(col1, col2, pct=50):
    """
    Blend color 1 with percentage of color 2

    :param col1: Color 1
    :param col2: Color 2
    :param pct: Percentage of color 2
    :return: color tuple
    """
    if 0 <= pct <= 100:      
        result = [0, 0, 0]
        for i in range(len(col1)):
            result[i] = uint8(col1[i] + (col2[i] - col1[i]) / 100 * pct)
        return tuple(result)
    else:
        return col1
    

def step_inc(c1, c2, steps):
    """ Calculate step increment to blend colors in n steps """
    return tuple((c2[i] - c1[i]) / steps for i in range(len(c1)))  


def uint8(val):
    if 0 <= val <= 255:
        return int(val)
    if val < 0:
        return 0
    else:
        return 255


def shift_color(col, steps):
    # brighten or dim a color (1 = brighten, -1 = dim)
    if steps > 0:
        return tuple([uint8(c << steps) for c in col])
    elif steps < 0:
        return tuple([c >> -steps for c in col])
    else:
        return col


def adjust_brightness(col, brightness=10):
    """
    Adjust brightness without converting to HSV

    :param col: Color
    :param brightness: Brightness 0-10
    :return: color tuple
    """
    if 1 <= brightness <= 10:
        if not any(col):
            # black
            mv = brightness * 25
            return tuple(mv for v in col)
        else:
            lit = [1 if v > 0 else 0 for v in col]
            max_val = max(col)
            adj = brightness * 25 / max_val
            val = []
            for i in range(len(col)):
                v = uint8(col[i] * adj)
                if v == 0 and lit[i]:
                    v = 1
                val.append(v)
            return tuple(val)
    if brightness == 0:
        return 0, 0, 0
    else:
        raise ValueError('brightness must be between 0 and 10')


def add8(a, b):
    return uint8(a + b)


def mult8(a, b):
    return uint8(a * b)


def sin8(v):
    """ """
    vr = v / 127.5 * math.pi
    return math.sin(vr)


def rgb2hsv(col):
    """
    Convert RGB color to HSV. Hue is 255 "degrees" instead of 360. Saturation and value are also 0-255 instead of 0-1.0.

    :param col: RGB color
    :return: HSV color
    """
    col = colval(col)
    r, g, b = col
    max_v = max(col)
    d = max_v - min(col)
    if d == 0 or max_v == 0:
        return 0, 0, max_v
    s = d / max_v * 255
    if r == max_v:
        h = (g - b) / d
    elif g == max_v:
        h = 2 + (b - r) / d
    else:
        h = 4 + (r - g) / d
    h *= 42.5
    if h < 0:
        h += 255
    return uint8(h), uint8(s), max_v


def color_wheel(hue, val=255):
    hue = uint8(hue) % 255
    pa = hue % 85
    ss = val / 85
    ci = uint8(ss * pa)
    cd = uint8(val) - ci
    if hue < 85:
        return cd, ci, 0
    elif hue < 170:
        return 0, cd, ci
    else:
        return ci, 0, cd


def heat_color(temp):
    """ """
    t192 = temp * 191 // 255
    heat_ramp = (t192 & 63) << 2
    if t192 < 64:
        return heat_ramp, 0, 0
    elif t192 < 128:
        return 255, heat_ramp, 0
    else:
        return 255, 255, heat_ramp


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


def colval(val, bpp=3):
    # allow the input of color values as ints (including hex) and None/0 for black
    if not val:
        val = (0,) * bpp
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
        self.wc = math.ceil(n / 32)
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
        if 0 <= i < self.n:
            return self.bit(i)
        else:
            raise IndexError('index out of range')

    def __setitem__(self, i, val):
        if 0 <= i < self._mi:
            #
            self.bit(i, val)
        else:
            raise IndexError('index out of range')

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
            n = math.ceil(self.wc * 4 / 3)
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
    Map some number of bytes to items. Values automatically wrap around instead of throwing index errors.
    Use for color palettes or keeping track of things like temperature during animations.
    """
    def __init__(self, n, bpi=3):
        """
        :param n: Number of items
        :param bpi: bytes per item
        """
        self.n = n
        self.bpi = bpi
        self.buf = bytearray(n * bpi)

    def __setitem__(self, key, value):
        value = bytes(colval(value, self.bpi))
        idx = key * self.bpi
        if 0 <= key < self.n:
            self.buf[idx:idx + self.bpi] = value
        elif key == self.n:
            self.buf += value
            self.n += 1
        else:
            raise IndexError('index out of range')

    def __getitem__(self, key):
        if isinstance(key, int):
            if 0 <= key < self.n:
                si = key * self.bpi
            elif -self.n < key < 0:
                si = (key + self.n) * self.bpi
            else:
                raise IndexError('index out of range')
            if self.bpi > 1:
                return tuple(self.buf[si: si + self.bpi])
            else:
                return self.buf[si]
        elif isinstance(key, slice):
            si = (key.start if key.start else 0) * self.bpi
            ei = (key.stop if key.stop else self.n) * self.bpi
            if key.step and (key.step < -1 or key.step > 1):
                step = key.step * self.bpi
            else:
                step = key.step
            return self.buf[si:ei:step]

    def __len__(self):
        return self.n

    def scroll(self, step=1):
        cut = self.bpi * -step
        self.buf = self.buf[cut:] + self.buf[:cut]

    def fill(self, val, start_pos=0, end_pos=None):
        val = colval(val, self.bpi)
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        for i in range(start_pos, end_pos + 1):
            self[i] = val

    def fill_gradient(self, v1, v2, start_pos=0, end_pos=None):
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        steps = end_pos - start_pos
        v1 = colval(v1, self.bpi)
        v2 = colval(v2, self.bpi)
        inc = step_inc(v1, v2, steps)
        for i in range(steps):
            val = tuple(uint8(v1[n] + inc[n] * i) for n in range(self.bpi))
            self[start_pos + i] = val
        self[end_pos] = v2


class TrickLED(NeoPixel):
    """ NeoPixels with benefits to aid in creating animations.
    """
    # repeat section 0-n, 0-n, 0-n
    REPEAT_MODE_STRIPE = const(1)
    # repeat section alternating backward and forward 0-n, n-0, 0-n
    REPEAT_MODE_MIRROR = const(2)

    def __init__(self, pin, n, repeat_n=None, repeat_mode=None, **kwargs):
        """
        :param pin: Data pin
        :param n: number of pixels
        :param repeat_n: If set, the first n pixels will be repeated across the rest of the strip 
        :param repeat_mode: Controls if section is repeated or mirrored (alternating between forward and reversed)
        :param kwargs: bpp, timing
        """
        super().__init__(pin, n, **kwargs)
        self.repeat_n = repeat_n
        self.repeat_mode = repeat_mode if repeat_mode else TrickLED.REPEAT_MODE_STRIPE

    def __setitem__(self, i, val):
        if 0 <= i < self.n:
            val = colval(val, self.bpp)
            super().__setitem__(i, val)
        else:
            raise IndexError('Assignment index out of range')

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
        col1 = colval(col1, self.bpp)
        col2 = colval(col2, self.bpp)
        inc = step_inc(col1, col2, steps)
        for i in range(steps):
            col = tuple(uint8(col1[n] + inc[n] * i) for n in range(len(col1)))
            self[start_pos + i] = col
        self[end_pos] = col2

    def fill_gen(self, gen, start_pos=0, end_pos=None):
        """
        Fill strip with with colors from a generator.
        :param gen: Color generator
        :param start_pos: Start position, defaults to beginning of strip
        :param end_pos: End position, defaults to end of strip
        """
        if end_pos is None or end_pos >= self.n:
            end_pos = self.n - 1
        for i in range(start_pos, end_pos + 1):
            self[i] = next(gen)

    def blend_to_color(self, color=0, pct=50, start_pos=0, end_pos=None):
        """
         Blend each pixel with color from start position to end position.

        :param color: Color to blend
        :param pct: Percentage of new color vs existing color
        :param start_pos: Start position, defaults to beginning of strip
        :param end_pos: End position
        """
        color = colval(color, self.bpp)
        last_col = (0,) * self.bpp
        blend_col = (0,) * self.bpp
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
        for i in range(start_pos, end_pos + 1):
            self[i] = tuple(shift_bits(x, shift) for x in self[i])

    def _repeat_stripe(self, n=None):
        """
        Copy the first n pixels and repeat them over the rest of the strip

        :param n: Number of pixels to copy (not the zero-based index!)
        """
        if n is None:
            n = self.repeat_n
        loc = jump = n * self.bpp
        end = self.n * self.bpp
        section = self.buf[0:jump]
        while loc + jump <= end:
            self.buf[loc:loc + jump] = section
            loc += jump
        if loc < end:
            self.buf[loc:end] = section[:(end - loc)]

    def _repeat_mirror(self, n=None):
        """ Copy the first n pixels and repeat them alternating directions """
        if n is None:
            n = self.repeat_n
        rl = n - 1
        d = -1
        setitem = super().__setitem__
        for i in range(n, self.n):
            setitem(i, self[rl])
            if 0 < rl < n:
                rl += 1 * d
            elif rl == 0:
                d = 1
            else:
                d = -1

    def write(self):
        if self.repeat_n:
            if self.repeat_mode == TrickLED.REPEAT_MODE_STRIPE:
                self._repeat_stripe()
            elif self.repeat_mode == TrickLED.REPEAT_MODE_MIRROR:
                self._repeat_mirror()
        super().write()


class TrickMatrix(NeoPixel):
    # All rows run in the same direction
    LAYOUT_STRAIGHT =  const(1)
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
        """ TODO: implement matrix scrolling """
        pass

    def vscroll(self, step):
        """ TODO: implement matrix scrolling """
        pass
