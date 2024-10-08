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

    def test_color_wheel(self):
        # wheel is adjusted to 255 instead of 360
        c = trickLED.color_wheel(0, 255)
        self.assertEqual((255, 0, 0), c, 'incorrect color_wheel for red')
        c = trickLED.color_wheel(42, 200)
        self.assertEqual((102, 98, 0), c, 'incorrect color_wheel for red/green')
        c = trickLED.color_wheel(85, 255)
        self.assertEqual((0, 255, 0), c, 'incorrect color_wheel for green')
        c = trickLED.color_wheel(127, 100)
        self.assertEqual((0, 51, 49), c, 'incorrect color_wheel for green/blue')
        c = trickLED.color_wheel(170, 255)
        self.assertEqual((0, 0, 255), c, 'incorrect color_wheel for blue')
        c = trickLED.color_wheel(212, 60)
        self.assertEqual((29, 0, 31), c, 'incorrect color_wheel for blue/red')

    def test_uint(self):
        self.assertEqual(0, trickLED.uint8(-10), 'negative int8 value should return 0')
        self.assertEqual(100, trickLED.uint8(100.0), 'int8 should return return int')
        self.assertEqual(255, trickLED.uint8(256.0)), 'int8 should return maximum of 255'

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

        bm.repeat(255) # fill with 1s
        bm[0] = 0
        bm.scroll(1)
        self.assertEqual(0, bm[1], 'incorrect value for scroll(1)')
        bm.scroll(-101)
        self.assertEqual(0, bm[0], 'incorrect value for scroll(-1)')

    def test_byte_map(self):
        bm = trickLED.ByteMap(30, bpi=3)
        bm[20] = self.c1
        self.assertEqual(self.c1, bm[20], 'did not get value we stored back')
        bm.scroll(2)
        self.assertEqual(self.c1, bm[22], 'incorrect value returned after scroll')
        # (50, 200, 100)
        bm.fill(self.c2)
        self.assertEqual(self.c2, bm[29], 'incorrect value returned after fill')
        bm.add(5)
        self.assertEqual((55, 205, 105), bm[0], 'incorrect value after ByteMap.add int')
        bm.add((10, 0, 20))
        self.assertEqual((65, 205, 125), bm[0], 'incorrect value after ByteMap.add tuple')
        bm.sub((15, 5, 25))
        self.assertEqual(self.c2, bm[0], 'incorrect value after ByteMap.sub')
        bm.mul(2)
        self.assertEqual((100, 255, 200), bm[0], 'incorrect value after ByteMap.mul')
        bm.div((4, 1, 5))
        self.assertEqual((25, 255, 40), bm[0], 'incorrect value after ByteMap.div')

