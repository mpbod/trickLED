import machine
import uasyncio as asyncio

import trickLED
from trickLED import animations


if __name__ == '__main__':
    p26 = machine.Pin(26)
    tl = trickLED.TrickLED(p26, 100)
    bm = trickLED.BitMap(100)
    bm.repeat(int('11001100', 2))
    pal = trickLED.ByteMap(10, bpi=3)
    for i in range(10):
        pal[i] = trickLED.color_wheel(i*36, 100)
    #ani = animations.AnimationBase(tl, palette=pal)
    ani = animations.LitBitsBase(tl, palette=pal, lit_bits=bm)
