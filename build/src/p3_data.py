

# ============================================================ 2D ART DATA ===
# ---- Duga: the Woodpecker array (built procedurally, 74 x 14) --------------
def _build_duga():
    W, H = 74, 14
    g = [[' '] * W for _ in range(H)]
    rnd = random.Random(1976)
    for _ in range(30):                                   # night sky
        g[rnd.randrange(0, 5)][rnd.randrange(W)] = rnd.choice(".*+'`")
    x0, x1 = 11, 62
    n = x1 - x0 + 1
    def rail(y):
        for i in range(n): g[y][x0 + i] = '#' if i in (0, n - 1) else '='
    def bars(y, ch):
        for i in range(n): g[y][x0 + i] = '|' if i % 2 == 0 else ch
    def rungs(y):
        for i in range(n): g[y][x0 + i] = '+' if i % 2 == 0 else '-'
    rail(1)
    for tier_top in (2, 6, 10):
        bars(tier_top, 'X'); rungs(tier_top + 1); bars(tier_top + 2, 'X')
        if tier_top < 10: rail(tier_top + 3)
    for cx in (5, W - 6):                                 # lattice pylons
        for y in range(0, 12):
            hw = 1 + y // 4
            g[y][cx - hw] = '/'; g[y][cx + hw] = '\\'
            for k in range(-hw + 1, hw):
                g[y][cx + k] = 'x' if (k + y) % 2 == 0 else ' '
    for x in range(W):                                    # the Zone: pines and grass
        g[12][x] = rnd.choice('^^^A^ ') if g[12][x] == ' ' else g[12][x]
        g[13][x] = rnd.choice('"\'",.') if g[13][x] == ' ' else g[13][x]
    return [''.join(r) for r in g]

DUGA_ART = _build_duga()

DUGA_FACTS = [
    'DUGA ("arc")  -  Soviet over-the-horizon radar, NATO name STEEL YARD',
    "Receivers at Chernobyl-2, transmitters at Liubech-1, both in Ukraine",
    "Antenna array about 700 m long and 150 m high",
    "On air July 1976 - December 1989; pulses at 10 Hz (16 and 20 Hz rarely)",
    "Signals of 7-19 MHz bounced off the ionosphere to watch for missile launches",
    "Radio hams named it THE RUSSIAN WOODPECKER; thousands of complaints followed",
    "Today the array still stands inside the Chernobyl Exclusion Zone",
]
DUGA_DEDICATION = "DUGA :: the owner's 2nd love, 3rd wife and 5th cousin (his words, not ours)"

# ---- Red Choir dancers (7 rows x 11 cols) ---------------------------------
DANCER = {
    "stand": ["   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "  / |=| \\  ", "    | |    ", "    | |    ", "   _| |_   "],
    "squat": ["           ", "           ", "   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "  <(   )>  ", "  _/___\\_  "],
    "kickR": ["           ", "   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "  <(   )___", "  _/__\\_   ", "           "],
    "kickL": ["           ", "   _/^\\_   ", "  ( o_o )  ", "   /|=|\\   ", "___(   )>  ", "   _/__\\_  ", "           "],
    "arms":  ["   _/^\\_   ", "\\  ( o_o ) /", " \\ /|=|\\ / ", "   |=|     ", "   | |     ", "   | |     ", "  _| |_    "],
}
DANCE_SEQ = ["squat", "kickR", "squat", "kickL", "squat", "kickR", "squat", "kickL", "arms", "squat"]
DOMBRA_PLAYER = ["    _/^\\_      ", "   ( o_o )     ", "   /|===|\\-------o", "   >(___)<     ", "   _/___\\_     "]
YURT = ["        /\\        ", "       /__\\       ", "     .'    '.     ", "    /  .--.  \\    ", "   /___|    |___\\   ", "       |____|       "]

# ---- B-59 / the three keys --------------------------------------------------
KEY_BOX = [
    ("CAPTAIN", "V. SAVITSKY", "YES"),
    ("POLITICAL OFFICER", "I. MASLENNIKOV", "YES"),
    ("FLOTILLA STAFF CHIEF", "V. ARKHIPOV", "NO"),
]
B59_STORY = [
    "27 Oct 1962, off Cuba. Soviet submarine B-59 (Project 641, NATO 'Foxtrot')",
    "is hunted by eleven US destroyers and the carrier USS Randolph. They drop",
    "practice depth charges to force her up. Batteries low, air conditioning",
    "dead, cut off from Moscow - they could not know if war had begun.",
    "Captain Savitsky wants to fire the nuclear torpedo. Launch needed the",
    "captain and the political officer; aboard B-59 the flotilla chief of staff,",
    "Vasili Arkhipov, was a third voice. Two said yes. Arkhipov said no.",
    "B-59 surfaced among the American ships and was sent home.",
]

