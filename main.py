import machine
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import time
import trickLED
from trickLED import animations
from trickLED import generators


if __name__ == '__main__':
    p26 = machine.Pin(26)
    tl = trickLED.TrickLED(p26, 12)
    bm = trickLED.BitMap(12)
    g1 = generators.random_pastel(mask=(191, 63, 0))
    g2 = generators.random_pastel(mask=(63, 191, 0))
    g3 = generators.random_pastel(mask=(0, 191, 63))
    g4 = generators.random_pastel(mask=(0, 63, 191))
    g5 = generators.random_pastel(mask=(63, 0, 191))
    g6 = generators.random_pastel(mask=(63, 0, 191))
    ani = animations.SideSwipe(tl, color_generators=[g1, g2, g3, g4, g5, g6], interval=50)
    fire = animations.Fire(tl, interval=40)
    fcw = generators.fading_color_wheel(5)
    ani_fcw = animations.GenScroll(tl, generator=fcw)
    #asyncio.run(ani.play(500))