GOAL:    A Shorts viewer stops at frame 0, recognises "my AI never knows I left", and remembers the name.
OUTPUT:  HyperFrames, 1080 x 1920, 30 fps, vertical. Text and product inside 168–1330 px; below 1330 only texture.
TIME:    ~31 s x 30 fps. Narrated: the voice is the clock, each beat starts on its VO clip. Music bed under it
         (soft electronic pulse, ~100 BPM, instrumental), SFX on visible actions only.
LOOK:    Reference: Sber app Shorts — soft gradient world with depth of field, white glass UI cards tilted in
         3D perspective and stacked in depth, small glass spheres, bold white headline low in the frame.
         Ours: ground = radial gradient coral #F2795A (upper third) to peach #FFC9AE (bottom), with three
         blurred white blobs (blur 90 px, opacity 0.35) drifting 3–5 px/s for depth of field.
         Cards = white rgba(255,255,255,0.92), radius 36 px, 2 px top highlight rgba(255,255,255,0.9),
         thickness: a second face 14 px behind in #D9C6BA, contact shadow 0 40px 80px rgba(90,30,10,0.28).
         Perspective 1800 px on the stage; resting tilt rotateX 10°, rotateY -14°; cards in depth sit at
         translateZ -220/-440 px and blur 2/4 px (focus shift).
         Ink on cards #15140F; accent #E8491D only on time words, the gap pill, the badge.
         Headline Outfit 700 100 px white, tracking -3%, text-shadow 0 10px 40px rgba(110,35,10,0.35), left 90 px,
         max 5 words a line. Card body Inter 500 40 px; labels JetBrains Mono 600 34 px.
         Spheres: 3 glass bubbles 60–120 px (radial highlight, 1 px rim), drifting on the timeline.
OBJECTS: the clock pill (JetBrains Mono 600 120 px on a dark #15140F glass pill, ticking seconds);
         the chat card (a phone-width screen: two user bubbles right-aligned, a gap pill between them);
         context cards (date label + three grey bars, 520 x 300) fanned in depth; the intensity badge;
         reply cards (label + one assistant bubble in ink); the end card (tagline + wordmark on glass).
MOTION:  enter expo.out 0.5 s with rotateY from -34° to -14° and z from -300 to 0 (cards fly in from depth);
         focus shift: blur 0 -> 4 px and z -> -440 over 0.5 s power2.inOut when a card recedes;
         zoom-through: the hero card scales 1 -> 6 with blur 0 -> 14 px in 0.6 s power3.in at a beat end;
         ground hue shift 0.5 s power2.inOut between beats (coral -> deep coral -> peach -> ink at the end card);
         titles per word blur 6 -> 0 in 0.13 s, 0.07 s apart, then dead still; spheres and blobs never stop.
SHOTS:   1 (0–9 s)    Frame 0: chat card centred, tilted, clock pill floating above-left, both on screen.
                      Clock ticks. "1 second" pill rolls to "1 month"; the lower bubble collapses up onto the
                      upper one. Headline at y 1160: "To an LLM, both look the same." Zoom through the chat card.
         2 (9–17 s)   Five context cards fanned in depth (near to far). On "fade" the far ones blur and sink;
                      on "it mattered" the third flies forward (z -440 -> +120), badge pops. Headline:
                      "Recency × Intensity". The card tilts to flat and grows past the frame.
         3 (17–26 s)  Reply cards arrive from depth one per phrase, stacking downward with 3D offset:
                      "7 days later" / recap bubble · "00:14" / short bubble · "3 h straight" / "Still going?".
                      On "silence" they recede and blur; headline: "Time shapes how it answers." +
                      "Not what it talks about." Ground shifts to ink.
         4 (26–31 s)  Ink ground with a faint coral glow. Tagline white, "feel" in accent. Glass card rises with
                      the wordmark "sense-of-time", "Stores when. Never what.", "Coming soon to GitHub & MCP".
BANNED:  UI tilted so far it cannot be read; glow and neon; purple/blue gradients; lens flares; particles;
         everything centred and fading in; titles that keep drifting; corner logo; a fake dashboard;
         text under 28 px; anything in the top 168 px or the bottom 590 px.
QA:      f 0 (card + clock on screen, readable); f ~200 (gap at zero); f ~270 (headline, 5 words); f ~400
         (fan, depth visible); f ~440 (third card forward, badge); f ~600 (three reply cards); f ~760
         (headline on ink); f ~900 (tagline, "feel" accent, wordmark inside the safe band).
