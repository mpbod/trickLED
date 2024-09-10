> This is a import from https://gitlab.com/scottrbailey/trickLED. Original work by @scottrbailey.

## Purpose ##
Provide a framework for doing addressable LED animations in Micropython. This is not as fast
or efficient as the FastLED for Arduino. But it is pretty easy to create your own custom animation. 
Many of the animations use Python generators for their colors.  You can make a custom 
animation by writing a color generator and passing it to an animation class like NextGen or SideSwipe.
Most of the included color generators are a dozen lines of code or less.

Watch the [demo video](https://www.youtube.com/watch?v=vLvrJPNvkvU) 
showing the available animations and color generators.

### Hardware Support 
It currently supports the ESP32. It runs on the ESP8266, but only with the precompiled byte code. 
If you are running on an ESP8266, copy over the *.mpy files instead of *.py. 

### TrickLED Examples
    import uasyncio as asyncio
    import trickLED
    from trickLED import animations
    from trickLED import generators
    
    # use TrickLED class instead of NeoPixel
    tl = trickLED.TrickLED(machine.Pin(26), 200)
    tl.fill((50, 50, 50), start_pos=0, end_pos=24) # fill first 25 pixels with white
    tl.fill_gradient(0xDC143C, 0xF08080, 25) # fill remaining with red gradient
    tl.write()
    ''' 
    If you have a long strip and an animation that is expensive to calculate, you can 
    set repeat_n and either stripe or mirror that section to the rest of the strip. 
    Once it is set on the TrickLED object, animations will automatically just calculate
    that section.
    '''
    tl.repeat_n = 50 
    tl.repeat_mode = tl.REPEAT_MODE_MIRROR # stripe is default
    
    # Python generators are awesome, ones that generate colors are awesomer
    cwg = generators.striped_color_wheel(hue_stride=5, stripe_size=1)
    tl.fill_gen(cwg) # fill our strip from the color generator
    tl.write()
    tl.scroll(1) # move pixels forward 1 position
    tl.blend_to_color(0, 50) # blend the strip with black at 50%

### Animation Examples
All animations are subclassed from the AnimationBase class. When making a new animation
you typically override the setup, and calc_frame methods. Additional keyword arguments to 
__init__() and play() are automatically added to the self.settings dict. 
All runtime info should be stored in the self.state dict.

    ani = animations.Fire(tl, interval=40)
    # settings can also be set by passing as keyword arguments to play()
    asyncio.run(ani.play(500, sparking=64, cooling=15))

### Additional Data Structures
When creating animations, we often have to store metadata about each pixel. Additional
array style data structures are provided to significantly reduce the memory footprint and 
provide additional utilities. Use BitMap store boolean information about our pixels,
for instance if they are lit or if they need blended. Use ByteMap to store one or more bytes 
per pixel.

    # 1 bit per pixel
    ani.lit = BitMap(80)
    ani.lit.repeat(0b11101110) # 1 off 4 on will be repeated 
    ani.lit.scroll(-1) # pattern is now 4 on 1 off
    ani.lit.randomize(25) # pattern is now random with approx 25% on

    # 1 byte per pixel
    ani.heat_map = ByteMap(80, bpi=1)
    ani.heat_map.fill(100)
    ani.heat_map[0] = 200
    ani.heat_map.scroll(1)

    # 3 bytes per pixel
    ani.palette = ByteMap(80, bpi=3)
    ani.palette.fill_gradient((0, 0, 200), (100, 100, 0))
    
