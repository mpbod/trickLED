import machine
import sys
try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import trickLED
from trickLED import animations
from trickLED import generators


def play(animation, n_frames, **kwargs):
    try:
        asyncio.run(animation.play(n_frames, **kwargs))
    except KeyboardInterrupt as e:
        animation._print_fps()
        raise e
    finally:
        # needed to reset state otherwise the animations will get all jumbled when ended with CTRL+C
        asyncio.new_event_loop()


def demo_animations(leds, n_frames=200):
    print('Demonstrating animations press CTRL+C to cancel... or wait about 2 minutes.')
    # store repeat_n so we can set it back if we change it
    leds_repeat_n = leds.repeat_n
    # LitBits
    ani = animations.LitBits(leds)
    print('LitBits settings: default')
    play(ani, n_frames)
    print('LitBits settings: lit_percent=50')
    play(ani, n_frames, lit_percent=50)
    
    # NextGen
    ani = animations.NextGen(leds)
    print('NextGen settings: default')
    play(ani, n_frames)
    print('NextGen settings: blanks=2, interval=150')
    play(ani, n_frames, blanks=2, interval=150)
    
    # Jitter
    ani = animations.Jitter(leds)
    print('Jitter settings: default')
    play(ani, n_frames)
    print('Jitter settings: background=0x020212, fill_mode=FILL_MODE_SOLID')
    ani.generator = generators.random_vivid()
    play(ani, n_frames, background=0x020212, fill_mode=ani.FILL_MODE_SOLID)
    
    # SideSwipe
    ani = animations.SideSwipe(leds)
    print('SideSwipe settings: default')
    play(ani, n_frames)
    
    if leds.n > 60:
        print('Setting leds.repeat_n = 40, set it back to {} if you cancel the demo'.format(leds_repeat_n))
        leds.repeat_n = 40
    
    # Fire
    ani = animations.Fire(leds)
    print('Fire settings: default')
    play(ani, n_frames)
    
    # Divergent
    ani = animations.Divergent(leds)
    print('Divergent settings: default')
    play(ani, n_frames)
    print('Divergent settings: fill_mode=FILL_MODE_MULTI')
    play(ani, n_frames, fill_mode=ani.FILL_MODE_MULTI)
    
    # Convergent
    ani = animations.Convergent(leds)
    print('Convergent settings: default')
    play(ani, n_frames)
    print('Convergent settings: fill_mode=FILL_MODE_MULTI')
    play(ani, n_frames, fill_mode=ani.FILL_MODE_MULTI)

    # Conjuction
    ani = animations.Conjunction(leds)
    print('Conjuction settings: default')
    play(ani, n_frames)
    
    if leds.repeat_n != leds_repeat_n:
        leds.repeat_n = leds_repeat_n


def demo_generators(leds, n_frames=200):
    print('Demonstrating generators:')
    # stepped_color_wheel  
    print('stepped_color_wheel')
    ani = animations.NextGen(leds, generator = generators.stepped_color_wheel())
    play(ani, n_frames)
    
    # striped_color_wheel
    print('stepped_color_wheel')
    ani.generator = generators.striped_color_wheel()
    play(ani, n_frames)
    print('stepped_color_wheel(stripe_size=1)')
    ani.generator = generators.striped_color_wheel(stripe_size=1)
    play(ani, n_frames)
    
    #fading_color_wheel
    print('fading_color_wheel(mode=FADE_OUT) (default)')
    ani.generator = generators.fading_color_wheel()
    play(ani, n_frames)
    print('fading_color_wheel(mode=FADE_IN)')
    ani.generator = generators.fading_color_wheel(mode=trickLED.FADE_IN)
    play(ani, n_frames)
    print('fading_color_wheel(mode=FADE_IN_OUT)')
    ani.generator = generators.fading_color_wheel(mode=trickLED.FADE_IN_OUT)
    play(ani, n_frames)
    
    # color_compliment
    print('color_compliment()')
    ani.generator = generators.color_compliment(stripe_size=10)
    play(ani, n_frames)
    
    # random_vivid
    print('random_vivid()')
    ani.generator = generators.random_vivid()
    play(ani, n_frames)
    
    # random_pastel
    print('random_pastel()')
    ani.generator = generators.random_pastel()
    play(ani, n_frames)
    print('random_pastel(mask=(127, 0, 31))')
    ani.generator = generators.random_pastel(mask=(127, 0, 31))
    play(ani, n_frames)
    print('random_pastel(mask=(0, 63, 63))')
    ani.generator = generators.random_pastel(mask=(0, 63, 63))
    play(ani, n_frames)


if __name__ == '__main__':
    if sys.platform == 'esp32':
        led_pin = machine.Pin(26)
    else:
        # labeled D2 on most ESP8266 boards
        led_pin = machine.Pin(4)

    tl = trickLED.TrickLED(led_pin, 12)
    # demo_animations(tl, 100)
    # demo_generators(tl, 100)

    play(ani, 200)