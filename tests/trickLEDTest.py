import unittest
import trickLED

try:
    from machine import Pin
except ImportError:
    class Pin:
        OUT = 1

        def __init__(self, *args):
            pass

        def init(self, *args):
            pass


class TrickLEDTest(unittest.TestCase):
    def setUp(self):
        self.pixels = trickLED.TrickLED(Pin(26), 100)
        self.bitmap = trickLED.BitMap(100)
        self.bytemap = trickLED.ByteMap(100, bpi=3)
        self.c1 = (200, 100, 50)
        self.c2 = (50, 200, 100)

    def test_blend(self):
        cb = trickLED.blend(self.c1, self.c2, 50)
        self.assertEqual((125, 150, 75), cb, 'incorrect blend 50%')
        cb = trickLED.blend(self.c1, self.c2, 0)
        self.assertEqual(self.c1, cb, 'incorrect blend 0%')
        cb = trickLED.blend(self.c1, self.c2, 100)
        self.assertEqual(self.c2, cb, 'incorrect blend 100%')

    def test_step_inc(self):
        si = trickLED.step_inc(self.c1, self.c2, 10)
        self.assertEqual((-15.0, 10.0, 5.0), si, 'incorrect step increment')

    def test_adjust_brightness(self):
        col = (200, 50, 5)
        val = trickLED.adjust_brightness(col, 10)
        self.assertEqual(250, val[0], 'brightness=10 was not 250')

    def test_color_wheel(self):
        c = trickLED.color_wheel(60, 200)
        self.assertEqual((100, 100, 0), c, 'incorrect color for 60 red/green')
        c = trickLED.color_wheel(180, 100)
        self.assertEqual((0, 50, 50), c, 'incorrect color for 180 green/blue')
        c = trickLED.color_wheel(300, 60)
        self.assertEqual((30, 0, 30), c, 'incorrect blend for blue/red')

    def test_uint(self):
        self.assertEqual(0, trickLED.int8(-10), 'negative uint value should return 0')
        self.assertEqual(100, trickLED.int8(100.0), 'uint should return return int')
        self.assertEqual(255, trickLED.int8(256.0)), 'uint should return maximum of 255'

    def test_rand32(self):
        fmt = '{:032b}'
        v = trickLED.rand32(0)
        self.assertEqual(v, 0, 'rand32(0) should return 0')
        for i in range(12, 100, 12):
            v = trickLED.rand32(i)
            e = int(32 * i / 100)
            c = fmt.format(v).count('1')
            d = abs(c - e)
            self.assertLess(d, 6, f'rand32({i}) expected to return {e} 1s but got {c}')

    def test_colval(self):
        v = trickLED.colval(0xc86432)
        self.assertEqual(v, self.c1, 'failed to convert integer to color tuple')
        v = trickLED.colval(0xc8643264, 4)
        self.assertEqual(v, (200, 100, 50, 100), 'failed to convert 4 bytes int to color')
        v = trickLED.colval(None)
        self.assertEqual((0, 0, 0), v, '_colval(None) should return black')

    def test_shift_bits(self):
        v = trickLED.shift_bits(63, 1)
        self.assertEqual(126, v, 'incorrect value for shift left')
        v = trickLED.shift_bits(63, -1)
        self.assertEqual(31, v, 'incorrect value for shift right')
        v = trickLED.shift_bits(63, 0)
        self.assertEqual(63, v, 'incorrect value for noop')

    def test_bit_map(self):
        bm = trickLED.BitMap(100)
        # 1 byte repeat
        bm.repeat(trickLED.BITS_HIGH)
        self.assertEqual(trickLED.BITS_HIGH, bm.buf[4], 'bits were not repeated')
        self.assertEqual(16, len(bm.buf), 'buffer length changed during 1 byte repeat')
        # 2 byte repeat
        bm.repeat(trickLED.BITS_ALL << 8 | trickLED.BITS_ODD)
        self.assertEqual(16, len(bm.buf), 'buffer length changed during 2 byte repeat')
        self.assertEqual(bm.buf[0], bm.buf[12], 'bits were not repeated correctly')
        # repeat 3 byte sequence 11111111 01010101 00000000
        i = (trickLED.BITS_ALL << 16) | (trickLED.BITS_ODD << 8)
        bm.repeat(i)
        self.assertEqual(16, len(bm.buf), 'buffer length changed during 3 byte repeat')
        self.assertEqual(bm.buf[0], bm.buf[12], 'bits were not repeated correctly')
        # repeat 4 byte sequence 11111111 01010101 11111111 00000000
        i = trickLED.BITS_ALL << 24 | trickLED.BITS_ODD << 16 | trickLED.BITS_ALL << 8
        bm.repeat(i)
        self.assertEqual(16, len(bm.buf), 'buffer length changed during 4 byte repeat')
        self.assertEqual(bm.buf[0], bm.buf[12], 'bits were not repeated correctly')

        bm.scroll(-1)
        self.assertEqual(128, bm.buf[0], 'incorrect value for scroll(-1)')
        bm.scroll(9)
        self.assertEqual(255, bm.buf[0], 'incorrect value for scroll(9')

    def test_byte_map(self):
        bm = trickLED.ByteMap(30)
        bm[20] = self.c1
        self.assertEqual(self.c1, bm[20], 'did not get value we stored back')
        bm.scroll(2)
        self.assertEqual(self.c1, bm[22], 'incorrect value returned after scroll')