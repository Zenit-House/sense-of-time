GOAL:    The viewer recognises the gap in their own AI ("it never knows I left") and wants to see the repo.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    30 s x 30 = 900 frames. No music bed (voice only, by request); the voice is the clock.
         Beat starts land on the first word of each VO clip; exact starts come from the clip durations.
LOOK:    ground #F3F1EC (warm grey-white, flat, 0 texture); ink #15140F; one accent #E8491D (time words,
         the gap label, the glowing card) and nothing else in colour.
         Display: Outfit 700, 110 px, -3% tracking (hero lines 7–9% of frame height); body Inter 500, 40 px.
         Clock digits: JetBrains Mono 600, 220 px, tabular. Medium: a chat app's own surfaces, flat-lit:
         bubbles #FFFFFF with 1 px #DAD7CF edge, radius 28 px, shadow 0 6px 18px rgba(21,20,15,0.10);
         assistant bubbles #15140F with #F3F1EC text. Grain 0, vignette 0.
OBJECTS: the clock (seven-segment-ish mono digits with a blinking colon, in a rounded dark tile);
         chat bubbles (user right, assistant left, each with a 12 px tail);
         the gap label (a pill between two bubbles reading "1 second" / "1 month");
         context cards (white cards with a date in the corner and three grey text bars);
         the intensity badge (accent pill "4 h · 60 turns");
         the wordmark "sense-of-time" in JetBrains Mono.
MOTION:  enter expo.out 0.45 s (14 f); move power2.inOut 0.5 s; exit power3.in 0.25 s; camera power2.inOut 0.6 s.
         Titles: per word blur 6 px -> 0, opacity 0 -> 1, 0.13 s each, 0.07 s apart, no translate; then dead still.
         Bubbles: y 40 -> 0 with expo.out 0.45 s, 0.12 s apart. The gap collapse: the lower bubble travels up
         onto the upper one over 0.6 s power3.in, the label shrinks with it (hero move, shot 1).
         Cards sink: y +60, opacity 1 -> 0.25, 0.5 s power2.inOut, 0.06 s stagger; the one card rises y -140,
         scale 1 -> 1.15, 0.5 s expo.out, 0.15 s after the sink starts.
SHOTS:   1 (0–~9 s)   Clock tile centre-left fills 45% of height, digits tick each second (timeline-driven),
                      then shrinks to the top-left corner (0.6 s). Two bubbles stack on the right half; the
                      pill between them reads "1 second", flips to "1 month" (slot roll 0.3 s), then the gap
                      collapses to zero. Line lands bottom-left: "To an LLM, both look the same." Reads 2.5 s.
                      Hands off: the ground floods to ink (#15140F) in 0.4 s power2.inOut while the line stays.
         2 (~9–17 s)  Ink ground. Five context cards fan across the lower two thirds, dates from
                      "3 weeks ago" to "today". On "fade" the four old ones sink and dim. On "it mattered" the
                      third card does not: badge pops (scale 0.6 -> 1, back.out(1.4)), card rises above the fresh
                      ones. Line top-left: "Recency × Intensity", the × in accent. Hands off: the risen card
                      grows past the frame (object becomes the world, 0.65 s), its white fill is shot 3's ground.
         3 (~17–25 s) Ground #F3F1EC. Three panels, one per VO phrase, each a label + one assistant bubble:
                      "7 days later" -> bubble whose first line is a recap in accent; "00:14" -> a short bubble
                      (one line) next to a ghost of a long one; "3 h straight" -> bubble "Still going?".
                      Panels enter from the right with a whip (0.2 s), the previous slides left 30% and dims.
                      On "silence" every panel exits (blur-out 0.2 s) and the line lands centre: "Time shapes how
                      it answers." then under it, smaller: "Not what it talks about." Hands off: dip cut.
         4 (~25–30 s) Ink ground. Tagline fills 80% width in two lines, per word: "It can read the clock." then
                      "It can't feel the time." with "feel" in accent. Holds 2 s. Then the wordmark rises from
                      below (expo.out) with "Stores when. Never what." and the last line "Coming soon to
                      GitHub & MCP" held to the end.
BANNED:  dark void with small floating elements; glow, bloom, neon, particles; purple/blue gradients; glass
         cards; cream + serif + italics; everything centred; everything fading in; text moving while read;
         corner labels and HUD brackets; three cards in a row as a feature list; a logo in a corner;
         a fake product dashboard; an emoji as an icon.
QA:      f 30 (clock readable, 45% height); f ~150 (gap at zero, label gone); f ~270 (flood done, line still
         legible); f ~420 (one card risen, others dim); f ~600 (three panels, text >= 28 px); f ~780 (tagline,
         "feel" in accent); f 899 (wordmark + CTA, nothing cut off).
