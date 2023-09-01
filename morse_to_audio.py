#!/usr/bin/python3

import time 
import math
import numpy as np
import sounddevice as sd

# James Lemley K5DRU, Arduino code 2014-04-21, implemented from forum post by AE5AE http://forum.arduino.cc/index.php/topic,8243.0.html, 
# James Lemley K5DRU, converted to Python 2019-01-12
# James Lemley K5DRU, reworked to acually beep audio on a PC 2023-08-31

class morse_to_audio(object):

    # set constants

    #   Represent the letter, then the 
    #   number of bits, then a right-justified
    #   Morse word with 0 as dit and 1 as dah. 
    morse_symbols={
    '!': [  6,  int('00101011', 2)], #KW.digraph
    '"': [  6,  int('00010010', 2)],
    '“': [  6,  int('00010010', 2)],
    '”': [  6,  int('00010010', 2)],
    '$': [  7,  int('00001001', 2)],  #SX.digraph
    '&': [  5,  int('00001000', 2)],  #AS.digraph
    '(': [  5,  int('00010110', 2)],
    ')': [  6,  int('00101101', 2)],
    '+': [  5,  int('00001010', 2)],
    ',': [  6,  int('00110011', 2)],
    '-': [  6,  int('00100001', 2)],
    '—': [  6,  int('00100001', 2)], #treat emdash as dash
    '.': [  6,  int('00010101', 2)],
    '/': [  5,  int('00010010', 2)],
    '0': [  5,  int('00011111', 2)],
    '1': [  5,  int('00001111', 2)],
    '2': [  5,  int('00000111', 2)],
    '3': [  5,  int('00000011', 2)],
    '4': [  5,  int('00000001', 2)],
    '5': [  5,  int('00000000', 2)],
    '6': [  5,  int('00010000', 2)],
    '7': [  5,  int('00011000', 2)],
    '8': [  5,  int('00011100', 2)],
    '9': [  5,  int('00011110', 2)],
    ':': [  6,  int('00111000', 2)],
    ';': [  6,  int('00101010', 2)],
    '=': [  5,  int('00010001', 2)],
    '?': [  6,  int('00001100', 2)],
    '@': [  6,  int('00011010', 2)],
    'A': [  2,  int('00000001', 2)],
    'B': [  4,  int('00001000', 2)],
    'C': [  4,  int('00001010', 2)],
    'D': [  3,  int('00000100', 2)],
    'E': [  1,  int('00000000', 2)],
    'F': [  4,  int('00000010', 2)],
    'G': [  3,  int('00000110', 2)],
    'H': [  4,  int('00000000', 2)],
    'I': [  2,  int('00000000', 2)],
    'J': [  4,  int('00000111', 2)],
    'K': [  3,  int('00000101', 2)],
    'L': [  4,  int('00000100', 2)],
    'M': [  2,  int('00000011', 2)],
    'N': [  2,  int('00000010', 2)],
    'O': [  3,  int('00000111', 2)],
    'P': [  4,  int('00000110', 2)],
    'Q': [  4,  int('00001101', 2)],
    'R': [  3,  int('00000010', 2)],
    'S': [  3,  int('00000000', 2)],
    'T': [  1,  int('00000001', 2)],
    'U': [  3,  int('00000001', 2)],
    'V': [  4,  int('00000001', 2)],
    'W': [  3,  int('00000011', 2)],
    'X': [  4,  int('00001001', 2)],
    'Y': [  4,  int('00001011', 2)],
    'Z': [  4,  int('00001100', 2)],
    '\'': [ 6,  int('00011110', 2)],
    '’': [ 6,  int('00011110', 2)],
    '‘': [ 6,  int('00011110', 2)],
    '_': [  6,  int('00001101', 2)]  # Not.in.ITU-R.recommendation
    }

    def __init__(self, wpm=35, amplitude=0.2, frequency=500, Farnsworth=False, doubleFarnsworth=False, declick_cycles=1.5):
        # portions of this sinewave generation code borrowed from python-sounddevice/examples/play_sine.py 
        # which is at https://github.com/spatialaudio/python-sounddevice/blob/master/examples/play_sine.py
        # and is Copyright (c) 2015-2023 Matthias Geier

        # set local variables
        samplerate = sd.query_devices(None, 'output')['default_samplerate']
        sd.default.samplerate = samplerate

        # do math to determine the optimal length of dit and dah given frequency and wpm; need to ensure a dit ends as clean as it begins 

        """ from https://morsecode.world/international/timing.html : 
            Dit: 1 unit
            Dah: 3 units
            Intra-character space (the gap between dits and dahs within a character): 1 unit
            Inter-character space (the gap between the characters of a word): 3 units
            Word space (the gap between two words): 7 units

            Farnsworth: 
            Dit: 1 unit (or tdit)
            Dah: 3 units (or 3 tdit)
            Intra-character space: 1 unit (or tdit)
            Inter-character space: 3 Farnsworth-units (or 3t fdit)
            Word space: longer than 7 Farnsworth-units (or 7t fdit)
        """

        swpm=wpm # speed, words per minute.  18 minimum
        # tdit is the time of a dit in seconds (will be fractional)
        tdit=60 / (50 * swpm) 

        full_cycle_samples=samplerate / frequency
        #print (f"init: full_cycle_samples {full_cycle_samples}")

        # clean up tdit per samplerate and frequency so that the sound ends on a full cycle boundary 
        # want to find samples_per_dit as an even mutilple of full_cycle_samples
        samples_per_dit=math.ceil((samplerate * tdit) / full_cycle_samples) * full_cycle_samples
        samples_per_dit=int(samples_per_dit)
        tdit=samplerate / samples_per_dit  # reset time period in seconds of a dit to represent exact number of samples

        #print (f"init: samples_per_dit {samples_per_dit}  tdit  {tdit} ") 

        # define a dit as a numpy array of samples
        adit=np.empty((samples_per_dit,1), dtype=float)        
        sample_times=np.arange(0.0, (1.0 / samplerate * samples_per_dit), (1.0 / samplerate))  # define time, in seconds, of each sample for sin function
        
        # FIXED: arange is not numerically stable. sometimes sample_times gets one too many samples. Fixed with slice to :samples_per_dit below.
        #sample_times=sample_times.reshape((samples_per_dit,1))
        sample_times=sample_times[:samples_per_dit].reshape((samples_per_dit,1))
        
        adit[:] = amplitude * np.sin(2 * np.pi * frequency * sample_times)
        aspace=np.empty((samples_per_dit,1), dtype=float)        
        aspace[:] = 0 * np.sin(2 * np.pi * frequency * sample_times)

        #print (f"init: adit.shape {adit.shape} adit {adit}")

        adah=np.concatenate((adit, adit, adit),axis=0)                      # 1+1+1 units
        acharspace=np.concatenate((aspace, aspace, aspace),axis=0)          # 1+1+1 units
        awordspace=np.concatenate((acharspace, acharspace, aspace),axis=0)  # 3+3+1 units

        if Farnsworth: 
            acharspace=np.concatenate((acharspace, aspace),axis=0)          # 1 extra unit
            awordspace=np.concatenate((awordspace, aspace, aspace),axis=0)  # 2 extra units

        if doubleFarnsworth:
            acharspace=np.concatenate((acharspace, acharspace, acharspace),axis=0)  
            awordspace=np.concatenate((awordspace, awordspace, acharspace),axis=0) 

        #print (f"init: adit.shape {adit.shape}")
        #print (f"init: adah.shape {adah.shape}")
        #print (f"init: aspace.shape {aspace.shape}")
        #print (f"init: acharspace.shape {acharspace.shape}")
        #print (f"init: awordspace.shape {awordspace.shape}")

        def declick(a, ramp):
            samples=a.shape[0]

            for i in range(0,ramp): 
                a[i,0] *= (float(i) / ramp)  
            #   a[i,0] *= math.log10((i+1) / ramp * 10.0) 

                a[samples-i-1,0] *= (float(i) / ramp) 
            #   a[samples-i-1,0] *= math.log10((i+1) / ramp * 10.0) 


        declick(adit, int(full_cycle_samples * declick_cycles))
        declick(adah, int(full_cycle_samples * declick_cycles))

        # expose what we have created here
        self.adit=adit
        self.adah=adah
        self.aspace=aspace
        self.acharspace=acharspace
        self.awordspace=awordspace
        self.audio_out=np.empty((1,1), dtype=float)  
        """
        # make the word PARIS
        paris=np.concatenate((
            adit, aspace, adah, aspace, adah, aspace, adit, acharspace, # P
            adit, aspace, adah, acharspace,  # A
            adit, aspace, adah, aspace, adit, acharspace,  # R
            adit, aspace, adit, acharspace,  # I
            adit, aspace, adit, aspace, adit, awordspace, # S
            ), axis=0)

        sd.play(paris) 
        sd.wait()
        """

    def send_a_char(self, bits, pattern):
        while(bits):
            bits = bits - 1
            if (pattern & (1 << bits)):
                self.audio_out=np.concatenate((self.audio_out, self.adah), axis=0)
            else:
                self.audio_out=np.concatenate((self.audio_out, self.adit), axis=0)
            if (bits):
                self.audio_out=np.concatenate((self.audio_out, self.aspace), axis=0)
           
    def send_word(self, text):
        # empty the output buffer
        self.audio_out=np.empty((1,1), dtype=float)  

        for i in range(0,len(text)):
            if (text[i] == ' '):
                self.audio_out=np.concatenate((self.audio_out, self.awordspace), axis=0)
                continue
  
            try: 
                c = self.morse_symbols[text[i]]
            except: 
                #print (f"send_text: Unspported character {text[i]}")
                print (f"!{text[i]}!",end='')
                #self.send_a_char(8, 0x00000000)  #  error? 
                continue
      
            self.send_a_char(c[0], c[1])

            # if this is not the last character: 
            if (i < len(text) - 1 and text[i+1] != ' '): 
                self.audio_out=np.concatenate((self.audio_out, self.acharspace), axis=0)

        self.audio_out=np.concatenate((self.audio_out, self.awordspace), axis=0)
          
    def play_text(self, text): 
        # keep the audio buffers short by splitting into lines and words
        for line in text.splitlines(): 
            words = line.upper().split()
            for word in words: 
                self.send_word(word)
                sd.play(self.audio_out) 
                sd.wait()
                print(f"{word} ",end='',flush=True)
            print(f"")
            time.sleep(0.5)


if __name__ == '__main__':
    mo = morse_to_audio()
    mo.play_text("""CQ CQ DE K5DRU       
                 UR RST 599 599 BK""")


